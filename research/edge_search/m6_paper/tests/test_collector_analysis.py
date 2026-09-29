"""Collector (fake HTTP; no network), safety scans, and the frozen inference/decision rules."""
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
from decimal import Decimal as D

import pytest

from m6_paper import analysis as AN
from m6_paper import collector as C
from m6_paper import selection as SEL
from m6_paper import spec as S
from m6_paper import storage as ST

PKG = pathlib.Path(C.__file__).resolve().parent
NS = 10**9
NOW = SEL.ts_ns("2026-10-01T06:00:10Z")
BOOK = {"yes_dollars": [["0.40", "600"]], "no_dollars": [["0.55", "700"]]}


def program(i):
    return {"id": f"p{i:03d}", "market_ticker": f"M{i:03d}", "incentive_type": "liquidity",
            "start_date": "2026-09-30T12:00:00Z", "end_date": "2026-10-05T00:00:00Z",
            "period_reward": 1_000_000 + i, "target_size_fp": "1000.00", "discount_factor_bps": 5000}


class Fake:
    def __init__(self, n=120):
        self.calls, self.n = [], n
        self.trades = []
        self.volume = {}

    def __call__(self, url):
        u = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(u.query)
        path = u.path.replace("/trade-api/v2", "")
        self.calls.append((u.netloc, path, q))
        if path == "/incentive_programs":
            body = {"incentive_programs": [program(i) for i in range(self.n)] if q["status"] == ["active"] else []}
        elif path == "/markets":
            body = {"markets": [{"ticker": t, "event_ticker": "E" + t, "status": "active", "volume_24h_fp": "0",
                                 "volume_fp": str(self.volume.get(t, 0)), "close_time": "2027-01-01T00:00:00Z"}
                                for t in q["tickers"][0].split(",")]}
        elif path == "/markets/orderbooks":
            body = {"orderbooks": [{"ticker": t, "orderbook_fp": BOOK} for t in q["tickers"]]}
        elif path == "/series":
            body = {"series": [{"ticker": f"S{i:03d}", "fee_type": "quadratic", "fee_multiplier": 1} for i in range(self.n)]}
        elif path == "/events":
            body = {"events": [{"event_ticker": f"EM{i:03d}", "series_ticker": f"S{i:03d}"} for i in range(self.n)]}
        elif path.startswith("/events/"):
            e = path.split("/")[2]
            body = {"event": {"event_ticker": e, "series_ticker": "S" + e[2:]}}
        elif path.startswith("/series/") and path != "/series/fee_changes":
            body = {"series": {"ticker": path.split("/")[2], "fee_type": "quadratic", "fee_multiplier": 1}}
        elif path == "/series/fee_changes":
            body = {"series_fee_change_arr": []}
        elif path == "/markets/trades":
            body = {"trades": [t for t in self.trades if "ticker" not in q or t["ticker"] == q["ticker"][0]]}
        else:
            return 404, b"{}"
        return 200, json.dumps(body).encode()


def collector(tmp_path, fake):
    http = C.Http(opener=fake, rate=1e9, sleep=lambda s: None)
    return C.Collector(http, ST.Writer(str(tmp_path)), now_ns=lambda: NOW)


def test_http_is_get_only_and_allowlisted():
    http = C.Http(opener=Fake(), rate=1e9, sleep=lambda s: None)
    for bad in ("/portfolio/orders", "/portfolio/balance", "/orders", "/markets/X/orders", "/api_keys"):
        with pytest.raises(PermissionError):
            http.api(bad)
    assert http.api("/series")["series"]


def test_epoch_records_raw_data_and_tracks_top100(tmp_path):
    fake = Fake(120)
    c = collector(tmp_path, fake)
    rec = c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    assert len(rec["programs"]) == 120 and len(rec["books"]) == 120 and rec["event_series"]["EM007"] == "S007"
    tracked = list(ST.read(str(tmp_path), "tracked"))[0]
    assert len(tracked["set"]) == S.TOP_TRACK
    assert all(h.startswith("api.elections.kalshi.com") for h, _, _ in fake.calls)


def test_books_are_recorded_change_only_and_trades_deduplicated(tmp_path):
    fake = Fake(3)
    c = collector(tmp_path, fake)
    c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    a, b = c.poll_books(), c.poll_books()
    assert len(a["books"]) == 3 and b["books"] == {} and len(b["same"]) == 3
    tr = {"ticker": "M001", "trade_id": "x1", "created_time": "2026-10-01T06:00:05Z", "count_fp": "5.00",
          "taker_side": "no", "yes_price_dollars": "0.4000", "no_price_dollars": "0.6000"}
    fake.trades = [tr, {**tr, "trade_id": "x2", "ticker": "UNTRACKED"}]
    assert c.poll_trades() == 1 and c.poll_trades() == 0


def test_completeness_gap_triggers_backfill(tmp_path):
    fake = Fake(2)
    c = collector(tmp_path, fake)
    c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    fake.volume = {"M000": 100}
    c.completeness()                                   # baseline
    fake.volume = {"M000": 150}
    fake.trades = [{"ticker": "M000", "trade_id": "b1", "created_time": "2026-10-01T06:00:05Z", "count_fp": "50.00",
                    "taker_side": "no", "yes_price_dollars": "0.4000", "no_price_dollars": "0.6000"}]
    c.completeness()
    rows = [r for r in ST.read(str(tmp_path), "completeness") if r["ticker"] == "M000"]
    assert D(rows[-1]["gap"]) == 1 and rows[-1]["backfilled"] == 1
    assert [t["trade_id"] for r in ST.read(str(tmp_path), "trades") for t in r["trades"]] == ["b1"]


def test_restart_restores_tracking_from_recorded_streams(tmp_path):
    fake = Fake(5)
    c = collector(tmp_path, fake)
    c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    c2 = collector(tmp_path, fake)
    assert c2.restore() == 5 and set(c2.tracked) == set(c.tracked) and c2.last_epoch_ns == c.last_epoch_ns


def test_epoch_boundaries():
    assert C.epoch_due(None, SEL.ts_ns("2026-10-01T07:30:00Z")) == SEL.ts_ns("2026-10-01T06:00:00Z")
    assert C.epoch_due(SEL.ts_ns("2026-10-01T06:00:00Z"), SEL.ts_ns("2026-10-01T11:59:59Z")) is None
    assert C.epoch_due(None, SEL.ts_ns("2026-10-01T03:00:00Z")) == SEL.ts_ns("2026-10-01T00:00:00Z")


def test_collector_refuses_to_start_without_explicit_approval(tmp_path):
    r = subprocess.run([sys.executable, "-m", "m6_paper.collector", "--data-dir", str(tmp_path), "--mode", "full"],
                       cwd=str(PKG.parent), capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "NOT approved" in (r.stderr + r.stdout)
    assert not list(tmp_path.iterdir())


def test_source_has_no_order_or_credential_paths():
    src = "\n".join(p.read_text() for p in PKG.glob("*.py"))
    assert not re.search(r"/portfolio|KALSHI-ACCESS|Authorization|api_key|private_key|method=\"(POST|PUT|DELETE)\"", src)
    assert "method=\"GET\"" in (PKG / "collector.py").read_text()


# ---------------------------------------------------------------- inference and decision rules
def test_bootstrap_is_deterministic_and_sensible():
    rows = [(f"E{i % 7}", D(i % 5) - D("1.5")) for i in range(40)]
    assert AN.bootstrap_lb95(rows) == AN.bootstrap_lb95(list(reversed(rows)))
    assert AN.bootstrap_lb95([(f"E{i}", D(1)) for i in range(25)]) == 25
    assert AN.bootstrap_lb95([(f"E{i}", D(i) - D(12)) for i in range(25)]) < 0


@pytest.mark.parametrize("net,lb,wo,n,v", [(D(5), D(1), D(1), 20, "SURVIVE"), (D(5), D(1), D(-1), 20, "INCONCLUSIVE"),
                                           (D(5), D(-1), D(1), 20, "INCONCLUSIVE"), (D(0), D(-1), D(-3), 20, "KILL"),
                                           (D(9), D(9), D(9), 19, "INSUFFICIENT_EVIDENCE")])
def test_verdict_rules(net, lb, wo, n, v):
    assert AN.verdict(net, lb, wo, n) == v


def test_m6_overall_uses_ranked_arms_only():
    r = {"P30": {"verdict": "KILL"}, "P100": {"verdict": "KILL"}, "P200": {"verdict": "KILL"}, "U": {"verdict": "REPORTED_ONLY"}}
    assert AN.m6_overall(r) == "KILL"
    r["P100"]["verdict"] = "SURVIVE"
    assert AN.m6_overall(r) == "SURVIVE"
    r["P100"]["verdict"] = "INSUFFICIENT_EVIDENCE"
    assert AN.m6_overall(r) == "INCONCLUSIVE"
