"""Pre-data analysis: hurdle rates implied by the cost model.

``required_gross`` answers: "for a unit of this size and contents profile,
how much base-case gross resale must it hold for the margin rules to allow
a bid of X?" Everything here is SIMULATED from config assumptions; nothing is
stored. Compare the hurdles with what lockers actually contain (once real
data exists) to see whether an edge is even plausible.
"""

from __future__ import annotations

import math
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
