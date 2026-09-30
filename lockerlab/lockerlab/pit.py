"""Point-in-time reads: the ONLY way decision code may see auction data.

``snapshot_as_of(conn, auction_id, t)`` returns the latest observation that
was both *observed* and *recorded* at or before ``t``. Requiring
recorded_at <= t is what prevents look-ahead: a row typed in tomorrow can't
influence a decision stamped today, even if it claims an earlier observed_at.

Strategies receive a frozen ``Snapshot``, never a DB connection, so they
cannot reach around this function.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, fields

TERMINAL_STATUSES = ("closed", "sold", "cancelled", "unsold")
OPEN_STATUSES = ("scheduled", "active")


@dataclass(frozen=True)
class Snapshot:
    auction_id: int
    source_key: str
    external_id: str
    market_key: str
    observation_id: int
    observed_at: str
    recorded_at: str
    status: str
    url: str | None
    facility_name: str | None
    facility_operator: str | None
    city: str | None
    state: str | None
    distance_miles: float | None
    width_ft: float | None
    length_ft: float | None
    height_ft: float | None
    size_bucket: str | None
    current_bid_cents: int | None
    opening_bid_cents: int | None
    bid_count: int | None
    ends_at: str | None
    buyer_premium_rate: float | None
    buyer_premium_min_cents: int | None
    purchase_deposit_rate: float | None
    cleaning_deposit_cents: int | None
    sales_tax_rate: float | None
    cleanout_hours: float | None
    photo_count: int | None
    description: str | None
    access_constraints: str | None
    as_of: str

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


_SNAPSHOT_COLS = [
    f.name for f in fields(Snapshot)
    if f.name not in {"auction_id", "source_key", "external_id", "market_key", "observation_id", "as_of"}
]


def snapshot_as_of(conn: sqlite3.Connection, auction_id: int, as_of: str) -> Snapshot | None:
    cols = ", ".join(f"o.{c}" for c in _SNAPSHOT_COLS)
    row = conn.execute(
        f"""SELECT a.id AS auction_id, a.source_key, a.external_id, a.market_key,
                   o.id AS observation_id, {cols}
            FROM auction_observations o JOIN auctions a ON a.id = o.auction_id
            WHERE o.auction_id = ? AND o.observed_at <= ? AND o.recorded_at <= ?
            ORDER BY o.observed_at DESC, o.id DESC LIMIT 1""",
        (auction_id, as_of, as_of),
    ).fetchone()
    return None if row is None else Snapshot(**dict(row), as_of=as_of)


def terminal_observation_as_of(conn: sqlite3.Connection, auction_id: int, as_of: str):
    """Earliest-known terminal observation recorded by ``as_of`` (or None)."""
    return conn.execute(
        f"""SELECT * FROM auction_observations
            WHERE auction_id = ? AND recorded_at <= ? AND observed_at <= ?
              AND status IN ({",".join("?" * len(TERMINAL_STATUSES))})
            ORDER BY observed_at ASC, id ASC LIMIT 1""",
        (auction_id, as_of, as_of, *TERMINAL_STATUSES),
    ).fetchone()


def find_auction(conn: sqlite3.Connection, source_key: str, external_id: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM auctions WHERE source_key = ? AND external_id = ?",
        (source_key, external_id),
    ).fetchone()
    return None if row is None else row["id"]
