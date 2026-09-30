"""Disposal cost, pathways, and Disposal Burden.

v2 (2026-10 audit): the v1 Colorado Springs figure ($126.50/ton with a $253
two-ton minimum) turned out to be the Waste Connections transfer station's
*construction & demolition* rate, wrongly applied to household junk. Public
self-haul facilities in the area (Woodmen Dump, Peak Disposal) charge by
scale weight with no minimum, so v2 supports a tiered weight schedule
(``weight_schedule``) as well as the v1 minimum + per-ton rule.

Pathways (docs/AUDIT_2026-10.md §1), cheapest legitimate first:
  A negligible      a few cuft of trash; leaves with the operator's own garbage
  B household       fits spare household bin capacity over a couple of weeks
  C donate/recycle  free drop-off (ARC, Goodwill), county e-waste, scrap metal
  D small paid      a partial load at a weigh-and-pay public dump
  E dump run        a full vehicle load at the same dump
  F special items   mattresses, appliances, TVs: per-item fees
  G junk hauler     bulky items no available vehicle can carry
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from .money import cost_cents


@dataclass(frozen=True)
class DisposalRates:
    per_ton_cents: int
    minimum_charge_cents: int
    mattress_each_cents: int
    appliance_each_cents: int
    ewaste_each_cents: int
    lbs_per_cuft: float
    # [(lbs, cents), ...] ascending. When present it replaces minimum + per-ton:
    # linear between points, first point is the floor, last segment extrapolated.
    weight_schedule: tuple[tuple[float, int], ...] = ()
    negligible_trash_cuft: float = 0.0
    mattress_weight_lbs: float = 0.0  # mattresses also pay weight where the fee is "+ weight"

    @classmethod
    def from_config(cls, d: dict) -> "DisposalRates":
        sched = tuple((float(lb), int(c)) for lb, c in d.get("weight_schedule") or ())
        if any(b[0] <= a[0] or b[1] < a[1] for a, b in zip(sched, sched[1:])):
            raise ValueError("weight_schedule must be strictly ascending in lbs and non-decreasing in price")
        return cls(
            per_ton_cents=int(d["per_ton_cents"]),
            minimum_charge_cents=int(d["minimum_charge_cents"]),
            mattress_each_cents=int(d["mattress_each_cents"]),
            appliance_each_cents=int(d["appliance_each_cents"]),
            ewaste_each_cents=int(d["ewaste_each_cents"]),
            lbs_per_cuft=float(d["lbs_per_cuft"]),
            weight_schedule=sched,
            negligible_trash_cuft=float(d.get("negligible_trash_cuft", 0.0)),
            mattress_weight_lbs=float(d.get("mattress_weight_lbs", 0.0)),
        )

    def visit_charge_cents(self, lbs: float) -> int:
        """Gate charge for one visit carrying ``lbs``."""
        if lbs <= 0:
            return 0
        if not self.weight_schedule:
            return max(self.minimum_charge_cents, cost_cents(lbs / 2000 * self.per_ton_cents))
        pts = self.weight_schedule
        if lbs <= pts[0][0] or len(pts) == 1:
            return pts[0][1]
        i = bisect.bisect_left([p[0] for p in pts], lbs)
        (x0, y0), (x1, y1) = (pts[i - 1], pts[i]) if i < len(pts) else (pts[-2], pts[-1])
        return cost_cents(y0 + (y1 - y0) * (lbs - x0) / (x1 - x0))


@dataclass(frozen=True)
class DisposalInput:
    trash_cuft: float
    mattresses: int = 0
    appliances: int = 0
    ewaste_items: int = 0
    bulky_items: int = 0  # couches, large furniture: labor + volume burden


@dataclass(frozen=True)
class DisposalEstimate:
    visits: int
    weight_lbs: float
    load_fees_cents: int
    item_fees_cents: int
    burden_score: float  # 0 (none) .. 100 (severe); display heuristic only
    burden_level: str
    pathways: tuple[str, ...] = field(default=())

    @property
    def total_cents(self) -> int:
        return self.load_fees_cents + self.item_fees_cents


def split_trash(trash_cuft: float, rates: DisposalRates,
                household_allowance_cuft: float = 0.0) -> tuple[float, float, str | None]:
    """(cuft that goes home as household garbage, cuft that must go to a dump,
    pathway A/B used or None)."""
    if 0 < trash_cuft <= rates.negligible_trash_cuft:
        return trash_cuft, 0.0, "A_negligible"
    if trash_cuft > 0 and household_allowance_cuft > 0:
        home = min(trash_cuft, household_allowance_cuft)
        return home, trash_cuft - home, "B_household"
    return 0.0, trash_cuft, None


def estimate(d: DisposalInput, rates: DisposalRates, dump_visits: int,
             household_allowance_cuft: float = 0.0) -> DisposalEstimate:
    """Cheapest legitimate pathway mix for this locker's trash.

    ``household_allowance_cuft`` is pathway B capacity (0 unless the operator
    really has spare bin space). Donations (C) are free and handled by the
    caller's volumes; this function prices what must be thrown away.
    """
    paths: list[str] = []
    _, trash, home_path = split_trash(d.trash_cuft, rates, household_allowance_cuft)
    if home_path:
        paths.append(home_path)
    has_special = d.mattresses > 0 or d.appliances > 0
    visits = max(dump_visits, 1) if (trash > 0 or has_special) else 0
    weight = trash * rates.lbs_per_cuft + d.mattresses * rates.mattress_weight_lbs
    load_fees = 0
    if visits:
        per_visit = weight / visits
        load_fees = visits * rates.visit_charge_cents(per_visit) if weight > 0 else 0
        if not rates.weight_schedule and weight <= 0:
            load_fees = visits * rates.minimum_charge_cents  # v1: minimum applies even to item-only visits
        paths.append("D_small_paid" if trash * rates.lbs_per_cuft < 500 else "E_dump_run")
    item_fees = (
        d.mattresses * rates.mattress_each_cents
        + d.appliances * rates.appliance_each_cents
        + d.ewaste_items * rates.ewaste_each_cents
    )
    if has_special or d.ewaste_items:
        paths.append("F_special_items")
    # Heuristic score; the dollar estimate above is what underwriting uses.
    score = min(
        100.0,
        d.trash_cuft / 3 + 15 * d.mattresses + 10 * d.appliances + 8 * d.bulky_items + 2 * d.ewaste_items,
    )
    level = "LOW" if score < 20 else "MEDIUM" if score < 50 else "HIGH"
    return DisposalEstimate(visits, weight, load_fees, item_fees, score, level, tuple(paths))
