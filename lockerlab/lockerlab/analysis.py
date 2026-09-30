"""Pre-data analysis: hurdle rates implied by the cost model.

``required_gross`` answers: "for a unit of this size and contents profile,
how much base-case gross resale must it hold for the margin rules to allow
a bid of X?" Everything here is SIMULATED from config assumptions; nothing is
stored. Compare the hurdles with what lockers actually contain (once real
data exists) to see whether an edge is even plausible.
"""

from __future__ import annotations

import math
import dataclasses
from dataclasses import dataclass, fields

from .config import Assumptions
from .pit import Snapshot
from .strategies import OperatorEstimate, UnderwritingError, manual_v1

STANDARD_SIZES = {"5x5": (5, 5), "5x10": (5, 10), "10x10": (10, 10), "10x15": (10, 15), "10x20+": (10, 20)}


@dataclass(frozen=True)
class Profile:
    fill_fraction: float = 0.5
    keep_fraction: float = 0.3
    trash_fraction: float = 0.4
    low_ratio: float = 0.33  # low-case gross as a share of base
    high_ratio: float = 2.0
    avg_sale_cents: int = 4000  # average proceeds per order: the value-density lever
    listings_per_order: float = 1.2
    longest_item_in: float = 48
    confidence: float = 0.6


def synthetic_snapshot(width: float, length: float, market_key: str) -> Snapshot:
    vals = {f.name: None for f in fields(Snapshot)}
    vals.update(
        auction_id=0, source_key="SIMULATED", external_id="SIMULATED", market_key=market_key,
        observation_id=0, observed_at="", recorded_at="", status="active", as_of="",
        width_ft=float(width), length_ft=float(length),
    )
    return Snapshot(**vals)


def _estimate(base_cents: int, p: Profile) -> OperatorEstimate:
    orders = max(1, math.ceil(base_cents / p.avg_sale_cents))
    return OperatorEstimate(
        gross_low_cents=int(base_cents * p.low_ratio), gross_base_cents=base_cents,
        gross_high_cents=int(base_cents * p.high_ratio), confidence=p.confidence,
        fill_fraction=p.fill_fraction, keep_fraction=p.keep_fraction, trash_fraction=p.trash_fraction,
        n_listings=math.ceil(orders * p.listings_per_order), n_orders=orders,
        longest_item_in=p.longest_item_in,
    )


def max_bid_for(snap: Snapshot, base_cents: int, p: Profile, market: Assumptions, uw: Assumptions) -> int | None:
    try:
        return manual_v1(snap, _estimate(base_cents, p), market, uw).max_bid_cents
    except UnderwritingError:
        return None


def required_gross(snap: Snapshot, bid_cents: int, p: Profile, market: Assumptions, uw: Assumptions,
                   ceiling_cents: int = 5_000_000) -> int | None:
    """Smallest base gross (to the nearest $10) whose max bid is >= bid_cents;
    None if even ``ceiling_cents`` is not enough (or no vehicle can clear it)."""
    ok = lambda g: (max_bid_for(snap, g, p, market, uw) or -1) >= bid_cents  # noqa: E731
    if not ok(ceiling_cents):
        return None
    lo, hi = 0, ceiling_cents // 1000  # in $10 steps
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(mid * 1000):
            hi = mid
        else:
            lo = mid
    return hi * 1000


def breakeven_table(market_key: str, market: Assumptions, uw: Assumptions, bids_cents: list[int],
                    p: Profile) -> list[dict]:
    rows = []
    for name, (w, l) in STANDARD_SIZES.items():
        snap = synthetic_snapshot(w, l, market_key)
        row = {"size": name}
        for b in bids_cents:
            row[f"bid_{b // 100}_cents"] = required_gross(snap, b, p, market, uw)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Small-unit sensitivity (2026-10 audit). SIMULATED from config assumptions:
# given a REALIZED gross resale figure (no valuation haircut), what do cash
# profit, economic profit, ROI and hours look like across purchase prices,
# disposal profiles and vehicle situations?
# ---------------------------------------------------------------------------

import copy  # noqa: E402

from .config import Assumptions  # noqa: E402
from .economics import evaluate  # noqa: E402
from .strategies import Physical, build_scenario, cost_policy  # noqa: E402

# Physical load profiles (cuft). GUESS values, stated explicitly so they can be
# argued with. Kept volume is fixed per size, so gross / kept = value density.
DISPOSAL_PROFILES: dict[str, dict[str, Physical]] = {
    "5x5": {  # 200 cuft unit
        "LOW": Physical(retained_cuft=20, donate_cuft=25, trash_cuft=3, longest_item_in=36),
        "MEDIUM": Physical(retained_cuft=20, donate_cuft=40, trash_cuft=30, longest_item_in=60, ewaste_items=1),
        "HIGH": Physical(retained_cuft=20, donate_cuft=45, trash_cuft=70, longest_item_in=84,
                         mattresses=1, ewaste_items=1, bulky_items=1),
    },
    "5x10": {  # 400 cuft unit
        "LOW": Physical(retained_cuft=40, donate_cuft=50, trash_cuft=8, longest_item_in=48),
        "MEDIUM": Physical(retained_cuft=40, donate_cuft=80, trash_cuft=60, longest_item_in=60,
                           mattresses=1, ewaste_items=1),
        "HIGH": Physical(retained_cuft=40, donate_cuft=90, trash_cuft=150, longest_item_in=84,
                         mattresses=2, appliances=1, ewaste_items=2, bulky_items=2),
    },
}

# scenario key -> (disposal profile, allowed vehicle kinds, only these vehicles or None)
VEHICLE_SCENARIOS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...] | None]] = {
    "LOW disposal / borrowed SUV": ("LOW", ("borrowed",), ("friend_suv",)),
    "LOW disposal / rental van": ("LOW", ("rental",), ("uhaul_cargo_van",)),
    "MEDIUM disposal / borrowed vehicle": ("MEDIUM", ("borrowed",), None),
    "MEDIUM disposal / rental vehicle": ("MEDIUM", ("rental",), None),
    "HIGH disposal / rental vehicle": ("HIGH", ("rental",), None),
}

BIDS_DOLLARS = (0, 50, 100, 150, 200, 300, 500)
GROSS_DOLLARS = (250, 500, 750, 1000, 1500, 2000, 3000)


def _only_vehicles(market: Assumptions, keys: tuple[str, ...] | None) -> Assumptions:
    if keys is None:
        return market
    tree = copy.deepcopy(market.tree)
    for k, v in tree["vehicles"].items():
        if k not in keys:
            v["available"] = {"value": False, "status": "VERIFIED", "source": "sensitivity scenario"}
    return Assumptions(tree)


def _sales_counts(gross_cents: int, avg_sale_cents: int, listings_per_order: float) -> tuple[int, int]:
    orders = max(1, math.ceil(gross_cents / avg_sale_cents)) if gross_cents else 0
    return orders, math.ceil(orders * listings_per_order)


def cell(size: str, scenario_key: str, bid_cents: int, gross_cents: int, market: Assumptions,
         uw: Assumptions, avg_sale_cents: int = 5000, listings_per_order: float = 1.25,
         one_way_miles: float | None = None) -> dict:
    profile, kinds, only = VEHICLE_SCENARIOS[scenario_key]
    phys = DISPOSAL_PROFILES[size][profile]
    mkt = _only_vehicles(market, only)
    miles = one_way_miles if one_way_miles is not None else market.get("home_to_unit_miles_default")
    orders, listings = _sales_counts(gross_cents, avg_sale_cents, listings_per_order)
    b = build_scenario("realized", gross_cents, orders, listings, phys, mkt, uw, miles, kinds=kinds)
    e = evaluate(bid_cents, b.scenario, cost_policy(market, uw))
    labor_values = uw.get("labor_value_scenarios_cents")
    return {
        "size": size, "scenario": scenario_key, "bid_cents": bid_cents, "gross_cents": gross_cents,
        "cash_profit_cents": e.cash_profit_cents,
        **{f"economic_profit_at_{v // 100}_cents": e.economic_profit_cents(v) for v in labor_values},
        "cash_roi": e.cash_roi,
        "labor_hours": e.labor_hours,
        "cash_profit_per_hour_cents": e.cash_profit_per_hour_cents,
        "cash_required_cents": e.cash_required_cents,
        "acquisition_cents": e.acquisition.total_cents,
        "transport_cents": e.transport_cents,
        "disposal_cents": e.disposal_cents,
        "selling_and_tax_cents": e.selling_costs_cents - e.risk_reserve_cents,
        "vehicle": b.transport.vehicle,
        "trips": b.transport.trips,
        "pathways": list(b.disposal.pathways),
    }


def breakeven_gross(size: str, scenario_key: str, bid_cents: int, market: Assumptions, uw: Assumptions,
                    labor_value_cents: int = 0, avg_sale_cents: int = 5000,
                    ceiling_cents: int = 2_000_000) -> int | None:
    """Smallest realized gross (to $10) with economic profit >= 0 at this labor
    value (0 = cash break-even). None if above ``ceiling_cents``."""
    def ok(g: int) -> bool:
        c = cell(size, scenario_key, bid_cents, g, market, uw, avg_sale_cents)
        return c["cash_profit_cents"] - round(c["labor_hours"] * labor_value_cents) >= 0

    if not ok(ceiling_cents):
        return None
    lo, hi = 0, ceiling_cents // 1000
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(mid * 1000):
            hi = mid
        else:
            lo = mid
    return hi * 1000


def sensitivity(market_key: str, market: Assumptions, uw: Assumptions, avg_sale_cents: int = 5000,
                sizes: tuple[str, ...] = ("5x5", "5x10")) -> dict:
    cells, breakevens = [], []
    for size in sizes:
        for sk in VEHICLE_SCENARIOS:
            for bid in BIDS_DOLLARS:
                for gross in GROSS_DOLLARS:
                    cells.append(cell(size, sk, bid * 100, gross * 100, market, uw, avg_sale_cents))
                row = {"size": size, "scenario": sk, "bid_cents": bid * 100}
                for lv in uw.get("labor_value_scenarios_cents"):
                    row[f"breakeven_gross_at_{lv // 100}_per_hour_cents"] = breakeven_gross(
                        size, sk, bid * 100, market, uw, lv, avg_sale_cents)
                breakevens.append(row)
    return {"market": market_key, "avg_sale_cents": avg_sale_cents, "bids": list(BIDS_DOLLARS),
            "grosses": list(GROSS_DOLLARS), "profiles": {s: {k: dataclasses.asdict(p) for k, p in d.items()}
                                                          for s, d in DISPOSAL_PROFILES.items()},
            "cells": cells, "breakevens": breakevens}


def _money(c: float | None) -> str:
    if c is None:
        return "n/a"
    return f"-${abs(c) / 100:,.0f}" if c < 0 else f"${c / 100:,.0f}"


def render_sensitivity_md(data: dict, metrics: tuple[str, ...] = ("cash_profit_cents", "economic_profit_at_25_cents")) -> str:
    """Markdown tables: per size x scenario, rows = purchase price, cols = realized gross."""
    bids, grosses = data["bids"], data["grosses"]
    idx = {(c["size"], c["scenario"], c["bid_cents"], c["gross_cents"]): c for c in data["cells"]}
    out = [
        f"# Small-unit sensitivity ({data['market']}), SIMULATED",
        "",
        "Generated by `lockerlab sensitivity`. Rows: winning bid. Columns: REALIZED gross resale",
        f"(no valuation haircut). Average sale ${data['avg_sale_cents'] / 100:.0f}. Every input is from",
        "config/*.yaml; most are GUESS. See docs/AUDIT_2026-10.md for interpretation.",
        "",
    ]
    for size in dict.fromkeys(c["size"] for c in data["cells"]):
        out.append(f"## {size}")
        for sk in VEHICLE_SCENARIOS:
            probe = idx[(size, sk, bids[0] * 100, grosses[0] * 100)]
            out += ["", f"### {size}: {sk}",
                    f"Vehicle chosen: {probe['vehicle']} ({probe['trips']} trips). Disposal pathways: "
                    f"{', '.join(probe['pathways'])}.", ""]
            hrs = " | ".join(f"{idx[(size, sk, 0, g * 100)]['labor_hours']:.1f}" for g in grosses)
            out += [f"Labor hours by gross: {hrs}", ""]
            for m in metrics:
                out += [f"**{m.replace('_cents', '').replace('_', ' ')}**", "",
                        "| bid \\ gross | " + " | ".join(f"${g:,}" for g in grosses) + " |",
                        "|---|" + "---|" * len(grosses)]
                for b in bids:
                    out.append(f"| ${b} | " + " | ".join(_money(idx[(size, sk, b * 100, g * 100)][m])
                                                     for g in grosses) + " |")
                out.append("")
        out += [f"### {size}: break-even realized gross", "",
                "| scenario | bid | cash | econ @$15/h | econ @$25/h | econ @$40/h |", "|---|---|---|---|---|---|"]
        for r in data["breakevens"]:
            if r["size"] == size:
                out.append(f"| {r['scenario']} | ${r['bid_cents'] // 100} | "
                           f"{_money(r['breakeven_gross_at_0_per_hour_cents'])} | "
                           f"{_money(r['breakeven_gross_at_15_per_hour_cents'])} | "
                           f"{_money(r['breakeven_gross_at_25_per_hour_cents'])} | "
                           f"{_money(r['breakeven_gross_at_40_per_hour_cents'])} |")
        out.append("")
    return "\n".join(out)
