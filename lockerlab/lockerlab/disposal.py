"""Disposal cost and Disposal Burden.

Dump fees are charged per visit: max(minimum charge, weight * per-ton rate).
A per-visit minimum matters enormously for small operators: a $253 minimum
(the sourced Colorado Springs transfer-station figure, still to be confirmed
by phone) can exceed the winning bid on a 5x5.
"""

from __future__ import annotations

from dataclasses import dataclass

from .money import cost_cents


@dataclass(frozen=True)
class DisposalRates:
    per_ton_cents: int
    minimum_charge_cents: int
    mattress_each_cents: int
    appliance_each_cents: int
    ewaste_each_cents: int
    lbs_per_cuft: float

    @classmethod
    def from_config(cls, d: dict) -> "DisposalRates":
        return cls(
            per_ton_cents=int(d["per_ton_cents"]),
            minimum_charge_cents=int(d["minimum_charge_cents"]),
            mattress_each_cents=int(d["mattress_each_cents"]),
            appliance_each_cents=int(d["appliance_each_cents"]),
            ewaste_each_cents=int(d["ewaste_each_cents"]),
            lbs_per_cuft=float(d["lbs_per_cuft"]),
        )


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

    @property
    def total_cents(self) -> int:
        return self.load_fees_cents + self.item_fees_cents


def estimate(d: DisposalInput, rates: DisposalRates, dump_visits: int) -> DisposalEstimate:
    has_load = d.trash_cuft > 0 or d.mattresses > 0 or d.appliances > 0
    visits = max(dump_visits, 1) if has_load else 0
    weight = d.trash_cuft * rates.lbs_per_cuft
    load_fees = 0
    if visits:
        per_visit_tons = weight / 2000 / visits
        load_fees = visits * max(
            rates.minimum_charge_cents, cost_cents(per_visit_tons * rates.per_ton_cents)
        )
    item_fees = (
        d.mattresses * rates.mattress_each_cents
        + d.appliances * rates.appliance_each_cents
        + d.ewaste_items * rates.ewaste_each_cents
    )
    # Heuristic score; the dollar estimate above is what underwriting uses.
    score = min(
        100.0,
        d.trash_cuft / 3 + 15 * d.mattresses + 10 * d.appliances + 8 * d.bulky_items + 2 * d.ewaste_items,
    )
    level = "LOW" if score < 20 else "MEDIUM" if score < 50 else "HIGH"
    return DisposalEstimate(visits, weight, load_fees, item_fees, score, level)
