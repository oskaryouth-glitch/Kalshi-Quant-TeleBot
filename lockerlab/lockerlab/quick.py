"""Quick underwriter (strategy ``quick_v1``) and the opportunity score.

Five inputs, about a minute:
  1. visible resale: what the items you can see would realistically SELL for
  2. hidden value range: low-high for boxes, bags and what's out of frame
  3. disposal burden: negligible | light | medium | heavy
  4. transport: car_suv | pickup_van | truck
  5. confidence: 0-100%
plus optional category tags.

These are mapped onto the same cost model as the full underwriter
(strategies.build_scenario, economics.max_bid), using the audit's load
profiles scaled to the unit's size. The mapping parameters live in
config/underwriting.yaml under ``quick`` and are all GUESS until real units
calibrate them.

The opportunity score only orders your attention. It is computed from the
underwriting results and never feeds back into the max bid or the rules.
"""

from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

from . import strategies
from .config import Assumptions
from .economics import evaluate, increment_for, max_bid
from .money import fmt
from .pit import Snapshot
from .strategies import Physical, Underwriting, UnderwritingError, build_scenario, rules
from .units import unit_volume_cuft

CATEGORIES = ("TOOLS", "SKI_SNOWBOARD", "OUTDOOR", "ELECTRONICS", "BIKES", "CLOTHING", "FURNITURE",
              "COLLECTIBLES", "MUSICAL", "HOUSEHOLD", "UNKNOWN")
CATEGORY_LABELS = {"SKI_SNOWBOARD": "Ski/snowboard"}
DISPOSAL_LEVELS = ("negligible", "light", "medium", "heavy")
TRANSPORT_LEVELS = ("car_suv", "pickup_van", "truck")
TRANSPORT_LABELS = {"car_suv": "Car or SUV", "pickup_van": "Pickup or van", "truck": "Box truck"}


@dataclass(frozen=True)
class QuickEstimate:
    visible_value_cents: int
    hidden_low_cents: int
    hidden_high_cents: int
    disposal: str
    transport: str
    confidence: float
    tags: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if self.visible_value_cents < 0 or self.hidden_low_cents < 0:
            raise UnderwritingError("values must be >= 0")
        if self.hidden_high_cents < self.hidden_low_cents:
            raise UnderwritingError("hidden value: high must be at least low")
        if self.disposal not in DISPOSAL_LEVELS:
            raise UnderwritingError(f"disposal must be one of {DISPOSAL_LEVELS}")
        if self.transport not in TRANSPORT_LEVELS:
            raise UnderwritingError(f"transport must be one of {TRANSPORT_LEVELS}")
        if not 0 <= self.confidence <= 1:
            raise UnderwritingError("confidence must be 0-100%")
        bad = set(self.tags) - set(CATEGORIES)
        if bad:
            raise UnderwritingError(f"unknown category tags {sorted(bad)}")


def gross_cases(est: QuickEstimate, q: Assumptions) -> dict[str, int]:
    """Pre-haircut gross resale for low/base/high."""
    v, lo, hi = est.visible_value_cents, est.hidden_low_cents, est.hidden_high_cents
    pos = q.get("hidden_base_position")
    return {
        "low": int(v * q.get("visible_low_factor") + lo),
        "base": int(v + lo + pos * (hi - lo)),
        "high": int(v * q.get("visible_high_factor") + hi),
    }


def avg_sale_cents(tags: tuple[str, ...], q: Assumptions) -> int:
    table = q.get("avg_sale_by_category_cents")
    known = [t for t in tags if t != "UNKNOWN"] or ["UNKNOWN"]
    return max(100, round(sum(table[t] for t in known) / len(known)))


def physical(snap: Snapshot, est: QuickEstimate, q: Assumptions) -> Physical:
    prof = q.get("disposal_profiles")[est.disposal]
    vol = unit_volume_cuft(snap.width_ft, snap.length_ft, snap.height_ft)
    per50 = snap.width_ft * snap.length_ft / 50

    def count(rate: float) -> int:
        return math.floor(rate * per50 + 0.5)  # half-up, so one 5x5 'heavy' still has its mattress

    longest = q.get("transport_requirements")[est.transport]["longest_in"]
    return Physical(
        retained_cuft=vol * prof["retained"], donate_cuft=vol * prof["donate"], trash_cuft=vol * prof["trash"],
        longest_item_in=longest, mattresses=count(prof["mattresses_per_50sqft"]),
        appliances=count(prof["appliances_per_50sqft"]), ewaste_items=int(prof["ewaste"]),
        bulky_items=count(prof["bulky_per_50sqft"]),
    )


def _market_for_transport(market: Assumptions, min_cuft: float) -> Assumptions:
    if not min_cuft:
        return market
    tree = copy.deepcopy(market.tree)
    for v in tree["vehicles"].values():
        if v["usable_cuft"]["value"] < min_cuft:
            v["available"] = {"value": False, "status": "VERIFIED", "source": "quick estimate: needs a truck"}
    return Assumptions(tree)


def quick_v1(snap: Snapshot, est: QuickEstimate, market: Assumptions, uw: Assumptions) -> Underwriting:
    if snap.width_ft is None or snap.length_ft is None:
        raise UnderwritingError("unit size unknown: add it to the capture before estimating")
    q = uw.section("quick")
    haircut = uw.get("valuation_haircut")
    gross = {k: int(v * haircut) for k, v in gross_cases(est, q).items()}
    avg = avg_sale_cents(est.tags, q)
    lpo = q.get("listings_per_order")
    phys = physical(snap, est, q)
    mkt = _market_for_transport(market, q.get("transport_requirements")[est.transport]["min_cuft"])
    one_way = snap.distance_miles if snap.distance_miles is not None else market.get("home_to_unit_miles_default")

    built = {}
    for name in ("low", "base", "high"):
        p = phys if name != "low" else Physical(  # low case: half the would-be donations are junk
            phys.retained_cuft, phys.donate_cuft / 2, phys.trash_cuft + phys.donate_cuft / 2, phys.longest_item_in,
            phys.mattresses, phys.appliances, phys.ewaste_items, phys.bulky_items)
        orders = math.ceil(gross[name] / avg) if gross[name] > 0 else 0
        built[name] = build_scenario(name, gross[name], orders, math.ceil(orders * lpo), p, mkt, uw, one_way)
    scenarios = {k: b.scenario for k, b in built.items()}
    policy = strategies._policy(snap, market, uw)
    mb = max_bid(scenarios, policy, rules(uw))

    current = snap.current_bid_cents if snap.current_bid_cents is not None else snap.opening_bid_cents
    schedule = uw.get("bid_increments")
    reasons: list[str] = []
    if mb.max_bid_cents is None:
        rec = "PASS"
        reasons.append("No bid satisfies the underwriting rules (" + ", ".join(mb.binding_constraints) + ").")
    elif current is not None and mb.max_bid_cents < current + increment_for(current, schedule):
        rec = "PASS"
        reasons.append(f"Current bid {fmt(current)} is already at or above the max paper bid {fmt(mb.max_bid_cents)}.")
    elif est.confidence < uw.get("min_confidence_for_paper_bid"):
        rec = "WATCH"
        reasons.append(f"Confidence {est.confidence:.0%} is below the {uw.get('min_confidence_for_paper_bid'):.0%} "
                       "needed for a paper bid.")
    else:
        rec = "PAPER_BID"
        reasons.append("Max bid limited by: " + ", ".join(mb.binding_constraints) + ".")

    at_max = mb.max_bid_cents if mb.max_bid_cents is not None else (current or 0)
    evals_max = {k: evaluate(at_max, s, policy) for k, s in scenarios.items()}
    at_cur = current or 0
    evals_cur = {k: evaluate(at_cur, s, policy) for k, s in scenarios.items()}
    labor_values = uw.get("labor_value_scenarios_cents")
    headline_lv = uw.get("labor_value_cents_per_hour")
    base_b = built["base"]
    outputs = {
        "model_recommendation": rec,
        "max_bid_cents": mb.max_bid_cents,
        "evaluated_at_bid_cents": at_max,
        "current_bid_cents": current,
        "binding_constraints": mb.binding_constraints,
        "evaluations": {k: e.summary() for k, e in evals_max.items()},
        "evaluations_at_current_bid": {k: e.summary() for k, e in evals_cur.items()},
        "economic_profit_cents_by_labor_value": {
            k: {str(v): e.economic_profit_cents(v) for v in labor_values} for k, e in evals_max.items()},
        "economic_profit_cents_by_labor_value_at_current_bid": {
            k: {str(v): e.economic_profit_cents(v) for v in labor_values} for k, e in evals_cur.items()},
        "headline_labor_value_cents": headline_lv,
        "physical": asdict(phys),
        "avg_sale_cents": avg,
        "transport": {"choice": asdict(base_b.transport), "options": [asdict(o) for o in base_b.options]},
        "disposal": asdict(base_b.disposal) | {
            "total_cents": base_b.disposal.total_cents,
            "burden_level": strategies._disposal_level(base_b.disposal, scenarios["base"].gross_proceeds_cents)},
        "value_density": strategies._density_label(evals_max["base"].gross_per_retained_cuft_cents),
        "gross_before_haircut_cents": gross_cases(est, q),
    }
    inputs = {
        "snapshot": snap.to_dict(),
        "quick_estimate": asdict(est),
        "policy": asdict(policy),
        "rules": asdict(rules(uw)),
        "scenarios": {k: asdict(s) for k, s in scenarios.items()},
        "valuation_haircut": haircut,
    }
    return Underwriting(rec, mb.max_bid_cents, mb.max_bid_cents if rec == "PAPER_BID" else None,
                        est.confidence, reasons, outputs, inputs)


strategies.STRATEGIES["quick_v1"] = {"fn": quick_v1, "version": "1", "automatic": False}


# ---------------------------------------------------------------------------
# Opportunity score: transparent points, for ordering attention only.
# ---------------------------------------------------------------------------

def opportunity_score(outputs: dict, est: dict, size_bucket: str | None, current_bid_cents: int | None,
                      uw: Assumptions) -> dict:
    """Score 0-100 from a stored underwriting. Every point has a stated reason.
    ``current_bid_cents`` may be newer than the decision (a later capture)."""
    comps: list[tuple[str, float, int, str]] = []  # (name, points, max, reason)
    minus: list[str] = []
    base = outputs["evaluations"]["base"]
    mb = outputs.get("max_bid_cents")
    cur = current_bid_cents if current_bid_cents is not None else outputs.get("current_bid_cents")

    # 1. Headroom between the current bid and the max paper bid (25)
    if mb is not None and cur is not None and mb > cur:
        h = (mb - cur) / mb
        comps.append(("Bid headroom", 25 * h, 25, f"Current bid {fmt(cur)} is {h:.0%} below the max paper bid {fmt(mb)}"))
    elif mb is not None and cur is None:
        comps.append(("Bid headroom", 12, 25, f"No current bid recorded; max paper bid {fmt(mb)}"))
    else:
        comps.append(("Bid headroom", 0, 25, "No room under the max paper bid"))
        minus.append("Current bid is at or above what the rules allow" if mb is not None else "No bid satisfies the rules")

    # 2. Cash profit at the max paper bid (15)
    cash = base["cash_profit_cents"]
    comps.append(("Cash profit", 15 * max(0.0, min(1.0, cash / 60000)), 15,
                  f"Expected cash profit {fmt(cash)} even at the max bid"))
    # 3. Economic profit at your value of time (10)
    lv = str(uw.get("labor_value_cents_per_hour"))
    econ = outputs["economic_profit_cents_by_labor_value"]["base"].get(lv)
    if econ is None:
        econ = base["cash_profit_cents"] - round(base["labor_hours"] * int(lv))
    comps.append(("Economic profit", 10 * max(0.0, min(1.0, econ / 30000)), 10,
                  f"Economic profit {fmt(econ)} at ${int(lv) // 100}/h for {base['labor_hours']:.0f} h"))
    if econ <= 0:
        minus.append(f"Not worth it at ${int(lv) // 100}/h ({base['labor_hours']:.0f} h of work)")
    # 4. Value density (10)
    dens = base.get("gross_per_retained_cuft_cents") or 0
    comps.append(("Value density", 10 if dens >= 2000 else 5 if dens >= 800 else 0, 10,
                  f"{fmt(round(dens))} of resale per kept cubic foot"))
    # 5. Disposal (10)
    dpts = {"negligible": 10, "light": 8, "medium": 4, "heavy": 0}[est["disposal"]]
    comps.append(("Disposal", dpts, 10, f"{est['disposal'].capitalize()} disposal "
                  f"(~{fmt(outputs['disposal']['total_cents'])})"))
    if est["disposal"] == "heavy":
        minus.append(f"Heavy disposal (~{fmt(outputs['disposal']['total_cents'])} and extra trips)")
    # 6. Transport (10)
    veh = outputs["transport"]["choice"]["vehicle"]
    borrowed = veh.startswith("friend_")
    comps.append(("Transport", 10 if borrowed else 4 if est["transport"] != "truck" else 0, 10,
                  f"{outputs['transport']['choice']['trips']} trip(s) by {veh.replace('_', ' ')}"))
    if not borrowed:
        minus.append(f"Needs a rental ({veh.replace('_', ' ')})")
    # 7. Confidence (10)
    conf = est["confidence"]
    comps.append(("Confidence", 10 * conf, 10, f"Valuation confidence {conf:.0%}"))
    if conf < 0.6:
        minus.append(f"Valuation confidence only {conf:.0%}")
    # 8. Small unit (5): your stated constraint, not an edge
    small = size_bucket in ("5x5", "5x10")
    comps.append(("Small unit", 5 if small else 0, 5, f"{size_bucket or 'unknown size'} "
                  + ("fits your space and vehicle limits" if small else "is outside your default focus")))
    # 9. Category prior (+/-5, unvalidated)
    pts_table = uw.get("score", "category_points")
    tags = est.get("tags") or []
    cat = max(-5, min(5, sum(pts_table.get(t, 0) for t in tags)))
    if tags:
        comps.append(("Categories (unvalidated prior)", cat, 5, ", ".join(t.replace("_", "/").title() for t in tags)))
    # Hidden-value share
    vis, lo, hi = est["visible_value_cents"], est["hidden_low_cents"], est["hidden_high_cents"]
    hidden_mid = (lo + hi) / 2
    if vis + hidden_mid > 0 and hidden_mid / (vis + hidden_mid) > 0.5:
        minus.append(f"Most of the value is hidden ({fmt(round(hidden_mid))} of {fmt(round(vis + hidden_mid))} unseen)")

    total = max(0, min(100, round(sum(c[1] for c in comps))))
    plus = [c[3] for c in sorted(comps, key=lambda c: -c[1]) if c[1] >= 0.6 * c[2] and c[1] > 0]
    return {"score": total, "plus": plus, "minus": minus,
            "components": [{"name": n, "points": round(p, 1), "max": m, "why": w} for n, p, m, w in comps]}
