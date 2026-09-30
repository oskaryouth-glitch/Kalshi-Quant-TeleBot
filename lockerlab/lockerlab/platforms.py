"""Auction URL recognition and per-source capture policy.

Only the URL string you paste is parsed; nothing is fetched. The auction ID is
taken from the URL only when it is unambiguous (one query parameter named like
an ID, or exactly one long digit run in the path). Otherwise the capture
screen asks you for it: it is never guessed.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit, urlunsplit

HOSTS = {
    "storagetreasures.com": "storagetreasures",
    "lockerfox.com": "lockerfox",
    "storageauctions.com": "storageauctions_com",
    "storageauctions.net": "storageauctions_com",
    "bid13.com": "bid13",
    "ibid4storage.com": "ibid4storage",
    "publicstorageauctions.com": "publicstorage_notices",
    "cubesmart.com": "cubesmart_schedule",
}
ID_PARAMS = ("auctionid", "auction_id", "id", "lotid", "lot_id", "unitid")
_DIGITS = re.compile(r"(?<!\d)(\d{4,})(?!\d)")


@dataclass(frozen=True)
class UrlInfo:
    normalized_url: str | None
    source_key: str | None
    external_id: str | None
    evidence: str


def parse_url(url: str) -> UrlInfo:
    u = (url or "").strip()
    if not u:
        return UrlInfo(None, None, None, "no URL given")
    if "://" not in u:
        u = "https://" + u
    parts = urlsplit(u)
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return UrlInfo(None, None, None, f"not a URL: {url!r}")
    source = next((k for h, k in HOSTS.items() if host == h or host.endswith("." + h)), None)
    # Keep the path and query, drop fragments and tracking parameters.
    query = "&".join(p for p in parts.query.split("&") if p and not p.lower().startswith(("utm_", "fbclid", "gclid")))
    norm = urlunsplit(("https", host, parts.path.rstrip("/") or "/", query, ""))

    qs = {k.lower(): v for k, v in parse_qs(parts.query).items()}
    for p in ID_PARAMS:
        if p in qs and len(qs[p]) == 1 and qs[p][0].strip():
            return UrlInfo(norm, source, qs[p][0].strip(), f"query parameter {p}={qs[p][0]}")
    runs = _DIGITS.findall(parts.path)
    if len(runs) == 1:
        return UrlInfo(norm, source, runs[0], f"the only long number in the URL path ({runs[0]})")
    if len(runs) > 1:
        return UrlInfo(norm, source, None, f"several numbers in the path {runs}: enter the auction ID yourself")
    return UrlInfo(norm, source, None, "no auction ID in the URL: enter it yourself")


@dataclass(frozen=True)
class CapturePolicy:
    source_key: str
    screenshot_policy: str  # allowed | manual_only
    reason: str
    decided_by: str  # config | event #id


def capture_policy(conn: sqlite3.Connection, sources: dict, source_key: str) -> CapturePolicy:
    """Latest recorded policy event for the source, else the config default.
    Unknown sources are manual-only."""
    src = sources.get(source_key)
    if src is None:
        return CapturePolicy(source_key, "manual_only", "unknown source", "default")
    row = conn.execute(
        "SELECT * FROM source_policy_events WHERE source_key = ? ORDER BY id DESC LIMIT 1", (source_key,)
    ).fetchone()
    if row is not None:
        return CapturePolicy(source_key, row["screenshot_policy"], f"{row['basis']}: {row['note']}",
                             f"event #{row['id']} at {row['recorded_at']}")
    pol = src.get("screenshot_policy", "manual_only")
    if pol not in ("allowed", "manual_only"):
        pol = "manual_only"
    return CapturePolicy(source_key, pol, src.get("screenshot_policy_reason", ""), "config")


def set_policy(conn: sqlite3.Connection, sources: dict, source_key: str, policy: str, basis: str,
               note: str, now: str) -> int:
    if source_key not in sources:
        raise KeyError(f"unknown source {source_key}")
    if policy not in ("allowed", "manual_only"):
        raise ValueError("policy must be allowed or manual_only")
    if not note.strip():
        raise ValueError("record why (e.g. 'written permission from support, 2026-10-05, ticket 123')")
    return conn.execute(
        "INSERT INTO source_policy_events (source_key, recorded_at, screenshot_policy, basis, note)"
        " VALUES (?, ?, ?, ?, ?)", (source_key, now, policy, basis, note.strip()),
    ).lastrowid
