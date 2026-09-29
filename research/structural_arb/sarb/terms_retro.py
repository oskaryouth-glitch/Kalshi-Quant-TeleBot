"""Retroactive, DEMOTE-ONLY re-evaluation of recorded lock-like candidates against the filing record.

A recorded GUARANTEED_STRUCTURAL_NOT_EXECUTABLE or RULE_DEFINED_LOCK keeps its label only if, for
every leg, the terms were registry-verified at the snapshot with an OK filing check, AND no
regulatory filing for that template that was already posted at the snapshot (LastModified <= snapshot
+ grace) is missing from the filing set the record relied on. Anything else becomes
CANDIDATE_TERMS_UNVERIFIED with a reason. Nothing is ever promoted and no data file is modified.

Reasons:
  TERMS_NOT_VERIFIED_AT_SNAPSHOT        a leg's series was not registry-verified (e.g. the MECNET
                                        exemption removed on 2026-09-27, or a de-registered template)
  TERMS_FILINGS_NOT_CHECKED_AT_SNAPSHOT a record written before amendment-aware verification, with no
                                        superseding filing found either
  TERMS_SUPERSEDED_AT_SNAPSHOT          a regulatory filing for the template had been posted by the
                                        snapshot but was not in the set the verification relied on
"""
from __future__ import annotations

from . import filings as FL
from . import terms as TERMS

LOCK_LIKE = ("GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", "RULE_DEFINED_LOCK")
DEMOTED = "CANDIDATE_TERMS_UNVERIFIED"


def _series(event_ticker: str) -> str:
    return event_ticker.split("-")[0]


def retro_status(rec: dict, bucket: list[FL.Filing], series_terms: dict[str, str | None],
                 grace_s: float = 0.0) -> tuple[str, str | None]:
    """rec: a recorded candidate. bucket: a complete current listing of the regulatory bucket.
    series_terms: series ticker -> contract_terms_url (used when the record carries no provenance).
    Returns (status, reason); reason is None when the recorded status stands."""
    status = rec.get("status")
    if status not in LOCK_LIKE:
        return status, None
    snap_ns = int(rec["logged_utc_ns"]) + int(grace_s * 1e9)
    legs = ((rec.get("extra") or {}).get("provenance") or {}).get("legs") or {}
    if legs:
        leg_info = [(pl.get("terms_url"), pl.get("terms_status"), pl.get("terms_filing_status"),
                     pl.get("terms_known_filings")) for pl in legs.values()]
    else:                                           # legacy record: series -> terms URL, nothing checked
        leg_info = [(series_terms.get(_series(e)), None, None, None) for e in rec.get("event_tickers", [])]
    reasons = []
    for url, tstatus, fstatus, known in leg_info:
        t = TERMS.REGISTRY.get(url or "")
        if t is None or (legs and tstatus != "TERMS_VERIFIED"):
            reasons.append("TERMS_NOT_VERIFIED_AT_SNAPSHOT")
            continue
        relied_on = {k[0] for k in known} if (fstatus == FL.OK and known) else {f.key for f in t.known_filings}
        posted = [f for f in bucket if FL.belongs(t.template, f.key) and f.key.startswith("regulatory/")
                  and FL.iso_to_ns(f.last_modified) <= snap_ns and f.key not in relied_on]
        if posted:
            reasons.append("TERMS_SUPERSEDED_AT_SNAPSHOT")
        elif fstatus != FL.OK:
            reasons.append("TERMS_FILINGS_NOT_CHECKED_AT_SNAPSHOT")
    if not reasons:
        return status, None
    order = ("TERMS_SUPERSEDED_AT_SNAPSHOT", "TERMS_NOT_VERIFIED_AT_SNAPSHOT", "TERMS_FILINGS_NOT_CHECKED_AT_SNAPSHOT")
    return DEMOTED, next(r for r in order if r in reasons)
