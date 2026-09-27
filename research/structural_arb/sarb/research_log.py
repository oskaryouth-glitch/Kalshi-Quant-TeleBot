"""Append-only paper/research log. EVERY candidate inconsistency is recorded, passing or failing.

One JSON object per line. Decimals and Fractions are serialized as strings to avoid float loss.
Records are never rewritten; corrections are appended as new records referencing `candidate_id`.
"""
from __future__ import annotations

import gzip
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any

from . import config

SCHEMA_VERSION = 1

# Relationship classes
GUARANTEED = "GUARANTEED"      # locked payoff by contract definition (if rules verified)
STATISTICAL = "STATISTICAL"    # correlational; never scored as arbitrage

# Outcome statuses
EXECUTABLE = "GUARANTEED_STRUCTURAL_EXECUTABLE"
NOT_EXECUTABLE = "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"
STAT_ONLY = "STATISTICAL"
REJECTED = "REJECTED"


@dataclass
class LegRecord:
    ticker: str
    action: str                     # always 'buy' (taker) in this project
    side: str                       # 'yes' | 'no'
    qty: str
    best_ask: str | None
    vwap: str | None
    worst_price: str | None
    displayed_depth: str
    filled: str
    fee: str | None
    fee_alt_rounding: str | None
    sent_utc_ns: int
    recv_utc_ns: int
    book_format: str | None = None


@dataclass
class CandidateRecord:
    relationship: str               # R1_MEE_LONG, R2_MONOTONE, ...
    relationship_class: str         # GUARANTEED | STATISTICAL
    status: str                     # EXECUTABLE | NOT_EXECUTABLE | STATISTICAL | REJECTED
    reasons: list[str]              # why it passed / failed (every gate listed)
    event_tickers: list[str]
    size: str
    legs: list[LegRecord]
    gross_cost: str | None = None
    total_fees: str | None = None
    total_fees_alt_rounding: str | None = None
    locked_payoff: str | None = None           # None for STATISTICAL
    edge: str | None = None                    # locked_payoff - cost - fees
    edge_alt_rounding: str | None = None
    raw_inconsistency: str | None = None       # price-level violation before fees/depth
    max_executable_size: str | None = None     # largest C with edge > 0 (depth-walked)
    skew_ns: int | None = None
    age_ns: int | None = None
    days_to_settlement: str | None = None
    persistence_confirmed: bool | None = None
    settlement_evidence: dict = field(default_factory=dict)  # rules text hashes, strike fields
    snapshot_id: str | None = None
    candidate_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    logged_utc_ns: int = field(default_factory=time.time_ns)
    schema_version: int = SCHEMA_VERSION
    config_version: str = config.CONFIG_VERSION


def _default(o: Any):
    if isinstance(o, (Decimal, Fraction)):
        return str(o)
    if is_dataclass(o):
        return asdict(o)
    raise TypeError(type(o))


class ResearchLog:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self.counts: dict[str, int] = {}

    def write(self, rec: CandidateRecord) -> None:
        line = json.dumps(asdict(rec), default=_default, sort_keys=True)
        opener = gzip.open if self.path.endswith(".gz") else open
        with self._lock, opener(self.path, "at", encoding="utf-8") as fh:
            fh.write(line + "\n")
        self.counts[rec.status] = self.counts.get(rec.status, 0) + 1


def read(path: str):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)
