"""Manual capture ingestion.

Because the major auction platforms prohibit automated collection (see
config/sources.yaml), the Phase-1 ingestion path is: Oskar looks at an auction
in his browser and records what he sees in a CSV row (spreadsheet-friendly,
one row per auction per look). This module validates that file, stores the
file itself as immutable raw evidence, and turns each row into an
append-only observation.

Rules:
  * An import is all-or-nothing: any invalid row rejects the whole file with
    every error listed, so nothing half-imports.
  * Re-importing an identical file is a no-op (same sha256).
  * Unknown columns are errors (a typo must not silently drop data).
  * Columns that would hold an occupant's name are refused outright.
  * A blank observed_at defaults to the import time. That can only make data
    look *later* than it was, which is the safe direction for look-ahead.
"""

from __future__ import annotations

import csv
import hashlib
import io
import mimetypes
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config, canonical_json
from .db import transaction
from .labels import Label
from .money import parse_dollars
from .pit import TERMINAL_STATUSES, find_auction
from .rawstore import RawStore
from .timeutil import now_ts, parse_user_time
from .units import parse_size, size_bucket

PARSER_VERSION = "manual_csv_v1"

STATUSES = ("scheduled", "active", "closed", "sold", "cancelled", "unsold", "unknown")

# column -> parser kind
COLUMNS: dict[str, str] = {
    "source": "str",
    "external_id": "str",
    "url": "str",
    "observed_at": "time",
    "status": "status",
    "facility_name": "str",
    "facility_operator": "str",
    "address": "str",
    "city": "str",
    "state": "str",
    "postal_code": "str",
    "distance_miles": "float",
    "unit_label": "str",
    "unit_size": "size",
    "height_ft": "float",
    "current_bid": "money",
    "opening_bid": "money",
    "bid_count": "int",
    "starts_at": "time",
    "ends_at": "time",
    "buyer_premium_pct": "pct",
    "buyer_premium_min": "money",
    "purchase_deposit_pct": "pct",
    "cleaning_deposit": "money",
    "sales_tax_pct": "pct",
    "cleanout_hours": "float",
    "payment_methods": "str",
    "photo_count": "int",
    "description": "str",
    "facility_rules": "str",
    "access_constraints": "str",
    "final_price": "money",
    "uncertain_fields": "list",
    "notes": "str",
}
REQUIRED = ("source", "external_id", "status")
FORBIDDEN = {"occupant", "occupant_name", "tenant", "tenant_name", "customer", "customer_name", "name"}

# CSV column -> auction_observations column (where they differ)
_DB_NAME = {
    "current_bid": "current_bid_cents",
    "opening_bid": "opening_bid_cents",
    "buyer_premium_pct": "buyer_premium_rate",
    "buyer_premium_min": "buyer_premium_min_cents",
    "purchase_deposit_pct": "purchase_deposit_rate",
    "cleaning_deposit": "cleaning_deposit_cents",
    "sales_tax_pct": "sales_tax_rate",
    "final_price": "final_price_cents",
}
_NOT_OBSERVATION_COLS = {"source", "external_id", "unit_size", "uncertain_fields", "notes", "observed_at", "status"}

EXAMPLE_ROW = {
    "source": "storagetreasures",
    "external_id": "EXAMPLE-123456",
    "url": "https://www.example.com/auction/123456",
    "observed_at": "2026-10-01 19:30",
    "status": "active",
    "facility_name": "Example Self Storage",
    "facility_operator": "Example Co",
    "city": "Colorado Springs",
    "state": "CO",
    "postal_code": "80909",
    "distance_miles": "6",
    "unit_label": "B112",
    "unit_size": "5x10",
    "current_bid": "45",
    "bid_count": "3",
    "ends_at": "2026-10-04 14:00",
    "buyer_premium_pct": "18",
    "buyer_premium_min": "10",
    "cleaning_deposit": "100",
    "cleanout_hours": "72",
    "photo_count": "6",
    "description": "totes, bike, tool bag, boxes",
    "uncertain_fields": "bid_count",
}


class CaptureError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass
class ImportResult:
    raw_capture_id: int | None
    already_imported: bool
    observations: int = 0
    new_auctions: int = 0
    warnings: list[str] = field(default_factory=list)


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(COLUMNS))
    w.writeheader()
    w.writerow(EXAMPLE_ROW)
    return buf.getvalue()


def _parse_value(kind: str, raw: str, tz: str):
    if kind == "str":
        return raw
    if kind == "int":
        v = int(raw)
        if v < 0:
            raise ValueError("must be >= 0")
        return v
    if kind == "float":
        v = float(raw)
        if v < 0:
            raise ValueError("must be >= 0")
        return v
    if kind == "money":
        v = parse_dollars(raw)
        if v < 0:
            raise ValueError("must be >= 0")
        return v
    if kind == "pct":
        v = float(raw.rstrip("%").strip())
        if not 0 <= v <= 100:
            raise ValueError("percent must be 0-100")
        if 0 < v < 1:
            raise ValueError(f"ambiguous percent {raw!r}: write 15 for 15%, not 0.15")
        return v / 100
    if kind == "time":
        return parse_user_time(raw, tz)
    if kind == "status":
        v = raw.lower()
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        return v
    if kind == "size":
        return parse_size(raw)
    if kind == "list":
        return [x.strip() for x in raw.replace(",", ";").split(";") if x.strip()]
    raise AssertionError(kind)


@dataclass
class _Row:
    line: int
    source: str
    external_id: str
    observed_at: str
    observed_at_defaulted: bool
    status: str
    obs: dict
    raw: dict
    meta: dict


def _parse_rows(text: str, cfg: Config, market_key: str, recorded_at: str) -> tuple[list[_Row], list[str]]:
    tz = cfg.market(market_key).get("timezone")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    errors: list[str] = []
    forbidden = sorted(set(h.lower() for h in header) & FORBIDDEN)
    if forbidden:
        return [], [f"refusing columns that hold personal names: {forbidden}. Never record occupant names."]
    unknown = sorted(set(header) - set(COLUMNS))
    if unknown:
        return [], [f"unknown columns {unknown}; allowed: {list(COLUMNS)}"]
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        return [], [f"missing required columns {missing}"]

    rows: list[_Row] = []
    for i, rec in enumerate(reader, start=2):
        if rec.get(None):  # csv puts surplus values under the None key
            errors.append(f"line {i}: more values than columns (unquoted comma?): {rec[None]}")
            continue
        raw = {k.strip(): (v or "").strip() for k, v in rec.items() if k is not None}
        if not any(raw.values()):
            continue
        parsed, row_err = {}, []
        for col, val in raw.items():
            if val == "":
                continue
            try:
                parsed[col] = _parse_value(COLUMNS[col], val, tz)
            except ValueError as e:
                row_err.append(f"line {i}: {col}={val!r}: {e}")
        for col in REQUIRED:
            if not raw.get(col):
                row_err.append(f"line {i}: {col} is required")
        if parsed.get("source") and parsed["source"] not in cfg.sources:
            row_err.append(f"line {i}: unknown source {parsed['source']!r}; add it to config/sources.yaml")
        observed_at = parsed.get("observed_at", recorded_at)
        if observed_at > recorded_at:
            row_err.append(f"line {i}: observed_at {observed_at} is in the future")
        status = parsed.get("status")
        if status == "sold" and "final_price" not in parsed:
            row_err.append(f"line {i}: status sold requires final_price")
        if "final_price" in parsed and status != "sold":
            row_err.append(f"line {i}: final_price given but status is {status!r}, not sold")
        if "final_price" in parsed and "current_bid" in parsed and parsed["current_bid"] > parsed["final_price"]:
            row_err.append(f"line {i}: current_bid exceeds final_price")
        uncertain = set(parsed.get("uncertain_fields", []))
        bad_uncertain = uncertain - set(COLUMNS)
        if bad_uncertain:
            row_err.append(f"line {i}: uncertain_fields names unknown columns {sorted(bad_uncertain)}")
        if row_err:
            errors.extend(row_err)
            continue

        obs: dict = {}
        meta: dict = {}
        for col, val in parsed.items():
            if col in _NOT_OBSERVATION_COLS:
                continue
            obs[_DB_NAME.get(col, col)] = val
        for col in parsed:
            if col in ("uncertain_fields", "notes"):
                continue
            meta[col] = {"label": Label.OBSERVED.value, "confidence": 0.5 if col in uncertain else 1.0}
        if "unit_size" in parsed:
            w, l, h = parsed["unit_size"]
            obs["width_ft"], obs["length_ft"] = w, l
            if h is not None and "height_ft" not in obs:
                obs["height_ft"] = h
            obs["size_bucket"] = size_bucket(w, l)
            meta["size_bucket"] = {"label": Label.INFERRED.value, "confidence": meta["unit_size"]["confidence"]}
        if "observed_at" not in parsed:
            meta["observed_at"] = {"label": "DEFAULTED_TO_IMPORT_TIME", "confidence": 1.0}
        rows.append(_Row(i, parsed["source"], parsed["external_id"], observed_at,
                         "observed_at" not in parsed, status, obs, raw, meta))
    if not rows and not errors:
        errors.append("file contains no data rows")
    return rows, errors


def register_sources(conn: sqlite3.Connection, cfg: Config) -> None:
    with transaction(conn):
        for key, s in cfg.sources.items():
            conn.execute(
                "INSERT OR IGNORE INTO sources (source_key, name, base_url, created_at) VALUES (?, ?, ?, ?)",
                (key, s.get("name", key), s.get("base_url"), now_ts()),
            )


def _store_raw(conn, store: RawStore, data: bytes, source_key: str, method: str, content_type: str,
               recorded_at: str, captured_by: str | None, source_url: str | None = None,
               notes: str | None = None) -> int:
    sha, rel = store.put(data)
    cur = conn.execute(
        """INSERT INTO raw_captures (source_key, source_url, capture_method, recorded_at,
               content_sha256, content_path, content_type, byte_size, captured_by, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_key, source_url, method, recorded_at, sha, rel, content_type, len(data), captured_by, notes),
    )
    return cur.lastrowid


def import_csv(conn: sqlite3.Connection, store: RawStore, cfg: Config, path: Path,
               market_key: str, captured_by: str | None = None, now: str | None = None) -> ImportResult:
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    prior = conn.execute(
        "SELECT id FROM raw_captures WHERE content_sha256 = ? AND capture_method = 'manual_csv'", (sha,)
    ).fetchone()
    if prior:
        return ImportResult(prior["id"], already_imported=True)

    recorded_at = now or now_ts()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise CaptureError([f"file is not UTF-8: {e}"]) from e
    rows, errors = _parse_rows(text, cfg, market_key, recorded_at)
    if errors:
        raise CaptureError(errors)

    result = ImportResult(None, already_imported=False)
    register_sources(conn, cfg)
    with transaction(conn):
        # A file can mix sources; attribute the capture to the first row's source.
        raw_id = _store_raw(conn, store, data, rows[0].source, "manual_csv", "text/csv",
                            recorded_at, captured_by, notes=f"file={Path(path).name}")
        result.raw_capture_id = raw_id
        for r in rows:
            aid = find_auction(conn, r.source, r.external_id)
            if aid is None:
                aid = conn.execute(
                    "INSERT INTO auctions (source_key, external_id, market_key, first_recorded_at) VALUES (?, ?, ?, ?)",
                    (r.source, r.external_id, market_key, recorded_at),
                ).lastrowid
                result.new_auctions += 1
            else:
                existing = conn.execute("SELECT market_key FROM auctions WHERE id = ?", (aid,)).fetchone()
                if existing["market_key"] != market_key:
                    raise CaptureError([f"line {r.line}: auction already recorded in market {existing['market_key']!r}"])
                prior_terminal = conn.execute(
                    f"SELECT status FROM auction_observations WHERE auction_id = ? AND status IN "
                    f"({','.join('?' * len(TERMINAL_STATUSES))}) LIMIT 1",
                    (aid, *TERMINAL_STATUSES),
                ).fetchone()
                if prior_terminal and r.status not in TERMINAL_STATUSES:
                    result.warnings.append(
                        f"line {r.line}: {r.source}/{r.external_id} was already {prior_terminal['status']}; "
                        f"now {r.status} (relisted?)"
                    )
            if r.observed_at_defaulted:
                result.warnings.append(f"line {r.line}: observed_at blank, defaulted to import time")
            ends = r.obs.get("ends_at")
            if ends and r.status in ("active", "scheduled") and ends < r.observed_at:
                result.warnings.append(f"line {r.line}: status {r.status} but ends_at is before observed_at")
            cols = ["auction_id", "raw_capture_id", "observed_at", "recorded_at", "parser_version",
                    "status", "raw_fields_json", "field_meta_json", *r.obs.keys()]
            vals = [aid, raw_id, r.observed_at, recorded_at, PARSER_VERSION, r.status,
                    canonical_json(r.raw), canonical_json(r.meta), *r.obs.values()]
            conn.execute(
                f"INSERT INTO auction_observations ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                vals,
            )
            result.observations += 1
    return result


def import_photos(conn: sqlite3.Connection, store: RawStore, source_key: str, external_id: str,
                  observed_at: str, paths: list[Path], captured_by: str | None = None,
                  now: str | None = None) -> tuple[int, int]:
    """Attach auction photos saved from the listing. Returns (added, skipped)."""
    recorded_at = now or now_ts()
    if observed_at > recorded_at:
        raise CaptureError([f"observed_at {observed_at} is in the future"])
    aid = find_auction(conn, source_key, external_id)
    if aid is None:
        raise CaptureError([f"unknown auction {source_key}/{external_id}; import its CSV row first"])
    added = skipped = 0
    with transaction(conn):
        for pos, p in enumerate(paths):
            data = Path(p).read_bytes()
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            if not ctype.startswith("image/"):
                raise CaptureError([f"{p}: not an image ({ctype})"])
            sha = hashlib.sha256(data).hexdigest()
            if conn.execute("SELECT 1 FROM images WHERE auction_id = ? AND sha256 = ?", (aid, sha)).fetchone():
                skipped += 1
                continue
            raw_id = _store_raw(conn, store, data, source_key, "manual_photo", ctype, recorded_at, captured_by)
            conn.execute(
                """INSERT INTO images (auction_id, raw_capture_id, observed_at, recorded_at, sha256,
                       original_name, position) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (aid, raw_id, observed_at, recorded_at, sha, Path(p).name, pos),
            )
            added += 1
    return added, skipped
