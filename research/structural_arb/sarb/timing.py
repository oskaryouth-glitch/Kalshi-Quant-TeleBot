"""Timestamp gates: reject stale or asynchronous multi-leg comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from . import config


@dataclass(frozen=True)
class LegTiming:
    ticker: str
    sent_utc_ns: int
    recv_utc_ns: int


@dataclass(frozen=True)
class TimingVerdict:
    ok: bool
    skew_ns: int
    age_ns: int
    reasons: tuple[str, ...]


def check(legs: Sequence[LegTiming], now_utc_ns: int,
          max_skew_ns: int = config.MAX_LEG_SKEW_NS,
          max_age_ns: int = config.MAX_SNAPSHOT_AGE_NS) -> TimingVerdict:
    """skew = latest response-received minus earliest request-sent across all legs: the widest
    window in which the displayed books could have been observed. age = now minus the earliest
    response-received (oldest information used)."""
    if not legs:
        return TimingVerdict(False, 0, 0, ("NO_LEGS",))
    reasons = []
    for lg in legs:
        if lg.recv_utc_ns < lg.sent_utc_ns:
            reasons.append(f"CLOCK_ANOMALY:{lg.ticker}")
    skew = max(l.recv_utc_ns for l in legs) - min(l.sent_utc_ns for l in legs)
    age = now_utc_ns - min(l.recv_utc_ns for l in legs)
    if skew > max_skew_ns:
        reasons.append("SKEW")
    if age > max_age_ns:
        reasons.append("STALE")
    if age < 0:
        reasons.append("FUTURE_TIMESTAMP")
    return TimingVerdict(not reasons, skew, age, tuple(reasons))
