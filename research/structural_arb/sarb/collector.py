"""Forward snapshot collector (read-only, public endpoints only).

Kalshi publishes no historical order-book depth, so every executable observation must be
collected forward. One cycle:
  1. GET /exchange/status
  2. page through GET /events?status=open&with_nested_markets=true  -> raw event metadata
  3. GET /series/{t} once per series per run                           -> fee_type / multiplier
  4. for each event with >= 2 active markets, fetch every market's order book back-to-back
     (a "group snapshot") so intra-event legs are as close in time as REST allows.

Raw responses are stored verbatim with per-request timestamps, so evaluation can be re-run
offline with any future version of the evaluator (no information is discarded or pre-judged).

Output files (git-ignored, isolated prefix):  data/sarb_<kind>_<UTCdate>.jsonl.gz
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import logging
import os
import time
import uuid

from .client import PublicClient, TimedResponse

log = logging.getLogger("sarb.collector")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _path(kind: str, data_dir: str) -> str:
    return os.path.join(data_dir, f"sarb_{kind}_{dt.datetime.now(dt.timezone.utc):%Y%m%d}.jsonl.gz")


def _append(path: str, obj: dict) -> None:
    with gzip.open(path, "at", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def _timing(r: TimedResponse) -> dict:
    return {"path": r.path, "params": r.params, "status": r.status, "sent_utc_ns": r.sent_utc_ns,
            "recv_utc_ns": r.recv_utc_ns, "latency_ns": r.latency_ns}


def _active(m: dict) -> bool:
    return str(m.get("status", "")).lower() in {"active", "open"}


class Collector:
    def __init__(self, client: PublicClient, data_dir: str = DATA_DIR, series_filter: set[str] | None = None,
                 max_events: int | None = None, min_markets: int = 2):
        self.client = client
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.series_filter = series_filter
        self.max_events = max_events
        self.min_markets = min_markets
        self._series_seen: set[str] = set()

    def run_cycle(self) -> dict:
        cycle_id = uuid.uuid4().hex
        stats = {"cycle_id": cycle_id, "events": 0, "groups": 0, "books": 0, "errors": 0}
        st = self.client.exchange_status()
        _append(_path("exchange", self.data_dir), {"cycle_id": cycle_id, **_timing(st), "body": st.body})

        n_events = 0
        for page in self.client.iter_events():
            if page.status != 200:
                stats["errors"] += 1
                log.warning("events page status %s", page.status)
                break
            for ev in page.body.get("events", []):
                series = ev.get("series_ticker")
                if self.series_filter and series not in self.series_filter:
                    continue
                n_events += 1
                _append(_path("events", self.data_dir), {"cycle_id": cycle_id, **_timing(page), "event": ev})
                if series and series not in self._series_seen:
                    sr = self.client.series(series)
                    _append(_path("series", self.data_dir), {"cycle_id": cycle_id, **_timing(sr), "body": sr.body})
                    self._series_seen.add(series)
                markets = [m for m in ev.get("markets") or [] if _active(m)]
                if len(markets) >= self.min_markets:
                    self._snapshot_group(cycle_id, ev, markets, stats)
                if self.max_events and n_events >= self.max_events:
                    stats["events"] = n_events
                    return stats
        stats["events"] = n_events
        return stats

    def _snapshot_group(self, cycle_id: str, ev: dict, markets: list[dict], stats: dict) -> None:
        books = []
        for m in markets:
            try:
                r = self.client.orderbook(m["ticker"])
            except Exception as e:   # network errors are recorded, never silently dropped
                stats["errors"] += 1
                books.append({"ticker": m["ticker"], "error": repr(e)})
                continue
            books.append({"ticker": m["ticker"], **_timing(r), "body": r.body})
            stats["books"] += 1
        ok = [b for b in books if "sent_utc_ns" in b]
        _append(_path("books", self.data_dir), {
            "snapshot_id": uuid.uuid4().hex, "cycle_id": cycle_id,
            "event_ticker": ev.get("event_ticker"), "series_ticker": ev.get("series_ticker"),
            "group_sent_utc_ns": min((b["sent_utc_ns"] for b in ok), default=None),
            "group_recv_utc_ns": max((b["recv_utc_ns"] for b in ok), default=None),
            "books": books,
        })
        stats["groups"] += 1


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Read-only Kalshi snapshot collector (no auth, no orders).")
    ap.add_argument("--series", nargs="*", help="restrict to these series tickers")
    ap.add_argument("--max-events", type=int)
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--sleep", type=float, default=60.0, help="seconds between cycles")
    ap.add_argument("--data-dir", default=DATA_DIR)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    c = Collector(PublicClient(), a.data_dir, set(a.series) if a.series else None, a.max_events)
    for i in range(a.cycles):
        log.info("cycle %d: %s", i, c.run_cycle())
        if i + 1 < a.cycles:
            time.sleep(a.sleep)


if __name__ == "__main__":
    main()
