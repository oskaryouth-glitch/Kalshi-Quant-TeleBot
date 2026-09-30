"""Timestamps.

Every timestamp stored by lockerlab is a UTC string in one fixed-width format
(``YYYY-MM-DDTHH:MM:SS.ffffffZ``) so that SQL string comparison is identical to
chronological comparison. Point-in-time queries rely on this property.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def to_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError(f"naive datetime {dt!r}: a timezone is required")
    return dt.astimezone(timezone.utc).strftime(_FMT)


def from_ts(ts: str) -> datetime:
    return datetime.strptime(ts, _FMT).replace(tzinfo=timezone.utc)


def now_ts() -> str:
    return to_ts(datetime.now(timezone.utc))


def parse_user_time(text: str, default_tz: str) -> str:
    """Parse a user/source-supplied time into a canonical UTC timestamp.

    Accepts ISO-8601 with or without offset (``2026-10-04T14:00``,
    ``2026-10-04 14:00:00-06:00``, ``...Z``). A value without an offset is
    interpreted in ``default_tz`` (the market's local zone), because auction
    sites display local facility time.
    """
    s = text.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(default_tz))
    return to_ts(dt)
