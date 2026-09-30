"""Transportation model: which vehicles can clear a unit, in how many trips,
at what cost. Every vehicle parameter comes from config (mostly GUESS today).

Simplifications (documented, to be replaced with measured data):
  * all trips happen within one rental/borrow period
  * packing efficiency is the fraction of a vehicle's nominal cargo volume a
    loose storage-unit load actually fills (irregular items waste space)
  * trips carrying trash detour to the dump; donations go to a drop-off
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .money import cost_cents

DEFAULT_PACKING_EFFICIENCY = 0.65
DEFAULT_MAX_TRIPS = 4  # beyond this, a cleanout deadline is at serious risk


@dataclass(frozen=True)
class Vehicle:
    key: str
    usable_cuft: float
    max_item_length_in: float
    fixed_cents: int
    per_mile_cents: int
    per_hour_cents: int = 0
    included_hours: float = 0.0
    insurance_cents: int = 0
    available: bool = True

    @classmethod
    def from_config(cls, key: str, d: dict) -> "Vehicle":
        return cls(
            key=key,
            usable_cuft=float(d["usable_cuft"]),
            max_item_length_in=float(d["max_item_length_in"]),
            fixed_cents=int(d["fixed_cents"]),
            per_mile_cents=int(d["per_mile_cents"]),
            per_hour_cents=int(d.get("per_hour_cents", 0)),
            included_hours=float(d.get("included_hours", 0.0)),
            insurance_cents=int(d.get("insurance_cents", 0)),
            available=bool(d.get("available", True)),
        )


@dataclass(frozen=True)
class Load:
    retained_cuft: float
    donate_cuft: float
    trash_cuft: float
    longest_item_in: float = 0.0

    @property
    def total_cuft(self) -> float:
        return self.retained_cuft + self.donate_cuft + self.trash_cuft


@dataclass(frozen=True)
class TransportOption:
    vehicle: str
    feasible: bool
    reason: str
    trips: int
    dump_trips: int
    miles: float
    hours: float
    cost_cents: int


def plan(
    load: Load,
    vehicles: list[Vehicle],
    one_way_miles: float,
    dump_round_trip_miles: float,
    hours_per_trip: float,
    packing_efficiency: float = DEFAULT_PACKING_EFFICIENCY,
    max_trips: int = DEFAULT_MAX_TRIPS,
) -> list[TransportOption]:
    """All vehicle options, cheapest feasible first."""
    if not 0 < packing_efficiency <= 1:
        raise ValueError("packing_efficiency must be in (0, 1]")
    out = []
    for v in vehicles:
        cap = v.usable_cuft * packing_efficiency
        trips = max(1, math.ceil(load.total_cuft / cap)) if load.total_cuft > 0 else 0
        dump_trips = math.ceil(load.trash_cuft / cap) if load.trash_cuft > 0 else 0
        miles = trips * 2 * one_way_miles + dump_trips * dump_round_trip_miles
        hours = trips * hours_per_trip
        billable_hours = max(0.0, hours - v.included_hours)
        cost = (
            v.fixed_cents + v.insurance_cents + cost_cents(miles * v.per_mile_cents)
            + cost_cents(billable_hours * v.per_hour_cents)
        ) if trips else 0
        if not v.available:
            feasible, reason = False, "not available"
        elif load.longest_item_in > v.max_item_length_in:
            feasible, reason = False, f"longest item {load.longest_item_in:.0f}in > {v.max_item_length_in:.0f}in"
        elif trips > max_trips:
            feasible, reason = False, f"{trips} trips > max {max_trips}"
        else:
            feasible, reason = True, "ok"
        out.append(TransportOption(v.key, feasible, reason, trips, dump_trips, miles, hours, cost))
    out.sort(key=lambda o: (not o.feasible, o.cost_cents, o.trips))
    return out


def best(options: list[TransportOption]) -> TransportOption | None:
    return next((o for o in options if o.feasible), None)
