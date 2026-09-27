"""Collector integration test: fake HTTP session behind the REAL PublicClient."""
import gzip
import hashlib
import json
import os
import time
import urllib.parse

import pytest

from sarb import config, terms as TERMS
from sarb.client import PublicClient
from sarb.collector import Collector

FAKE_TERMS = "https://assets.kalshi.com/contract_terms/FAKE.pdf"
FAKE_BYTES = b"fake terms for tests"
FUTURE = "2099-01-01T00:00:00Z"
TXT = "If the Fake Index on Jan 1, 2099 is above {k}, then the market resolves to Yes."


def market(t, k, yes_ask, no_ask, last):
    return {"ticker": t, "event_ticker": "KXFAKE-99", "status": "active", "strike_type": "greater",
            "floor_strike": k, "rules_primary": TXT.format(k=k), "rules_secondary": "", "market_type": "binary",
            "notional_value_dollars": "1.0000", "latest_expiration_time": FUTURE, "close_time": FUTURE,
            "yes_ask_dollars": yes_ask, "no_ask_dollars": no_ask, "last_price_dollars": last}


class Resp:
    def __init__(self, body, status=200):
        self._b, self.status_code, self.text = body, status, json.dumps(body)
        self.headers = {"x-cache": "Miss from cloudfront", "date": "Sun, 27 Sep 2026 00:00:00 GMT"}

    def json(self):
        return self._b


class Session:
    def __init__(self, last_a="0.40", ev_override=None, series_fee=("quadratic", 1)):
        self.headers = {}
        self.ev_override, self.series_fee = ev_override, series_fee
        self.paths = []
        self.markets = {"A": market("A", 10, "0.40", "0.72", last_a), "B": market("B", 12, "0.55", "0.53", "0.47")}
        self.books = {"A": {"orderbook_fp": {"yes_dollars": [["0.30", "50"]], "no_dollars": [["0.40", "100"], ["0.60", "5"]]}},
                      "B": {"orderbook_fp": {"yes_dollars": [["0.47", "50"]], "no_dollars": [["0.40", "50"]]}}}

    def request(self, method, url, params=None, headers=None, timeout=None):
        assert method == "GET" and "Authorization" not in (headers or {})
        path = urllib.parse.urlparse(url).path.replace("/trade-api/v2", "")
        self.paths.append(path)
        if path == "/exchange/status":
            return Resp({"trading_active": True})
        if path == "/series":
            return Resp({"series": [{"ticker": "KXFAKE", "fee_type": "quadratic", "fee_multiplier": 1,
                                     "contract_terms_url": FAKE_TERMS, "settlement_sources": []}]})
        if path == "/series/fee_changes":
            return Resp({"series_fee_change_arr": []})
        if path == "/events/fee_changes":
            return Resp({"event_fee_changes": [], "cursor": ""})
        if path.startswith("/events/") and path != "/events/fee_changes":
            return Resp({"event": {"event_ticker": path.split("/")[2], "series_ticker": "KXFAKE",
                                   **({"fee_type_override": "quadratic", "fee_multiplier_override": self.ev_override}
                                      if self.ev_override is not None else {})}})
        if path.startswith("/series/") and path != "/series/fee_changes":
            return Resp({"series": {"ticker": "KXFAKE", "fee_type": self.series_fee[0], "fee_multiplier": self.series_fee[1],
                                    "contract_terms_url": FAKE_TERMS}})
        if path == "/events":
            ev = {"event_ticker": "KXFAKE-99", "series_ticker": "KXFAKE", "mutually_exclusive": False,
                  "settlement_sources": [], "markets": list(self.markets.values())}
            return Resp({"events": [ev], "cursor": ""})
        if path.endswith("/orderbook"):
            return Resp(self.books[path.split("/")[2]])
        if path.startswith("/markets/"):
            return Resp({"market": self.markets[path.split("/")[2]]})
        return Resp({"error": "not found"}, 404)


@pytest.fixture
def fake_registry(monkeypatch):
    t = TERMS.VerifiedTerms(FAKE_TERMS, hashlib.sha256(FAKE_BYTES).hexdigest(), True, "LAST_VALUE", ("test",))
    monkeypatch.setattr(TERMS, "REGISTRY", {FAKE_TERMS: t})
    monkeypatch.setattr(config, "PERSISTENCE_REFETCH_DELAY_S", 0.05)
    monkeypatch.setattr(config, "AUDIT_FAMILIES_PER_CYCLE", 1)
    monkeypatch.setattr(config, "EVENTS_PAGE_MIN_INTERVAL_S", 0)


def read(d, kind):
    fs = [f for f in os.listdir(d) if f.startswith(f"sarb_{kind}_")]
    rows = []
    for f in fs:
        with gzip.open(os.path.join(d, f), "rt") as fh:
            rows += [json.loads(l) for l in fh]
    return rows


def run_cycle(tmp_path, session):
    c = Collector(PublicClient(session=session, per_second=1000, burst=100), str(tmp_path), seed=1,
                  terms_fetch=lambda url: FAKE_BYTES)
    return c.run_cycle()


def test_cycle_records_everything_and_confirms_lock(tmp_path, fake_registry):
    s = Session()
    res = run_cycle(tmp_path, s)
    cands = read(tmp_path, "candidates")
    p2 = [r for r in cands if r["extra"]["phase"] == "P2"]
    p3 = [r for r in cands if r["extra"]["phase"] == "P3"]
    assert len(p2) == 1 and len(p3) == 1 and p2[0]["extra"]["group"] == p3[0]["extra"]["group"]
    assert p2[0]["relationship"] == "R2_NESTED"
    assert p2[0]["status"] == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE" and "FAIL:persistence_confirmed" in p2[0]["reasons"]
    assert p3[0]["status"] == "RULE_DEFINED_LOCK" and p3[0]["persistence_confirmed"] is True
    assert p3[0]["extra"]["price_source"] == "orderbook" and "unwind" in p3[0]["extra"]
    books = read(tmp_path, "books")
    kinds = {ph: sorted((b["kind"], b["ticker"]) for b in books if b["phase"] == ph) for ph in ("P2", "P3")}
    assert kinds["P2"] == [("event", "KXFAKE-99"), ("market", "A"), ("market", "B"),
                           ("orderbook", "A"), ("orderbook", "B"), ("series", "KXFAKE")]
    # P3 (~1 s later) reuses the P2 event/series objects (< OBSERVATION_REUSE_S), fresh books + markets
    assert kinds["P3"] == [("market", "A"), ("market", "B"), ("orderbook", "A"), ("orderbook", "B")]
    assert any(b["phase"] == "AUDIT" for b in books)
    stat = read(tmp_path, "statscreen")
    assert any(r["relationship"] == "R1_LONG" and r["price_source"] == "events_summary_screen_only" for r in stat)
    ops = read(tmp_path, "ops")[0]
    assert ops["http_429"] == 0 and ops["requests_total"] > 0 and len(ops["p2_leg_fetch_ms"]) == 1 and len(ops["p3_delay_ms"]) == 1
    counts = read(tmp_path, "counts")[0]["counts"]
    assert counts["P3|R2_NESTED|RULE_DEFINED_LOCK"] == 1
    assert read(tmp_path, "rule511") == []
    uni = read(tmp_path, "universe")[0]
    assert uni["terms_verified_markets"] == 2 and uni["families"] == 1
    # metadata is fetched before books in each phase (books back-to-back)
    p = [x for x in s.paths if x.startswith("/markets/")]
    assert p[:4] == ["/markets/A", "/markets/B", "/markets/A/orderbook", "/markets/B/orderbook"]


def test_rule_5_11_rejections_go_to_separate_stream(tmp_path, fake_registry):
    s = Session(last_a="0.75")                       # executing YES A at 0.40 vs last trade 0.75
    run_cycle(tmp_path, s)
    r511 = read(tmp_path, "rule511")
    assert r511 and all(r["extra"]["rule_5_11"]["blocked_by_rule_5_11"] for r in r511)
    assert not any(r["status"] == "RULE_DEFINED_LOCK" for r in read(tmp_path, "candidates"))
    assert {r["extra"]["phase"] for r in r511} >= {"P2", "P3"}   # persistence still measured


def test_unverified_terms_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(TERMS, "REGISTRY", {})
    monkeypatch.setattr(config, "PERSISTENCE_REFETCH_DELAY_S", 0.05)
    run_cycle(tmp_path, Session())
    st = {r["status"] for r in read(tmp_path, "candidates") if r["extra"]["phase"] in ("P2", "P3")}
    assert "RULE_DEFINED_LOCK" not in st and "CANDIDATE_TERMS_UNVERIFIED" in st


def test_report_integrity_and_ops(tmp_path, fake_registry):
    from sarb.report import summarize
    run_cycle(tmp_path, Session())
    s = summarize(str(tmp_path))
    assert s["integrity"]["records_missing_leg_snapshots"] == 0 and s["integrity"]["p3_without_p2"] == 0
    assert s["ops"]["cycles"] == 1 and s["ops"]["http_429"] == 0
    assert s["candidates_by_phase_relationship_status"]["P3|R2_NESTED|RULE_DEFINED_LOCK"] == 1
    assert len(s["rule_defined_locks"]) == 1


def test_statscreen_deduplicated_across_cycles(tmp_path, fake_registry):
    c = Collector(PublicClient(session=Session(), per_second=1000, burst=100), str(tmp_path), seed=1,
                  terms_fetch=lambda url: FAKE_BYTES)
    c.run_cycle(); c.run_cycle()
    n = sum(1 for r in read(tmp_path, "statscreen") if r["relationship"] == "R1_LONG")
    counts = [r["counts"] for r in read(tmp_path, "counts")]
    assert n == 1 and counts[1].get("STATSCREEN|deduplicated", 0) >= 1


def test_fee_in_force_is_observed_and_recorded(tmp_path, fake_registry):
    run_cycle(tmp_path, Session(ev_override=2))
    p2 = [r for r in read(tmp_path, "candidates") if r["extra"]["phase"] == "P2"]
    prov = p2[0]["extra"]["fee_provenance"]
    # M=2 override doubles fees: the planted 0.07 edge no longer survives -> not a lock
    assert p2[0]["status"] == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"
    assert "FAIL:edge_positive_all_scenarios_some_size" in p2[0]["reasons"]
    assert all(v[1] == "2" and v[0].startswith("event_object_observed") for v in prov.values())
    kinds = {b["kind"] for b in read(tmp_path, "books") if b["phase"] == "P2"}
    assert {"event", "series", "market", "orderbook"} <= kinds


def test_unsupported_fee_type_in_force_gives_fee_unresolved(tmp_path, fake_registry):
    run_cycle(tmp_path, Session(series_fee=("flat", 1)))
    st = {r["status"] for r in read(tmp_path, "candidates") if r["extra"]["phase"] == "P2"}
    assert st == {"FEE_UNRESOLVED"}
