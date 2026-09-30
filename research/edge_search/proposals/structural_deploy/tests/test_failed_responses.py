"""Deterministic fixtures for the 2026-09-30 scratch-cycle failure modes (STRUCTURAL_SCRATCH_CYCLE_2026-09-30.md).

The scratch data was deleted, so the failures are reproduced end-to-end: the REAL frozen `sarb.collector`
(behind the real PublicClient) runs one cycle against the frozen test suite's fake HTTP session. A single
HTTP 429 is injected on the first P2 fetch of one source response, for exactly the endpoint families
rate-limited that day (/markets/{t}, /markets/{t}/orderbook, /series/{s}), plus /events/{e}. Then:
  * the frozen `sarb.reconstruct` is shown to fail in the same way as that day (mismatch or KeyError crash);
  * the proposed validation check handles each record without crashing, verifies it failed closed, and still
    requires exact reconstruction of every record whose inputs all succeeded.
No network. Nothing in research/structural_arb is modified (its test module is only imported).
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SARB = HERE.parents[3] / "structural_arb"
sys.path.insert(0, str(SARB))
sys.path.insert(0, str(HERE.parent))
import sarb_ops as O                                           # noqa: E402
from sarb import config, reconstruct as RC, terms as TERMS     # noqa: E402
from sarb.client import PublicClient                          # noqa: E402
from sarb.collector import Collector                           # noqa: E402

_spec = importlib.util.spec_from_file_location("frozen_test_collector", SARB / "tests" / "test_collector.py")
TC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TC)                                   # read-only reuse of the frozen harness


@pytest.fixture
def registry(monkeypatch):
    t = TERMS.VerifiedTerms(TC.FAKE_TERMS, hashlib.sha256(TC.FAKE_BYTES).hexdigest(), True, "LAST_VALUE", ("test",),
                            "test fixture: single fixed determination instant", template="FAKE",
                            controlling_filing=TC.FAKE_FILING,
                            controlling_filing_sha256=hashlib.sha256(TC.FAKE_FILING_BYTES).hexdigest(),
                            known_filings=TC.FAKE_KNOWN, reviewed="test fixture")
    monkeypatch.setattr(TERMS, "REGISTRY", {TC.FAKE_TERMS: t})
    monkeypatch.setattr(TC, "BUCKET", list(TC.FAKE_KNOWN))
    monkeypatch.setattr(config, "PERSISTENCE_REFETCH_DELAY_S", 0.05)
    monkeypatch.setattr(config, "AUDIT_FAMILIES_PER_CYCLE", 1)
    monkeypatch.setattr(config, "EVENTS_PAGE_MIN_INTERVAL_S", 0)


class RateLimited(TC.Session):
    """The frozen fake session, except that the first request to `path` answers HTTP 429 with Kalshi's body."""

    def __init__(self, path: str | None):
        super().__init__()
        self.fail_path, self.failed = path, False

    def request(self, method, url, params=None, headers=None, timeout=None):
        path = TC.urllib.parse.urlparse(url).path.replace("/trade-api/v2", "")
        if path == self.fail_path and not self.failed:
            self.failed = True
            self.paths.append(path)
            return TC.Resp({"error": {"code": "too_many_requests", "message": "too many requests"}}, 429)
        return super().request(method, url, params=params, headers=headers, timeout=timeout)


def cycle(tmp_path, fail_path):
    s = RateLimited(fail_path)
    c = Collector(PublicClient(session=s, per_second=1000, burst=100), str(tmp_path), seed=1,
                  terms_fetch=lambda url: TC.FAKE_BYTES, filings_list=TC.fake_list, filings_fetch=TC.fake_fetch)
    c.run_cycle()
    assert fail_path is None or s.failed, "the 429 was not injected"
    cands = TC.read(tmp_path, "candidates")
    return [r for r in cands if r["extra"]["phase"] in ("P2", "P3")]


def index(tmp_path):
    idx = {}
    for b in TC.read(tmp_path, "books"):
        idx.setdefault(b.get("group"), []).append(b)
    return idx


def validate(tmp_path, recs):
    return O.reconstruction_check(str(tmp_path), recs, index(tmp_path), RC.reconstruct)


# frozen reconstruct's behaviour per failure mode, as observed on 2026-09-30 (or, for /events, as it behaves)
MODES = [
    ("/series/KXFAKE", "series", "crash"),               # 2026-09-30: KeyError('ticker'), live FEE_UNRESOLVED/REJECTED
    ("/markets/A", "market", "mismatch"),                # 2026-09-30: MISSING_SNAPSHOT mismatch, live REJECTED
    ("/markets/A/orderbook", "orderbook", "exact"),      # 2026-09-30: replayed exactly, live REJECTED
    ("/events/KXFAKE-99", "event", "mismatch"),
]


def test_baseline_without_failures_passes_and_everything_reconstructs(tmp_path, registry):
    recs = cycle(tmp_path, None)
    assert {r["status"] for r in recs} >= {"RULE_DEFINED_LOCK"}
    v = validate(tmp_path, recs)
    assert v["pass"] and v["all_inputs_ok"] == {"records": len(recs), "exact": len(recs)} and v["failed_input"] == {}


@pytest.mark.parametrize("path,kind,frozen_replay", MODES)
def test_failed_response_mode(tmp_path, registry, path, kind, frozen_replay):
    recs = cycle(tmp_path, path)
    p2 = [r for r in recs if r["extra"]["phase"] == "P2"]
    assert len(p2) == 1
    rec = p2[0]
    # 1. the live frozen collector failed closed and never produced a lock-like label
    assert rec["status"] in O.FAIL_CLOSED
    assert not any(r["status"] in ("RULE_DEFINED_LOCK", "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE") for r in recs)
    # 2. the frozen reconstruct fails on it exactly as on 2026-09-30 (the reason the old check broke)
    idx = index(tmp_path)
    if frozen_replay == "crash":
        with pytest.raises(KeyError):
            RC.reconstruct(str(tmp_path), rec, idx)
    else:
        assert RC.reconstruct(str(tmp_path), rec, idx)["match"] is (frozen_replay == "exact")
    # 3. the validation check identifies the failed input, verifies fail-closed, never crashes, and passes
    failed, missing = O.required_inputs(rec, idx)
    assert missing == [] and len(failed) == 1 and failed[0].startswith(f"{kind}:") and failed[0].endswith("HTTP_429")
    v = validate(tmp_path, recs)
    assert v["pass"], v
    assert v["failed_input"]["records"] == 1 and v["failed_input"]["fail_closed"] == 1
    assert v["failed_input"][f"reconstruct_{'error' if frozen_replay == 'crash' else frozen_replay}"] == 1
    assert v["failed_input_kinds"] == {kind: 1}


def test_all_three_2026_09_30_modes_in_one_directory(tmp_path, registry):
    """One validation directory holding one record per mode, like the scratch cycle (35 ok + 3 non-exact)."""
    recs = []
    for i, (path, _, _) in enumerate(MODES[:3]):
        d = tmp_path / f"part{i}"
        d.mkdir()
        recs += [(d, r) for r in cycle(d, path)]
    merged = tmp_path / "merged"
    merged.mkdir()
    for kind in ("candidates", "books"):
        with gzip.open(merged / f"sarb_{kind}_20260930.jsonl.gz", "wt") as fh:
            for i in range(3):
                for row in TC.read(tmp_path / f"part{i}", kind):
                    fh.write(json.dumps(row) + "\n")
    # the fixture's fee ledger is identical in every part
    (merged / "sarb_fee_ledger.jsonl").write_bytes((tmp_path / "part0" / "sarb_fee_ledger.jsonl").read_bytes())
    rows = [r for r in TC.read(merged, "candidates") if r["extra"]["phase"] in ("P2", "P3")]
    v = validate(merged, rows)
    assert v["pass"], v
    assert v["failed_input"] == {"records": 3, "fail_closed": 3, "reconstruct_error": 1, "reconstruct_mismatch": 1,
                                 "reconstruct_exact": 1}


# ------------------------------------------------------------------ the criterion is not weakened
def _rewrite(tmp_path, kind, fn):
    f = next(tmp_path.glob(f"sarb_{kind}_*"))
    rows = [json.loads(x) for x in gzip.open(f, "rt")]
    rows = [y for y in (fn(x) for x in rows) if y is not None]
    with gzip.open(f, "wt") as fh:
        fh.write("".join(json.dumps(x) + "\n" for x in rows))


def test_failed_input_with_a_non_fail_closed_status_fails_validation(tmp_path, registry):
    cycle(tmp_path, "/series/KXFAKE")
    _rewrite(tmp_path, "candidates", lambda r: {**r, "status": "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"}
             if r["extra"]["phase"] == "P2" else r)
    recs = [r for r in TC.read(tmp_path, "candidates") if r["extra"]["phase"] in ("P2", "P3")]
    v = validate(tmp_path, recs)
    assert not v["pass"] and v["failures"][0]["why"] == "failed_input_not_fail_closed"


def test_all_ok_record_that_does_not_replay_exactly_fails_validation(tmp_path, registry):
    cycle(tmp_path, None)

    def tamper(b):
        if b["kind"] == "orderbook" and b["phase"] == "P3" and b["ticker"] == "B":
            b["body"] = {"orderbook_fp": {"yes_dollars": [["0.40", "50"]], "no_dollars": [["0.40", "50"]]}}
        return b
    _rewrite(tmp_path, "books", tamper)
    recs = [r for r in TC.read(tmp_path, "candidates") if r["extra"]["phase"] in ("P2", "P3")]
    v = validate(tmp_path, recs)
    assert not v["pass"] and any(f["why"] == "all_inputs_ok_but_mismatch" for f in v["failures"])


def test_unrecorded_source_response_fails_validation(tmp_path, registry):
    cycle(tmp_path, None)
    _rewrite(tmp_path, "books", lambda b: None if (b["kind"] == "orderbook" and b["phase"] == "P2"
                                                   and b["ticker"] == "A") else b)
    recs = [r for r in TC.read(tmp_path, "candidates") if r["extra"]["phase"] == "P2"]
    v = validate(tmp_path, recs)
    assert not v["pass"] and v["failures"][0] == {"candidate_id": recs[0]["candidate_id"], "why": "unrecorded_input",
                                                  "inputs": ["orderbook:A"]}


def test_crash_in_an_all_ok_record_fails_validation_without_aborting(tmp_path, registry):
    recs = cycle(tmp_path, None)

    def boom(root, rec, idx):
        raise KeyError("ticker")
    v = O.reconstruction_check(str(tmp_path), recs, index(tmp_path), boom)
    assert not v["pass"] and v["all_inputs_ok"]["error"] == len(recs)
