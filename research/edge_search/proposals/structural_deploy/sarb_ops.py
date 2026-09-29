"""structural_arb long collection: operational health, validation checks and the ONE formal end-of-run evaluation.

PROPOSED (not frozen). It lives outside research/structural_arb, so the experiment's manifest is unchanged. It
imports the frozen `sarb` package read-only.

No-peek design:
  * `health` reads ONLY the `ops` and `universe` streams (enforced by `_read`, which refuses any other kind
    unless evaluation is open). They hold request counts, 429s, errors, timings, universe size and terms-filing
    status, and never a candidate status, edge or price.
  * `validate` runs on the validation directory only (deleted afterwards). It prints totals such as "N of N
    P2/P3 records reconstruct exactly", never statuses.
  * `evaluate` refuses to run before END_UTC + EVAL_DELAY_S. It computes the verdict from the pre-specified
    rules below, and only then attaches the descriptive secondary report.

usage:
  python sarb_ops.py health   DATA_DIR WINDOW_FILE
  python sarb_ops.py validate VALIDATION_DIR COMMIT CONFIG_VERSION
  python sarb_ops.py evaluate DATA_DIR WINDOW_FILE COMMIT CONFIG_VERSION LATE_FILING_REVIEW.json [--bucket-listing F]
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import os
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "structural_arb"))

NS = 1_000_000_000
H = 3600 * NS
DAY = 24 * H

# ---- proposed pre-specified constants (frozen with this package; see STRUCTURAL_FREEZE_PROPOSAL.md §4)
COLLECTION_DAYS = 28
GAP_NS = 300 * NS                      # a gap between consecutive ops records longer than this is downtime
MAX_DOWNTIME_NS = 72 * H               # V1
MAX_SINGLE_GAP_NS = 24 * H             # V1
MAX_429_RATIO_24H = 0.01               # V2 (any rolling 24 h window)
MAX_INTEGRITY_FAIL_RATIO = 0.01        # V4 (P2/P3 records missing leg snapshots, or P3 without P2)
MAX_CYCLE_ERROR_RATIO = 0.05           # V5
MIN_VERIFIED_EXPOSURE_NS = 21 * DAY    # FAILURE needs at least this much terms-verified collection time
EVAL_DELAY_NS = 24 * H                 # evaluation opens END_UTC + 24 h
HEALTH_DISK_ALERT_GB = 20
HEALTH_STALE_NS = 600 * NS

HEALTH_STREAMS = ("ops", "universe")


# ------------------------------------------------------------------------------------------------ helpers
def iso_ns(s: str) -> int:
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * NS)


def read_window(path: str) -> tuple[int, int]:
    kv = dict(line.strip().split("=", 1) for line in open(path) if "=" in line)
    start, end = iso_ns(kv["START_UTC"]), iso_ns(kv["END_UTC"])
    if end - start != COLLECTION_DAYS * DAY:
        raise SystemExit(f"WINDOW is not exactly {COLLECTION_DAYS} days")
    return start, end


def _read(data_dir: str, kind: str, allow_all: bool = False):
    if not allow_all and kind not in HEALTH_STREAMS:
        raise PermissionError(f"stream '{kind}' is closed until evaluation (no-peek rule)")
    for f in sorted(glob.glob(os.path.join(data_dir, f"sarb_{kind}_*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def _timed(recs, start: int | None = None, end: int | None = None) -> list[tuple[int, dict]]:
    out = sorted(((iso_ns(r["utc"]), r) for r in recs if r.get("utc")), key=lambda x: x[0])
    return [(t, r) for t, r in out if (start is None or t >= start) and (end is None or t <= end)]


# ------------------------------------------------------------------------------------------------ measures
def downtime(ops_t: list[int], start: int, end: int) -> tuple[int, int]:
    """(total downtime, longest gap) over [start, end]; gaps include start->first and last->end."""
    pts = [start] + sorted(ops_t) + [end]
    gaps = [b - a for a, b in zip(pts, pts[1:])]
    return sum(g for g in gaps if g > GAP_NS), max(gaps, default=0)


def max_429_ratio(ops: list[tuple[int, dict]]) -> float:
    """Worst ratio of 429s to requests over rolling 24 h windows ending at each ops record."""
    rows = [(t, r.get("http_429", 0) or 0, r.get("requests_total", 0) or 0) for t, r in ops if "requests_total" in r]
    worst, j, s429, sreq = 0.0, 0, 0, 0
    for i, (t, a, n) in enumerate(rows):
        s429, sreq = s429 + a, sreq + n
        while rows[j][0] <= t - DAY:
            s429, sreq, j = s429 - rows[j][1], sreq - rows[j][2], j + 1
        if sreq:
            worst = max(worst, s429 / sreq)
    return worst


def verified_exposure(uni: list[tuple[int, dict]], end: int) -> int:
    """Time during which the latest universe snapshot had >= 1 terms-verified market, counting only
    stretches without a downtime gap."""
    pts = uni + [(end, None)]
    return sum(b - a for (a, r), (b, _) in zip(pts, pts[1:])
               if r is not None and (r.get("terms_verified_markets") or 0) > 0 and b - a <= GAP_NS)


def validity(data_dir: str, start: int, end: int) -> dict:
    ops = _timed(_read(data_dir, "ops"), start, end)
    cycles = [t for t, r in ops if "requests_total" in r]
    errors = sum(1 for _, r in ops if "cycle_error" in r)
    down, gap = downtime([t for t, _ in ops], start, end)
    r429 = max_429_ratio(ops)
    err_ratio = errors / max(1, len(cycles) + errors)
    return {"downtime_h": down / H, "longest_gap_h": gap / H, "max_429_ratio_24h": r429,
            "cycles": len(cycles), "cycle_errors": errors, "cycle_error_ratio": err_ratio,
            "V1_downtime_ok": down <= MAX_DOWNTIME_NS and gap <= MAX_SINGLE_GAP_NS,
            "V2_rate_limit_ok": r429 <= MAX_429_RATIO_24H,
            "V5_cycle_errors_ok": err_ratio <= MAX_CYCLE_ERROR_RATIO}


# ------------------------------------------------------------------------------------------------ health
def health(data_dir: str, window: str, now_ns: int | None = None) -> dict:
    start, end = read_window(window)
    now = now_ns or time.time_ns()
    ops = _timed(_read(data_dir, "ops"), start, None)
    uni = _timed(_read(data_dir, "universe"), start, None)
    horizon = min(now, end)
    down, gap = downtime([t for t, _ in ops if t <= horizon], start, horizon)
    last24 = [(t, r) for t, r in ops if t > now - DAY]
    req = sum(r.get("requests_total", 0) or 0 for _, r in last24)
    n429 = sum(r.get("http_429", 0) or 0 for _, r in last24)
    errs = sum(1 for _, r in last24 if "cycle_error" in r)
    size = sum(os.path.getsize(f) for f in glob.glob(os.path.join(data_dir, "*")))
    free_gb = shutil.disk_usage(data_dir).free / 1e9
    last_u = uni[-1][1] if uni else {}
    out = {"day": (now - start) / DAY, "days_remaining": max(0.0, (end - now) / DAY),
           "last_ops_age_s": (now - ops[-1][0]) / NS if ops else None,
           "downtime_so_far_h": down / H, "longest_gap_h": gap / H,
           "requests_24h": req, "http_429_24h": n429, "ratio_429_24h": n429 / req if req else None,
           "cycles_24h": sum(1 for _, r in last24 if "requests_total" in r), "cycle_errors_24h": errs,
           "data_gb": size / 1e9, "disk_free_gb": free_gb,
           "terms_verified_markets_now": last_u.get("terms_verified_markets"),
           "terms_filing_status_now": last_u.get("terms_filing_status"),
           "verified_exposure_so_far_d": verified_exposure(uni, horizon) / DAY}
    alerts = []
    if now < end and (not ops or now - ops[-1][0] > HEALTH_STALE_NS):
        alerts.append("NO_RECENT_CYCLE")
    if req and n429 / req > MAX_429_RATIO_24H:
        alerts.append("429_RATIO_ABOVE_1PCT_24H")
    if errs:
        alerts.append("CYCLE_ERRORS_24H")
    if free_gb < HEALTH_DISK_ALERT_GB:
        alerts.append("DISK_FREE_BELOW_20GB")
    if down > MAX_DOWNTIME_NS or gap > MAX_SINGLE_GAP_NS:
        alerts.append("V1_ALREADY_FAILED")
    if not out["terms_verified_markets_now"]:
        alerts.append("NO_TERMS_VERIFIED_MARKETS_NOW")
    out["alerts"] = alerts
    return out


# ------------------------------------------------------------------------------------------------ validation
def validate(vdir: str, commit: str, config_version: str, reconstruct_fn=None) -> dict:
    """Operational checks of a VALIDATION directory. It prints totals only, never a status distribution."""
    from sarb import reconstruct as RC
    reconstruct_fn = reconstruct_fn or RC.reconstruct
    out: dict = {"dir": vdir, "gzip": {}}
    for f in sorted(glob.glob(os.path.join(vdir, "*.jsonl.gz"))):
        n = 0
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                json.loads(line)
                n += 1
        out["gzip"][os.path.basename(f)] = n
    ops = _timed(_read(vdir, "ops"))
    cyc = [r for _, r in ops if "requests_total" in r]
    out["ops"] = {"cycles": len(cyc), "cycle_errors": sum(1 for _, r in ops if "cycle_error" in r),
                  "requests": sum(r["requests_total"] for r in cyc), "http_429": sum(r.get("http_429", 0) for r in cyc),
                  "req_per_s_mean": sum(r["req_per_s"] for r in cyc) / len(cyc) if cyc else None,
                  "req_per_s_max": max((r["req_per_s"] for r in cyc), default=None),
                  "cycle_s_mean": sum(r["cycle_s"] for r in cyc) / len(cyc) if cyc else None}
    cands = list(_read(vdir, "candidates", allow_all=True))
    codes = Counter((((r.get("extra") or {}).get("provenance") or {}).get("code") or {}).get("git_sha") for r in cands
                    if (r.get("extra") or {}).get("provenance"))
    dirty = Counter((((r.get("extra") or {}).get("provenance") or {}).get("code") or {}).get("dirty") for r in cands
                    if (r.get("extra") or {}).get("provenance"))
    out["code_identity"] = {"git_sha": dict(codes), "dirty": {str(k): v for k, v in dirty.items()},
                            "config_versions": dict(Counter(r.get("config_version") for r in cands)),
                            "ok": set(codes) <= {commit} and set(dirty) <= {False}
                            and {r.get("config_version") for r in cands} <= {config_version}}
    idx = defaultdict(list)
    for b in _read(vdir, "books", allow_all=True):
        idx[b.get("group")].append(b)
    p23 = [r for r in cands if (r.get("extra") or {}).get("phase") in ("P2", "P3") and "provenance" in r["extra"]]
    ok = sum(1 for r in p23 if reconstruct_fn(vdir, r, idx)["match"])
    out["reconstruct_all_p2_p3"] = {"records": len(p23), "exact": ok}
    out["integrity_fail_ratio"] = integrity(cands, idx)
    uni = _timed(_read(vdir, "universe"))
    out["terms"] = {"terms_verified_markets_last": uni[-1][1].get("terms_verified_markets") if uni else None,
                    "terms_filing_status_last": uni[-1][1].get("terms_filing_status") if uni else None}
    busy = sum(r["cycle_s"] for r in cyc)             # collection time actually covered by the cycles
    size = sum(os.path.getsize(f) for f in glob.glob(os.path.join(vdir, "*")))
    out["footprint"] = {"bytes": size, "collection_s": busy,
                        "projected_gb_28d": size / busy * COLLECTION_DAYS * 86400 / 1e9 if busy else None}
    return out


def integrity(cands: list[dict], idx: dict) -> float:
    """Share of P2/P3 records whose legs lack market/orderbook snapshots in their group, or P3 without a P2."""
    have = defaultdict(set)
    for g, bs in idx.items():
        for b in bs:
            have[(g, b.get("phase"))].add((b.get("kind"), b.get("ticker")))
    p2_groups = {r["extra"]["group"] for r in cands if r["extra"].get("phase") == "P2"}
    rows = [r for r in cands if r["extra"].get("phase") in ("P2", "P3")]
    bad = 0
    for r in rows:
        need = {(k, leg["ticker"]) for leg in r.get("legs", []) for k in ("market", "orderbook")}
        missing = not need <= have[(r["extra"]["group"], r["extra"]["phase"])]
        orphan = r["extra"]["phase"] == "P3" and r["extra"]["group"] not in p2_groups
        bad += missing or orphan
    return bad / len(rows) if rows else 0.0


# ------------------------------------------------------------------------------------------------ evaluation
def qualifying(rec: dict, commit: str, config_version: str, start: int, end: int, reconstruct_fn, idx,
               retro_fn, late_demoted: set[str]) -> tuple[bool, str]:
    """A qualifying lock (QL). Every condition is necessary; the first failing one is returned."""
    ex = rec.get("extra") or {}
    prov = ex.get("provenance") or {}
    code = prov.get("code") or {}
    if rec.get("status") != "RULE_DEFINED_LOCK" or ex.get("phase") != "P3":
        return False, "not_p3_lock"
    if not start <= int(rec["logged_utc_ns"]) <= end:
        return False, "outside_window"
    if code.get("git_sha") != commit or code.get("dirty") is not False or rec.get("config_version") != config_version:
        return False, "code_identity"
    legs = prov.get("legs") or {}
    if not legs or any(leg.get("terms_status") != "TERMS_VERIFIED" or leg.get("terms_filing_status") != "OK"
                       for leg in legs.values()):
        return False, "terms_not_verified_at_snapshot"
    if not reconstruct_fn(None, rec, idx)["match"]:
        return False, "reconstruction_mismatch"
    if retro_fn(rec)[1] is not None:
        return False, "terms_retro_demoted"
    if rec.get("candidate_id") in late_demoted:
        return False, "late_filing_review_demoted"
    return True, "QL"


def verdict(code_ok: bool, n_ql: int, valid: dict, integrity_ok: bool, exposure_ns: int) -> str:
    if not code_ok:
        return "INVALID"
    if n_ql >= 1:
        return "SUCCESS"
    if (valid["V1_downtime_ok"] and valid["V2_rate_limit_ok"] and valid["V5_cycle_errors_ok"] and integrity_ok
            and exposure_ns >= MIN_VERIFIED_EXPOSURE_NS):
        return "FAILURE"
    return "INSUFFICIENT_EVIDENCE"


def evaluate(data_dir: str, window: str, commit: str, config_version: str, late_review: str,
             bucket_listing: str | None = None, now_ns: int | None = None, reconstruct_fn=None, retro_fn=None,
             secondary: bool = True) -> dict:
    start, end = read_window(window)
    now = now_ns or time.time_ns()
    if now < end + EVAL_DELAY_NS:
        raise PermissionError("evaluation is closed until END_UTC + 24 h (no-peek rule)")
    review = json.load(open(late_review))            # required: the human late-filing review (may list nothing)
    late_demoted = {d["candidate_id"] for d in review.get("demoted", [])}
    from sarb import filings as FL
    from sarb import reconstruct as RC
    from sarb import terms_retro as TR
    if retro_fn is None:
        bucket = ([FL.Filing(*x) for x in json.load(open(bucket_listing))] if bucket_listing
                  else [f for pre in FL.PREFIXES for f in FL.http_list(pre)])
        retro_fn = lambda rec: TR.retro_status(rec, bucket, {})          # noqa: E731
    base = reconstruct_fn or RC.reconstruct
    cands = list(_read(data_dir, "candidates", allow_all=True))
    idx = defaultdict(list)
    for b in _read(data_dir, "books", allow_all=True):
        idx[b.get("group")].append(b)
    in_w = [r for r in cands if start <= int(r["logged_utc_ns"]) <= end]
    code_bad = sum(1 for r in in_w if r.get("config_version") != config_version
                   or ((r.get("extra") or {}).get("provenance") and
                       (r["extra"]["provenance"].get("code", {}).get("git_sha") != commit
                        or r["extra"]["provenance"].get("code", {}).get("dirty") is not False)))
    reasons = Counter()
    qls = []
    for r in in_w:
        if r.get("status") != "RULE_DEFINED_LOCK":
            continue
        ok, why = qualifying(r, commit, config_version, start, end, lambda _d, rec, i: base(data_dir, rec, i), idx,
                             retro_fn, late_demoted)
        reasons[why] += 1
        if ok:
            qls.append(r)
    valid = validity(data_dir, start, end)
    integ = integrity(in_w, idx)
    uni = _timed(_read(data_dir, "universe"), start, end)
    exposure = verified_exposure(uni, end)
    v = verdict(code_bad == 0, len(qls), valid, integ <= MAX_INTEGRITY_FAIL_RATIO, exposure)
    out = {"verdict": v, "qualifying_locks": len(qls),
           "distinct_lock_keys": len({(r.get("relationship"), tuple(sorted(map(tuple, r["extra"]["provenance"]["positions"]))))
                                      for r in qls}),
           "rule_defined_lock_records_by_reason": dict(reasons), "code_identity_violations": code_bad,
           "records_after_end_excluded": sum(1 for r in cands if int(r["logged_utc_ns"]) > end),
           "validity": valid, "integrity_fail_ratio": integ, "verified_exposure_d": exposure / DAY,
           "late_filing_review": review}
    if secondary:                                    # descriptive only; computed after the verdict, never changes it
        from sarb import report as REP
        out["secondary_report"] = REP.summarize(data_dir)
        out["qualifying_lock_detail"] = [{"candidate_id": r.get("candidate_id"), "utc_ns": r["logged_utc_ns"],
                                          "relationship": r.get("relationship"),
                                          "max_executable_size": r.get("max_executable_size"),
                                          "edges_by_size": r["extra"].get("edges_by_size")} for r in qls]
    return out


def main(argv: list[str]) -> None:
    cmd, args = argv[0], argv[1:]
    if cmd == "health":
        res = health(args[0], args[1])
    elif cmd == "validate":
        res = validate(args[0], args[1], args[2])
    elif cmd == "evaluate":
        bl = args[args.index("--bucket-listing") + 1] if "--bucket-listing" in args else None
        res = evaluate(args[0], args[1], args[2], args[3], args[4], bl)
    else:
        raise SystemExit(__doc__)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":                            # pragma: no cover
    main(sys.argv[1:])
