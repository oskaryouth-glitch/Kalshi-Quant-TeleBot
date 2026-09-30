"""Assumptions panel: view and override config values.

Overrides are stored as append-only rows in ``assumption_sets``; the latest
row is the complete set in force. The effective config = YAML files + latest
overrides. Paper decisions embed the effective config they were made with
(model_versions), so changing an assumption only affects future decisions.
A separate, clearly labelled retrospective analysis (``retro``) can re-run
old estimates under current assumptions without storing anything.
"""

from __future__ import annotations

import copy
import json
import sqlite3
from dataclasses import dataclass

from .config import STATUS_LABELS, STATUSES, Assumptions, Config
from .db import transaction
from .money import parse_dollars
from .timeutil import now_ts

M = "markets.colorado_springs"
U = "underwriting"


@dataclass(frozen=True)
class Editable:
    path: str
    label: str
    kind: str  # cents | cents_per_mile | pct | number | minutes | schedule | int
    group: str


EDITABLE: tuple[Editable, ...] = (
    Editable(f"{U}.labor_value_cents_per_hour", "Value of your time ($/hour)", "cents", "Your time"),
    Editable(f"{U}.labor.minutes_per_listing", "Listing minutes per item", "minutes", "Your time"),
    Editable(f"{U}.labor.minutes_per_sale", "Selling minutes per completed sale", "minutes", "Your time"),
    Editable(f"{U}.labor.hours_per_vehicle_trip", "Hours per vehicle round trip", "number", "Your time"),
    Editable(f"{U}.operator_age", "Your age (rental eligibility)", "int", "Your time"),
    Editable(f"{M}.vehicles.friend_suv.per_mile_cents", "Borrowed SUV fuel + wear (per mile)", "cents_per_mile", "Vehicles"),
    Editable(f"{M}.vehicles.friend_suv.fixed_cents", "Borrowed SUV thank-you per day", "cents", "Vehicles"),
    Editable(f"{M}.vehicles.friend_pickup.per_mile_cents", "Borrowed pickup fuel + wear (per mile)", "cents_per_mile", "Vehicles"),
    Editable(f"{M}.vehicles.friend_pickup.fixed_cents", "Borrowed pickup thank-you per day", "cents", "Vehicles"),
    Editable(f"{M}.vehicles.friend_suv.available", "Friend's SUV realistically available (1/0)", "int", "Vehicles"),
    Editable(f"{M}.vehicles.friend_pickup.available", "Friend's pickup realistically available (1/0)", "int", "Vehicles"),
    Editable(f"{M}.vehicles.uhaul_cargo_van.fixed_cents", "U-Haul van base per day", "cents", "Vehicles"),
    Editable(f"{M}.vehicles.uhaul_cargo_van.per_mile_cents", "U-Haul van per mile incl. fuel", "cents_per_mile", "Vehicles"),
    Editable(f"{M}.vehicles.uhaul_cargo_van.insurance_cents", "U-Haul damage waiver + fees", "cents", "Vehicles"),
    Editable(f"{M}.vehicles.uhaul_10ft_truck.per_mile_cents", "U-Haul 10ft truck per mile incl. fuel", "cents_per_mile", "Vehicles"),
    Editable(f"{M}.home_to_unit_miles_default", "Default one-way miles to a facility", "number", "Vehicles"),
    Editable(f"{M}.sales_tax_rate", "Sales tax rate", "pct", "Fees and tax"),
    Editable(f"{U}.default_buyer_premium_rate", "Buyer premium when not shown", "pct", "Fees and tax"),
    Editable(f"{U}.selling_fee_rate", "Blended platform fee on resale", "pct", "Fees and tax"),
    Editable(f"{U}.local_sales_share", "Share of resale sold locally", "pct", "Fees and tax"),
    Editable(f"{U}.tax_regime", "Tax regime (licensed_reseller / informal)", "text", "Fees and tax"),
    Editable(f"{M}.disposal.weight_schedule", "Dump price by weight (lb:$, ...)", "schedule", "Disposal"),
    Editable(f"{M}.disposal.mattress_each_cents", "Mattress fee each", "cents", "Disposal"),
    Editable(f"{M}.disposal.lbs_per_cuft", "Trash density (lb per cubic foot)", "number", "Disposal"),
    Editable(f"{M}.disposal.free_household_trash_cuft", "Trash your household bins can absorb (cuft)", "number", "Disposal"),
    Editable(f"{U}.min_cash_profit_cents", "Minimum expected cash profit", "cents", "Margin of safety"),
    Editable(f"{U}.target_cash_roi", "Minimum cash ROI", "pct", "Margin of safety"),
    Editable(f"{U}.min_cash_profit_per_hour_cents", "Minimum cash profit per hour", "cents", "Margin of safety"),
    Editable(f"{U}.max_low_case_loss_cents", "Largest acceptable low-case cash loss", "cents", "Margin of safety"),
    Editable(f"{U}.valuation_haircut", "Valuation haircut (multiply your estimates by)", "number", "Margin of safety"),
    Editable(f"{U}.bankroll_cents", "Paper bankroll", "cents", "Margin of safety"),
)
EDITABLE_BY_PATH = {e.path: e for e in EDITABLE}


def _split(path: str) -> tuple[str, list[str]]:
    head, *rest = path.split(".")
    if head == "markets":
        return f"markets.{rest[0]}", rest[1:]
    if head == "underwriting":
        return "underwriting", rest
    raise KeyError(path)


def leaf(cfg: Config, path: str) -> dict:
    scope, keys = _split(path)
    node = cfg.underwriting.tree if scope == "underwriting" else cfg.market(scope.split(".")[1]).tree
    for k in keys:
        node = node[k]
    return node


def apply_overrides(base: Config, overrides: dict[str, dict]) -> Config:
    """New Config with override leaves swapped in. ``base`` is not modified."""
    uw = copy.deepcopy(base.underwriting.tree)
    markets = {k: copy.deepcopy(v.tree) for k, v in base.markets.items()}
    for path, new_leaf in overrides.items():
        scope, keys = _split(path)
        node = uw if scope == "underwriting" else markets[scope.split(".")[1]]
        for k in keys[:-1]:
            node = node[k]
        if keys[-1] not in node:
            raise KeyError(f"override for unknown assumption {path}")
        node[keys[-1]] = dict(new_leaf)
    return Config(sources=base.sources, markets={k: Assumptions(v) for k, v in markets.items()},
                  underwriting=Assumptions(uw))


def current_overrides(conn: sqlite3.Connection) -> tuple[int | None, dict[str, dict]]:
    row = conn.execute("SELECT id, overrides_json FROM assumption_sets ORDER BY id DESC LIMIT 1").fetchone()
    return (None, {}) if row is None else (row["id"], json.loads(row["overrides_json"]))


def effective_config(conn: sqlite3.Connection, base: Config) -> Config:
    return apply_overrides(base, current_overrides(conn)[1])


def parse_input(kind: str, text: str):
    t = text.strip()
    if kind in ("cents", "cents_per_mile"):
        return parse_dollars(t)
    if kind == "pct":
        v = float(t.rstrip("%"))
        if not 0 <= v <= 100:
            raise ValueError("percent must be 0-100")
        return round(v / 100, 6)
    if kind in ("number", "minutes"):
        v = float(t)
        if v < 0:
            raise ValueError("must be >= 0")
        return v
    if kind == "int":
        return int(t)
    if kind == "text":
        if t not in ("licensed_reseller", "informal"):
            raise ValueError("expected licensed_reseller or informal")
        return t
    if kind == "schedule":
        pts = []
        for part in t.split(","):
            lb, dollars = part.split(":")
            pts.append([float(lb), parse_dollars(dollars)])
        if any(b[0] <= a[0] or b[1] < a[1] for a, b in zip(pts, pts[1:])) or not pts:
            raise ValueError("points must ascend in weight and never decrease in price")
        return pts
    raise AssertionError(kind)


def format_value(kind: str, v) -> str:
    if v is None:
        return ""
    if kind in ("cents", "cents_per_mile"):
        return f"{v / 100:.2f}"
    if kind == "pct":
        return f"{v * 100:g}"
    if kind == "schedule":
        return ", ".join(f"{lb:g}:{c / 100:g}" for lb, c in v)
    return f"{v:g}" if isinstance(v, float) else str(v)


def save(conn: sqlite3.Connection, base: Config, changes: dict[str, tuple[str, str, str]],
         note: str = "", now: str | None = None) -> int | None:
    """Record a new assumption set. ``changes``: path -> (raw input, status, source note).
    Returns the new set id, or None if nothing actually changed."""
    _, overrides = current_overrides(conn)
    merged = dict(overrides)
    effective = apply_overrides(base, overrides)
    changed = False
    for path, (raw, status, source) in changes.items():
        e = EDITABLE_BY_PATH.get(path)
        if e is None:
            raise KeyError(f"{path} is not editable from the panel")
        if status not in STATUSES:
            raise ValueError(f"unknown status {status}")
        value = parse_input(e.kind, raw)
        old = leaf(effective, path)
        if value == old["value"] and status == old["status"] and (source or old.get("source")) == old.get("source"):
            continue
        merged[path] = {"value": value, "status": status,
                        "source": source or f"Set in assumptions panel (was {old['value']!r}, {old['status']})"}
        changed = True
    if not changed:
        return None
    apply_overrides(base, merged)  # validate the whole set before storing it
    with transaction(conn):
        return conn.execute(
            "INSERT INTO assumption_sets (created_at, overrides_json, note) VALUES (?, ?, ?)",
            (now or now_ts(), json.dumps(merged, sort_keys=True), note),
        ).lastrowid


def panel_rows(cfg: Config, overrides: dict[str, dict]) -> list[dict]:
    rows = []
    for e in EDITABLE:
        lf = leaf(cfg, e.path)
        rows.append({"path": e.path, "label": e.label, "group": e.group, "kind": e.kind,
                     "value": format_value(e.kind, lf["value"]), "status": lf["status"],
                     "status_label": STATUS_LABELS[lf["status"]], "source": lf.get("source", ""),
                     "overridden": e.path in overrides})
    return rows
