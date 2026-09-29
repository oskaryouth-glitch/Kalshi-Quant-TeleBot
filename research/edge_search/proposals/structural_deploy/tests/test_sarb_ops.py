"""Synthetic-data tests of the proposed structural_arb ops/evaluation rules (no network, no real data)."""
from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sarb_ops as O  # noqa: E402

START = O.iso_ns("2026-11-01T00:00:00Z")
END = START + O.COLLECTION_DAYS * O.DAY
COMMIT, CFG = "c" * 40, "cfg-1"


def iso(ns: int) -> str:
    return O.dt.datetime.fromtimestamp(ns / O.NS, O.dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(d: Path, kind: str, rows: list[dict]) -> None:
    with gzip.open(d / f"sarb_{kind}_20261101.jsonl.gz", "at", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def lock(t: int, cid: str = "L1", sha: str = COMMIT, cfg: str = CFG, phase: str = "P3", filing: str = "OK") -> dict:
    return {"candidate_id": cid, "logged_utc_ns": t, "status": "RULE_DEFINED_LOCK", "config_version": cfg,
            "relationship": "R2", "legs": [{"ticker": "A"}, {"ticker": "B"}], "max_executable_size": "10",
            "extra": {"phase": phase, "group": "g1", "edges_by_size": {"1": "0.01"},
                      "provenance": {"code": {"git_sha": sha, "dirty": False, "config_version": cfg},
                                     "positions": [["A", "no", "1"], ["B", "yes", "1"]],
                                     "legs": {"A": {"terms_status": "TERMS_VERIFIED", "terms_filing_status": filing},
                                              "B": {"terms_status": "TERMS_VERIFIED", "terms_filing_status": filing}}}}}


@pytest.fixture
def run(tmp_path):
    def make(step_s=150, gap=None, verified=True, n429=0, cands=(), errors=0):
        d = tmp_path / "data"
        d.mkdir(exist_ok=True)
        ts = list(range(START + 60 * O.NS, END, step_s * O.NS))
        if gap:
            ts = [t for t in ts if not gap[0] <= t < gap[1]]
        write(d, "ops", [{"utc": iso(t), "requests_total": 300, "http_429": n429, "req_per_s": 2.0, "cycle_s": 150}
                         for t in ts] + [{"utc": iso(ts[i]), "cycle_error": "x"} for i in range(errors)])
        write(d, "universe", [{"utc": iso(t), "terms_verified_markets": 5 if verified else 0,
                               "terms_filing_status": {"u": "OK" if verified else "TERMS_FILING_CHANGED"}} for t in ts])
        write(d, "candidates", list(cands))
        write(d, "books", [{"group": "g1", "phase": p, "kind": k, "ticker": t}
                           for p in ("P2", "P3") for k in ("market", "orderbook") for t in ("A", "B")])
        if cands:
            write(d, "candidates", [{**cands[0], "status": "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", "candidate_id": "p2",
                                     "extra": {**cands[0]["extra"], "phase": "P2"}}])
        w = tmp_path / "WINDOW"
        w.write_text(f"START_UTC={iso(START)}\nEND_UTC={iso(END)}\n")
        rv = tmp_path / "late.json"
        rv.write_text(json.dumps({"reviewed_by": "t", "demoted": []}))
        return d, w, rv
    return make


def ev(d, w, rv, match=True, retro=None, **kw):
    return O.evaluate(str(d), str(w), COMMIT, CFG, str(rv), now_ns=END + O.EVAL_DELAY_NS,
                      reconstruct_fn=lambda _d, rec, i: {"match": match},
                      retro_fn=lambda rec: (rec["status"], retro), secondary=False, **kw)


def test_health_cannot_open_result_streams(run):
    d, w, _ = run()
    with pytest.raises(PermissionError):
        list(O._read(str(d), "candidates"))
    for k in ("counts", "rule511", "statscreen", "books"):
        with pytest.raises(PermissionError):
            list(O._read(str(d), k))


def test_health_reports_ops_only(run):
    d, w, _ = run()
    h = O.health(str(d), str(w), now_ns=START + 3 * O.DAY)
    assert h["alerts"] == [] and h["downtime_so_far_h"] < 0.1 and h["ratio_429_24h"] == 0
    assert 2.9 < h["verified_exposure_so_far_d"] <= 3.0
    assert not {"status", "edge", "RULE_DEFINED_LOCK"} & set(json.dumps(h).split('"'))


def test_evaluation_closed_before_end_plus_24h(run):
    d, w, rv = run()
    with pytest.raises(PermissionError):
        O.evaluate(str(d), str(w), COMMIT, CFG, str(rv), now_ns=END + O.EVAL_DELAY_NS - 1)


def test_window_must_be_exactly_28_days(tmp_path):
    p = tmp_path / "W"
    p.write_text(f"START_UTC={iso(START)}\nEND_UTC={iso(END + O.NS)}\n")
    with pytest.raises(SystemExit):
        O.read_window(str(p))


def test_success_on_one_qualifying_lock(run):
    d, w, rv = run(cands=[lock(START + O.DAY)])
    r = ev(d, w, rv)
    assert r["verdict"] == "SUCCESS" and r["qualifying_locks"] == 1


def test_success_does_not_need_coverage(run):
    d, w, rv = run(cands=[lock(START + O.DAY)], gap=(START + 2 * O.DAY, START + 5 * O.DAY))
    assert ev(d, w, rv)["verdict"] == "SUCCESS"


def test_failure_needs_valid_run_and_exposure(run):
    d, w, rv = run()
    r = ev(d, w, rv)
    assert r["verdict"] == "FAILURE" and r["verified_exposure_d"] > 27.9


def test_unverified_terms_give_insufficient_evidence(run):
    d, w, rv = run(verified=False)
    assert ev(d, w, rv)["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_long_gap_gives_insufficient_evidence(run):
    d, w, rv = run(gap=(START + 2 * O.DAY, START + 3 * O.DAY + O.H))
    r = ev(d, w, rv)
    assert r["verdict"] == "INSUFFICIENT_EVIDENCE" and not r["validity"]["V1_downtime_ok"]


def test_rate_limit_breach_gives_insufficient_evidence(run):
    d, w, rv = run(n429=4)                     # 4/300 = 1.3% > 1%
    r = ev(d, w, rv)
    assert r["verdict"] == "INSUFFICIENT_EVIDENCE" and not r["validity"]["V2_rate_limit_ok"]


def test_cycle_errors_give_insufficient_evidence(run):
    d, w, rv = run(errors=1000)
    assert ev(d, w, rv)["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_code_identity_violation_is_invalid(run):
    d, w, rv = run(cands=[lock(START + O.DAY, sha="d" * 40)])
    r = ev(d, w, rv)
    assert r["verdict"] == "INVALID" and r["qualifying_locks"] == 0


@pytest.mark.parametrize("kw,why", [({"match": False}, "reconstruction_mismatch"),
                                    ({"retro": "TERMS_SUPERSEDED_AT_SNAPSHOT"}, "terms_retro_demoted")])
def test_demotions_leave_no_qualifying_lock(run, kw, why):
    d, w, rv = run(cands=[lock(START + O.DAY)])
    r = ev(d, w, rv, **kw)
    assert r["qualifying_locks"] == 0 and r["rule_defined_lock_records_by_reason"] == {why: 1}
    assert r["verdict"] == "FAILURE"


def test_terms_not_ok_at_snapshot_does_not_qualify(run):
    d, w, rv = run(cands=[lock(START + O.DAY, filing="TERMS_FILING_CHANGED")])
    assert ev(d, w, rv)["rule_defined_lock_records_by_reason"] == {"terms_not_verified_at_snapshot": 1}


def test_late_filing_review_demotes(run):
    d, w, rv = run(cands=[lock(START + O.DAY)])
    rv.write_text(json.dumps({"reviewed_by": "t", "demoted": [{"candidate_id": "L1", "filing": "x"}]}))
    assert ev(d, w, rv)["rule_defined_lock_records_by_reason"] == {"late_filing_review_demoted": 1}


def test_records_outside_window_do_not_count(run):
    d, w, rv = run(cands=[lock(END + 60 * O.NS)])
    r = ev(d, w, rv)
    assert r["qualifying_locks"] == 0 and r["records_after_end_excluded"] >= 1


def test_rolling_429_window():
    ops = [(i * O.H, {"requests_total": 100, "http_429": 3 if i == 30 else 0}) for i in range(60)]
    assert abs(O.max_429_ratio(ops) - 3 / 2400) < 1e-12


def test_integrity_counts_missing_snapshots_and_orphans():
    idx = {"g": [{"phase": "P2", "kind": "market", "ticker": "A"}]}
    c = [{"legs": [{"ticker": "A"}], "extra": {"phase": "P2", "group": "g"}},
         {"legs": [{"ticker": "A"}], "extra": {"phase": "P3", "group": "h"}}]
    assert O.integrity(c, idx) == 1.0
