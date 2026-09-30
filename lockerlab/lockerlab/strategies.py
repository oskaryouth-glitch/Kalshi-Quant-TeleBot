"""Underwriting strategies.

A strategy is a pure function (Snapshot, estimate, config) -> Underwriting.
It never receives a database connection, so it can only use information in
the point-in-time snapshot it is handed.

``manual_v1`` underwrites from Oskar's own judgement of the photos (gross
low/base/high, how full the unit is, what share is keepable). It is FORWARD
only: a human estimate made after an auction closed is contaminated by
knowing the outcome, so it can never be backtested. It also serves as the
human baseline that the Phase-2/3 AI valuation must beat.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from . import disposal, transport
from .config import Assumptions
from .economics import CostPolicy, MarginRules, Scenario, evaluate, increment_for, max_bid
from .money import fmt, parse_dollars
from .pit import Snapshot
from .units import unit_volume_cuft


class UnderwritingError(ValueError):
    pass


@dataclass(frozen=True)
class OperatorEstimate:
    gross_low_cents: int
    gross_base_cents: int
    gross_high_cents: int
    confidence: float
    fill_fraction: float  # share of the unit's volume that is occupied
    keep_fraction: float  # share of the contents kept to sell
    trash_fraction: float  # share of the contents dumped (remainder is donated)
    n_listings: int
    n_orders: int
    longest_item_in: float = 0.0
    mattresses: int = 0
    appliances: int = 0
    ewaste_items: int = 0
    bulky_items: int = 0
    categories: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.gross_low_cents <= self.gross_base_cents <= self.gross_high_cents:
            raise UnderwritingError("need 0 <= low <= base <= high gross proceeds")
        for name in ("confidence", "fill_fraction", "keep_fraction", "trash_fraction"):
            if not 0 <= getattr(self, name) <= 1:
                raise UnderwritingError(f"{name} must be within [0, 1]")
        if self.keep_fraction + self.trash_fraction > 1 + 1e-9:
            raise UnderwritingError("keep_fraction + trash_fraction must be <= 1")
        if self.n_listings < 0 or self.n_orders < 0:
            raise UnderwritingError("counts must be >= 0")

    @classmethod
    def from_dict(cls, d: dict) -> "OperatorEstimate":
        g = d["gross_proceeds"]
        v = d["volume"]
        c = d.get("counts", {})
        return cls(
            gross_low_cents=parse_dollars(str(g["low"])),
            gross_base_cents=parse_dollars(str(g["base"])),
            gross_high_cents=parse_dollars(str(g["high"])),
            confidence=float(d["confidence"]),
            fill_fraction=float(v["fill_fraction"]),
            keep_fraction=float(v["keep_fraction"]),
            trash_fraction=float(v["trash_fraction"]),
            longest_item_in=float(d.get("longest_item_in", 0)),
            n_listings=int(c.get("listings", 0)),
            n_orders=int(c.get("orders", 0)),
            mattresses=int(c.get("mattresses", 0)),
            appliances=int(c.get("appliances", 0)),
            ewaste_items=int(c.get("ewaste_items", 0)),
            bulky_items=int(c.get("bulky_items", 0)),
            categories=tuple(d.get("categories", [])),
            reasons=tuple(d.get("reasons", [])),
            notes=str(d.get("notes", "")),
        )


@dataclass
class Underwriting:
    decision: str  # PAPER_BID | WATCH | PASS
    max_bid_cents: int | None
    paper_bid_cents: int | None
    confidence: float
    reasons: list[str]
    outputs: dict
    inputs: dict = field(default_factory=dict)


def _policy(snap: Snapshot, market: Assumptions, uw: Assumptions) -> CostPolicy:
    return CostPolicy(
        buyer_premium_rate=snap.buyer_premium_rate if snap.buyer_premium_rate is not None
        else uw.get("default_buyer_premium_rate"),
        buyer_premium_min_cents=snap.buyer_premium_min_cents if snap.buyer_premium_min_cents is not None
        else uw.get("default_buyer_premium_min_cents"),
        sales_tax_rate=snap.sales_tax_rate if snap.sales_tax_rate is not None else market.get("sales_tax_rate"),
        tax_applies_to_premium=True,
        resale_exempt=False,
        cleaning_deposit_cents=snap.cleaning_deposit_cents if snap.cleaning_deposit_cents is not None
        else uw.get("default_cleaning_deposit_cents"),
        cleaning_deposit_forfeit_prob=uw.get("cleaning_deposit_forfeit_prob"),
        selling_fee_rate=uw.get("selling_fee_rate"),
        per_order_fee_cents=uw.get("per_order_fee_cents"),
        packing_cost_per_shipped_order_cents=uw.get("packing_cost_per_shipped_order_cents"),
        shipped_order_share=uw.get("shipped_order_share"),
        returns_rate=uw.get("returns_rate"),
        risk_reserve_rate=uw.get("risk_reserve_rate"),
        labor_rate_cents_per_hour=uw.get("labor_rate_cents_per_hour"),
    )


def _rules(uw: Assumptions) -> MarginRules:
    return MarginRules(
        min_expected_profit_cents=uw.get("min_expected_profit_cents"),
        target_roi=uw.get("target_roi"),
        max_low_case_loss_cents=uw.get("max_low_case_loss_cents"),
        min_profit_per_hour_before_labor_cents=uw.get("min_profit_per_hour_before_labor_cents"),
        bankroll_cents=uw.get("bankroll_cents"),
    )


def _density_label(gross_per_cuft_cents: float | None) -> str:
    if gross_per_cuft_cents is None:
        return "UNKNOWN"
    # $/cuft of kept inventory. Display thresholds only (GUESS); not used in max bid.
    if gross_per_cuft_cents >= 2000:
        return "HIGH"
    if gross_per_cuft_cents >= 800:
        return "MEDIUM"
    return "LOW"


def _disposal_level(d: disposal.DisposalEstimate, gross_cents: int) -> str:
    """Worse of the volume/item burden and the cost burden (share of gross)."""
    order = ["LOW", "MEDIUM", "HIGH"]
    share = d.total_cents / gross_cents if gross_cents else (1.0 if d.total_cents else 0.0)
    by_cost = "LOW" if share < 0.10 else "MEDIUM" if share < 0.25 else "HIGH"
    return max(d.burden_level, by_cost, key=order.index)


def manual_v1(snap: Snapshot, est: OperatorEstimate, market: Assumptions, uw: Assumptions) -> Underwriting:
    if snap.width_ft is None or snap.length_ft is None:
        raise UnderwritingError("unit size unknown: capture unit_size before underwriting")

    haircut = uw.get("valuation_haircut")
    occupied = unit_volume_cuft(snap.width_ft, snap.length_ft, snap.height_ft) * est.fill_fraction
    retained = occupied * est.keep_fraction
    trash = occupied * est.trash_fraction
    donate = max(0.0, occupied - retained - trash)

    lab = uw.section("labor")
    hours_per_trip = lab.get("hours_per_vehicle_trip")
    vehicles = [transport.Vehicle.from_config(k, v) for k, v in market.section("vehicles").plain().items()]
    one_way = snap.distance_miles if snap.distance_miles is not None else market.get("home_to_unit_miles_default")
    rates = disposal.DisposalRates.from_config(market.section("disposal").plain())
    free_cuft = market.get("disposal", "free_household_trash_cuft")

    def scenario(name: str, gross_cents: int, trash_cuft: float, donate_cuft: float):
        load = transport.Load(retained, donate_cuft, trash_cuft, est.longest_item_in)
        options = transport.plan(load, vehicles, one_way, market.get("dump_round_trip_miles"), hours_per_trip)
        # Trash within the free allowance (household bins over a few weeks)
        # skips the dump; only the remainder pays gate fees.
        dump_cuft = max(0.0, trash_cuft - free_cuft)

        def disposal_for(opt: transport.TransportOption) -> disposal.DisposalEstimate:
            visits = opt.dump_trips if dump_cuft > 0 or est.mattresses or est.appliances else 0
            return disposal.estimate(
                disposal.DisposalInput(dump_cuft, est.mattresses, est.appliances, est.ewaste_items,
                                       est.bulky_items),
                rates, visits,
            )

        # Pick the vehicle by transport + disposal: each dump visit pays the
        # gate minimum, so a bigger vehicle can be cheaper overall.
        feasible = [(o, disposal_for(o)) for o in options if o.feasible]
        if not feasible:
            raise UnderwritingError(
                "no available vehicle can clear this unit: "
                + "; ".join(f"{o.vehicle}: {o.reason}" for o in options)
            )
        pick, disp = min(feasible, key=lambda od: (od[0].cost_cents + od[1].total_cents, od[0].trips))
        # Orders scale with how much actually sells in this scenario.
        orders = est.n_orders if est.gross_base_cents == 0 else math.ceil(
            est.n_orders * gross_cents / max(est.gross_base_cents * haircut, 1))
        hours = (
            lab.get("fixed_hours") + pick.hours + occupied * lab.get("minutes_per_cuft_handled") / 60
            + est.n_listings * lab.get("minutes_per_listing") / 60 + orders * lab.get("minutes_per_sale") / 60
        )
        storage = math.ceil(retained * uw.get("storage_cost_per_cuft_month_cents") * uw.get("expected_months_held"))
        s = Scenario(name, gross_cents, orders, pick.cost_cents, disp.total_cents, round(hours, 2), retained,
                     storage_cost_cents=storage)
        return s, pick, options, disp

    # Haircut applies to every case: it corrects systematic optimism in the
    # estimates themselves, not just the middle case.
    g = {k: int(v * haircut) for k, v in
         (("low", est.gross_low_cents), ("base", est.gross_base_cents), ("high", est.gross_high_cents))}
    # Low case: hidden contents disappoint, so half the would-be donations are junk.
    built = {
        "low": scenario("low", g["low"], trash + donate / 2, donate / 2),
        "base": scenario("base", g["base"], trash, donate),
        "high": scenario("high", g["high"], trash, donate),
    }
    scenarios = {k: v[0] for k, v in built.items()}
    policy = _policy(snap, market, uw)
    mb = max_bid(scenarios, policy, _rules(uw))

    reasons = list(est.reasons)
    current = snap.current_bid_cents if snap.current_bid_cents is not None else snap.opening_bid_cents
    schedule = uw.get("bid_increments")
    if mb.max_bid_cents is None:
        decision, paper_bid = "PASS", None
        reasons.append("no bid satisfies margin rules: " + ", ".join(mb.binding_constraints))
    elif current is not None and mb.max_bid_cents < current + increment_for(current, schedule):
        decision, paper_bid = "PASS", None
        reasons.append(f"current bid {fmt(current)} already at/above max {fmt(mb.max_bid_cents)}")
    elif est.confidence < uw.get("min_confidence_for_paper_bid"):
        decision, paper_bid = "WATCH", None
        reasons.append(f"confidence {est.confidence:.0%} below paper-bid threshold")
    else:
        decision, paper_bid = "PAPER_BID", mb.max_bid_cents
        reasons.append(f"max bid limited by: {', '.join(mb.binding_constraints)}")

    eval_bid = mb.max_bid_cents if mb.max_bid_cents is not None else (current or 0)
    evals = {k: evaluate(eval_bid, s, policy) for k, s in scenarios.items()}
    base_pick, base_disp = built["base"][1], built["base"][3]
    base_eval = evals["base"]
    outputs = {
        "evaluated_at_bid_cents": eval_bid,
        "binding_constraints": mb.binding_constraints,
        "evaluations": {k: e.summary() for k, e in evals.items()},
        "volumes_cuft": {"occupied": occupied, "retained": retained, "donate": donate, "trash": trash},
        "transport": {"choice": asdict(base_pick), "options": [asdict(o) for o in built["base"][2]]},
        "disposal": asdict(base_disp) | {
            "total_cents": base_disp.total_cents,
            "share_of_gross": base_disp.total_cents / base_eval.gross_proceeds_cents
            if base_eval.gross_proceeds_cents else None,
            "burden_level": _disposal_level(base_disp, base_eval.gross_proceeds_cents),
        },
        "value_density": _density_label(base_eval.gross_per_retained_cuft_cents),
        "net_profit_per_vehicle_trip_cents": (
            base_eval.net_profit_cents / base_pick.trips if base_pick.trips else None
        ),
    }
    inputs = {
        "snapshot": snap.to_dict(),
        "estimate": asdict(est),
        "policy": asdict(policy),
        "rules": asdict(_rules(uw)),
        "scenarios": {k: asdict(s) for k, s in scenarios.items()},
        "valuation_haircut": haircut,
    }
    return Underwriting(decision, mb.max_bid_cents, paper_bid, est.confidence, reasons, outputs, inputs)


STRATEGIES = {
    "manual_v1": {"fn": manual_v1, "version": "1", "automatic": False},
}
