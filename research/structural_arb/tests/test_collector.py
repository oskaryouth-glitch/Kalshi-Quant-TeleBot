import gzip, json, os
from sarb.collector import Collector
from sarb.client import TimedResponse


class FakeClient:
    def __init__(self):
        self.calls = []
    def _r(self, path, body):
        self.calls.append(path)
        return TimedResponse(path, {}, 200, body, 1, 2, 1, 2)
    def exchange_status(self): return self._r("/exchange/status", {"trading_active": True})
    def series(self, t): return self._r(f"/series/{t}", {"series": {"ticker": t, "fee_type": "quadratic", "fee_multiplier": 1}})
    def orderbook(self, t): return self._r(f"/markets/{t}/orderbook", {"orderbook_fp": {"yes_dollars": [], "no_dollars": []}})
    def iter_events(self):
        yield self._r("/events", {"events": [
            {"event_ticker": "E1", "series_ticker": "S1", "markets": [{"ticker": "M1", "status": "active"}, {"ticker": "M2", "status": "active"}, {"ticker": "M3", "status": "closed"}]},
            {"event_ticker": "E2", "series_ticker": "S1", "markets": [{"ticker": "N1", "status": "active"}]},
        ], "cursor": ""})


def _read(d, kind):
    [fn] = [f for f in os.listdir(d) if f.startswith(f"sarb_{kind}_")]
    with gzip.open(os.path.join(d, fn), "rt") as fh:
        return [json.loads(l) for l in fh]


def test_cycle(tmp_path):
    fc = FakeClient()
    stats = Collector(fc, str(tmp_path)).run_cycle()
    assert stats["events"] == 2 and stats["groups"] == 1 and stats["books"] == 2
    assert fc.calls.count("/series/S1") == 1          # series fetched once
    assert "/markets/M3/orderbook" not in fc.calls   # inactive market skipped
    [g] = _read(tmp_path, "books")
    assert g["event_ticker"] == "E1" and [b["ticker"] for b in g["books"]] == ["M1", "M2"]
    assert g["group_sent_utc_ns"] == 1 and g["group_recv_utc_ns"] == 2
    assert len(_read(tmp_path, "events")) == 2
