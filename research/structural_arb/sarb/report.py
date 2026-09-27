"""Summarize a data directory (schema v2). Negative results are reported with the same weight as
positive ones. Includes an integrity audit of snapshot recording.

    python -m sarb.report data/            # human-readable
    python -m sarb.report data/ --json     # machine-readable
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from collections import Counter, defaultdict
from decimal import Decimal

LOCK_LIKE = {"RULE_DEFINED_LOCK", "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", "CANDIDATE_TERMS_UNVERIFIED"}


def _read(data_dir: str, kind: str):
    for f in sorted(glob.glob(os.path.join(data_dir, f"sarb_{kind}_*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def _pct(v, q):
    if not v:
        return None
    v = sorted(v)
    return round(v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))], 1)


def summarize(data_dir: str) -> dict:
    out: dict = {}
    cands = list(_read(data_dir, "candidates"))
    by = Counter((r["extra"].get("phase"), r["relationship"], r["status"]) for r in cands)
    out["candidates_by_phase_relationship_status"] = {"|".join(k): v for k, v in sorted(by.items())}
    gate_fail = Counter()
    edge_sign = Counter()
    unwind, max_sizes = [], []
    for r in cands:
        if r["status"] not in LOCK_LIKE:
            continue
        for k, ok in (r["extra"].get("gates") or {}).items():
            if not ok:
                gate_fail[(r["extra"].get("phase"), k.split(":")[0])] += 1
        e = (r["extra"].get("edges_by_size") or {}).get("1")
        if isinstance(e, dict):
            d, n = Decimal(e["direct_expected"]) > 0, Decimal(e["nondirect_conservative"]) > 0
            edge_sign[f"direct_expected>0={d}|nondirect_conservative>0={n}"] += 1
        u = (r["extra"].get("unwind") or {}).get("1")
        if u and u.get("complete"):
            unwind.append(float(u["worst_partial_fill_unwind_loss"]))
        if r.get("max_executable_size"):
            max_sizes.append(int(r["max_executable_size"]))
    out["lock_like_gate_failures"] = {f"{p}|{g}": n for (p, g), n in gate_fail.most_common()}
    out["lock_like_size1_edge_sign_direct_vs_broker"] = dict(edge_sign)
    out["lock_like_worst_partial_unwind_loss_size1"] = {"n": len(unwind), "p50": _pct(unwind, .5), "p95": _pct(unwind, .95)}
    out["lock_like_max_executable_size"] = {"n": len(max_sizes), "p50": _pct(max_sizes, .5), "max": max(max_sizes) if max_sizes else None}
    out["rule_defined_locks"] = [{"relationship": r["relationship"], "phase": r["extra"].get("phase"),
                                  "legs": [(l["ticker"], l["side"], l["best_ask"]) for l in r["legs"]],
                                  "max_size": r["max_executable_size"], "edges": (r["extra"].get("edges_by_size") or {}).get("1"),
                                  "residual_risks": len(r["extra"].get("residual_risks", []))}
                                 for r in cands if r["status"] == "RULE_DEFINED_LOCK"]
    r511 = list(_read(data_dir, "rule511"))
    out["rule_5_11"] = {"records": len(r511),
                        "only_5_11_and_or_persistence_failed": sum(1 for r in r511 if r["extra"]["rule_5_11"]["only_rule_5_11_and_or_persistence_failed"]),
                        "by_phase": dict(Counter(r["extra"].get("phase") for r in r511))}
    stat = list(_read(data_dir, "statscreen"))
    out["statistical_screen_hits_summary_prices_only"] = dict(Counter(r["relationship"] for r in stat))
    counts = Counter()
    for c in _read(data_dir, "counts"):
        counts.update(c["counts"])
    out["aggregate_counts"] = dict(sorted(counts.items()))
    # ---- ops
    ops = [o for o in _read(data_dir, "ops") if "cycle" in o]
    errs = [o for o in _read(data_dir, "ops") if "cycle_error" in o]
    lat = defaultdict(list)
    for o in ops:
        for k, v in (o.get("latency_ms") or {}).items():
            lat[k].append(v["p50"])
    out["ops"] = {
        "cycles": len(ops), "cycle_errors": len(errs),
        "cycle_s": {"p50": _pct([o["cycle_s"] for o in ops], .5), "max": max((o["cycle_s"] for o in ops), default=None)},
        "requests_total": sum(o["requests_total"] for o in ops),
        "req_per_s_by_cycle": {"p50": _pct([o["req_per_s"] for o in ops], .5), "max": max((o["req_per_s"] for o in ops), default=None)},
        "http_429": sum(o["http_429"] for o in ops),
        "http_non200": dict(sum((Counter(o["http_non200"]) for o in ops), Counter())),
        "endpoint_latency_p50_ms_median_over_cycles": {k: _pct(v, .5) for k, v in lat.items()},
        "p2_leg_fetch_ms": {"n": sum(len(o["p2_leg_fetch_ms"]) for o in ops),
                            "p50": _pct([x for o in ops for x in o["p2_leg_fetch_ms"]], .5),
                            "p95": _pct([x for o in ops for x in o["p2_leg_fetch_ms"]], .95)},
        "p2_book_skew_ms": {"p50": _pct([x for o in ops for x in o["p2_book_skew_ms"]], .5),
                            "p95": _pct([x for o in ops for x in o["p2_book_skew_ms"]], .95)},
        "p3_delay_ms": {"n": sum(len(o["p3_delay_ms"]) for o in ops),
                        "p50": _pct([x for o in ops for x in o["p3_delay_ms"]], .5),
                        "p95": _pct([x for o in ops for x in o["p3_delay_ms"]], .95)},
        "phase_seconds_p50": {k: _pct([o[k] for o in ops], .5) for k in ("events_s", "screen_s", "phase23_s", "audit_s")},
    }
    # ---- integrity: every P2/P3 record's legs have market+orderbook snapshots in its group
    books = defaultdict(set)
    for b in _read(data_dir, "books"):
        books[(b["group"], b["phase"])].add((b["kind"], b["ticker"]))
    missing, p3_without_p2 = 0, 0
    p2_groups = {r["extra"]["group"] for r in cands if r["extra"].get("phase") == "P2"}
    for r in cands:
        ph = r["extra"].get("phase")
        if ph in ("P2", "P3"):
            need = {(k, l["ticker"]) for l in r["legs"] for k in ("market", "orderbook")}
            if not need <= books[(r["extra"]["group"], ph)]:
                missing += 1
        if ph == "P3" and r["extra"]["group"] not in p2_groups:
            p3_without_p2 += 1
    uni = list(_read(data_dir, "universe"))
    out["integrity"] = {"records_missing_leg_snapshots": missing, "p3_without_p2": p3_without_p2,
                        "universe_snapshots": len(uni), "cycles_in_counts": sum(1 for _ in _read(data_dir, "counts")),
                        "terms_verified_markets_last": uni[-1]["terms_verified_markets"] if uni else None,
                        "fee_ledger_changes_last": uni[-1].get("fee_ledger_changes") if uni else None}
    out["fee_unresolved_reasons"] = dict(Counter(v.split(":")[1] if ":" in v else v
                                                 for r in cands for v in (r["extra"].get("fee_unresolved") or {}).values()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = summarize(a.data_dir)
    if a.json:
        print(json.dumps(s, indent=1, default=str))
        return
    for k, v in s.items():
        print(f"== {k}")
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(f"   {kk}: {vv}")
        else:
            for x in v:
                print(f"   {x}")


if __name__ == "__main__":
    main()
