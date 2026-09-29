"""M6 paper experiment collector (DESIGN §2). Records raw public data; places NO orders.

Only unauthenticated GETs to an explicit allowlist of read endpoints (`ALLOWED`); anything else raises.
No credentials are read. Output: storage.Writer streams under --data-dir.

Modes
  full        epochs (selection + tracking), programs, book polls, trades, market state, fee state,
              completeness checks, LIP-rules watch. Used from start until the last arm's formal checkpoint.
  tail        no new epochs; keeps polling books/trades/state for markets still inside their tracked period.
  settlement  market state (and a daily book for liquidation marks) for every ever-tracked market until
              it settles, up to the settlement cutoff.

Usage: python -m m6_paper.collector --data-dir DIR --mode full   (NOT STARTED; see PREREG_M6_PAPER.md)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal as D

from . import selection as SEL
from . import spec as S
from . import storage as ST

NS = 1_000_000_000
ALLOWED = (re.compile(r"^/incentive_programs$"), re.compile(r"^/markets$"), re.compile(r"^/markets/orderbooks$"),
           re.compile(r"^/markets/trades$"), re.compile(r"^/series$"), re.compile(r"^/series/fee_changes$"),
           re.compile(r"^/series/[A-Za-z0-9_.\-]+$"), re.compile(r"^/events$"), re.compile(r"^/events/[A-Za-z0-9_.\-]+$"))
LIP_KEY = re.compile(r"liquidity|incentive", re.I)


class Http:
    """Rate-limited GET-only client. `opener(url) -> (status, bytes)` is injectable for tests."""

    def __init__(self, opener=None, rate: float = S.MAX_REQUESTS_PER_S, clock=time.monotonic, sleep=time.sleep):
        self.opener = opener or self._urlopen
        self.min_gap, self.clock, self.sleep = 1.0 / rate, clock, sleep
        self.last = -1e9
        self.stats = {"requests": 0, "http_429": 0, "errors": 0}

    @staticmethod
    def _urlopen(url: str):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def _raw(self, url: str) -> tuple[int, bytes]:
        for attempt in range(8):
            wait = self.min_gap - (self.clock() - self.last)
            if wait > 0:
                self.sleep(wait)
            self.last = self.clock()
            self.stats["requests"] += 1
            try:
                status, body = self.opener(url)
            except Exception:                                       # noqa: BLE001  transport errors: retry
                self.stats["errors"] += 1
                self.sleep(min(2 ** attempt, 30))
                continue
            if status == 429 or status >= 500:
                self.stats["http_429" if status == 429 else "errors"] += 1
                self.sleep(min(2 ** attempt, 30))
                continue
            return status, body
        raise RuntimeError("GET failed repeatedly: " + url)

    def api(self, path: str, params: list[tuple[str, str]] | dict | None = None) -> dict:
        if not any(p.match(path) for p in ALLOWED):
            raise PermissionError(f"endpoint not on the read-only allowlist: {path}")
        q = urllib.parse.urlencode(params or {}, doseq=True)
        status, body = self._raw(S.API + path + ("?" + q if q else ""))
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {path}")
        return json.loads(body)

    def bucket_list(self, prefix: str) -> list[str]:
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        keys, token = [], None
        while True:
            q = {"list-type": "2", "prefix": prefix, **({"continuation-token": token} if token else {})}
            status, body = self._raw(S.BUCKET_URL + "?" + urllib.parse.urlencode(q))
            if status != 200:
                raise RuntimeError(f"bucket HTTP {status}")
            root = ET.fromstring(body)
            keys += [c.findtext("s3:Key", namespaces=ns) for c in root.findall("s3:Contents", ns)]
            if root.findtext("s3:IsTruncated", namespaces=ns) != "true":
                return keys
            token = root.findtext("s3:NextContinuationToken", namespaces=ns)


def paged(http: Http, path: str, key: str, params: dict, cursor_key: str = "cursor") -> list:
    out, cur = [], None
    for _ in range(10_000):
        d = http.api(path, {**params, **({"cursor": cur} if cur else {})})
        out += d.get(key) or []
        cur = d.get(cursor_key) or d.get("next_cursor")
        if not cur or not d.get(key):
            return out
    raise RuntimeError("pagination did not terminate: " + path)


MARKET_FIELDS = ("ticker", "event_ticker", "status", "close_time", "result", "settlement_value_dollars", "volume_fp",
                 "volume_24h_fp", "price_ranges", "mve_collection_ticker", "can_close_early", "expiration_time")


class Collector:
    def __init__(self, http: Http, writer: ST.Writer, now_ns=time.time_ns, rng: random.Random | None = None):
        self.h, self.w, self.now = http, writer, now_ns
        self.rng = rng or random.Random()
        self.tracked: dict[str, dict] = {}        # ticker -> {"until_ns", "programs": set, "since_ns"}
        self.ever: dict[str, int] = {}            # ticker -> first tracked ns
        self.last_book_hash: dict[str, str] = {}
        self.seen_trades: dict[str, int] = {}     # trade_id -> created ns (pruned)
        self.trades_min_ts = None
        self.vol_base: dict[str, tuple[D, D, int]] = {}   # ticker -> (volume_fp at base, traded since base, base_ns)
        self.lip_keys: set[str] | None = None
        self.last_epoch_ns = None
        self.trades_polls = 0
        self.pending_fee_markets: list[tuple[str, str]] = []   # (ticker, scope) fee objects still to record

    # ------------------------------------------------------------------ epoch: selection + tracking
    def epoch(self, epoch_ns: int) -> dict:
        start = self.now()
        programs = paged(self.h, "/incentive_programs", "incentive_programs", {"status": "active", "type": "liquidity", "limit": 1000})
        upcoming = paged(self.h, "/incentive_programs", "incentive_programs", {"status": "upcoming", "type": "liquidity", "limit": 1000})
        tickers = sorted({g["market_ticker"] for g in programs if g.get("market_ticker")})
        markets = {}
        for i in range(0, len(tickers), S.MARKETS_PER_CALL):
            for m in self.h.api("/markets", {"tickers": ",".join(tickers[i:i + S.MARKETS_PER_CALL]), "limit": 1000}).get("markets", []):
                markets[m["ticker"]] = {k: m.get(k) for k in MARKET_FIELDS}
        books = self._books(tickers)
        series_raw = self.h.api("/series").get("series", [])
        series_t = self.now()
        series = {s["ticker"]: {k: v for k, v in s.items() if "fee" in k} for s in series_raw}   # raw fee fields
        events = paged(self.h, "/events", "events", {"status": "open", "limit": 200})
        events_t = self.now()
        event_series = {e["event_ticker"]: e.get("series_ticker") for e in events}
        rec = {"t_ns": self.now(), "epoch_ns": epoch_ns, "epoch_started_ns": start, "programs": programs, "upcoming": upcoming,
               "markets": markets, "books": {t: b for t, (b, _) in books.items()}, "missing_books": sorted(set(tickers) - set(books)),
               "series_fee": {s: series[s] for s in set(event_series.values()) if s in series}, "event_series": event_series,
               "fee_provenance": {"series_fee": "GET /series (series-level fee fields, raw)", "series_fee_t_ns": series_t,
                                  "event_series": "GET /events?status=open (series_ticker; no fee overrides in list)",
                                  "event_series_t_ns": events_t}}
        self.w.write("epoch", rec)
        cands = SEL.candidates(rec)
        rank = SEL.ranked(cands)
        adds = [(c, "top100") for c in rank[:S.TOP_TRACK]]
        if dt.datetime.fromtimestamp(epoch_ns / NS, dt.timezone.utc).hour == S.U_EPOCH_HOUR_UTC:
            adds += [(c, "arm_u") for c in SEL.u_draw(cands, epoch_ns, SEL.epoch_day(epoch_ns))]
        self._track(adds)
        self.last_epoch_ns = epoch_ns
        self.w.write("ops", {"t_ns": self.now(), "kind": "collection_gap", "reason": "epoch", "start_ns": start,
                             "end_ns": self.now(), "note": "planned selection pause; no book polls; not compensated"})
        return rec

    def _track(self, adds) -> None:
        now = self.now()
        new = []
        for c, why in adds:
            t = self.tracked.setdefault(c.ticker, {"until_ns": 0, "programs": set(), "since_ns": now})
            t["until_ns"] = max(t["until_ns"], c.end_ns)
            t["programs"].add(c.program_id)
            if c.ticker not in self.ever:
                self.ever[c.ticker] = now
                new.append(c.ticker)
                self.pending_fee_markets.append((c.ticker, "new_markets"))
            self.vol_base.setdefault(c.ticker, (None, D(0), now))
        self.w.write("tracked", {"t_ns": now, "add": [{"ticker": c.ticker, "program_id": c.program_id, "until_ns": c.end_ns,
                                                       "reason": why} for c, why in adds],
                                 "set": sorted(self.tracked), "new_markets": new})

    def restore(self) -> int:
        """Rebuild tracking state from the recorded streams after a restart (the tracked set is otherwise
        in memory only). Returns the number of markets restored."""
        for rec in ST.read(self.w.root, "tracked"):
            for a in rec.get("add", []):
                t = self.tracked.setdefault(a["ticker"], {"until_ns": 0, "programs": set(), "since_ns": rec["t_ns"]})
                t["until_ns"] = max(t["until_ns"], a["until_ns"])
                t["programs"].add(a["program_id"])
                self.ever.setdefault(a["ticker"], rec["t_ns"])
        for rec in ST.read(self.w.root, "epoch"):
            self.last_epoch_ns = max(self.last_epoch_ns or 0, rec["epoch_ns"])
        self.expire()
        return len(self.tracked)

    def expire(self) -> None:
        now = self.now()
        for t in [t for t, v in self.tracked.items() if v["until_ns"] <= now]:
            del self.tracked[t]

    # ------------------------------------------------------------------ polls
    def _books(self, tickers: list[str]) -> dict[str, tuple[dict, str]]:
        out = {}
        for i in range(0, len(tickers), S.BOOKS_PER_CALL):
            chunk = tickers[i:i + S.BOOKS_PER_CALL]
            d = self.h.api("/markets/orderbooks", [("tickers", t) for t in chunk])
            for b in d.get("orderbooks", []):
                ob = b.get("orderbook_fp") or {}
                out[b["ticker"]] = (ob, hashlib.sha256(json.dumps(ob, sort_keys=True).encode()).hexdigest())
        return out

    def poll_books(self) -> dict:
        tickers = sorted(self.tracked)
        if not tickers:
            return {}
        got = self._books(tickers)
        t = self.now()
        changed = {k: b for k, (b, h) in got.items() if self.last_book_hash.get(k) != h}
        for k, (_, h) in got.items():
            self.last_book_hash[k] = h
        rec = {"t_ns": t, "books": changed, "same": sorted(set(got) - set(changed)), "missing": sorted(set(tickers) - set(got))}
        self.w.write("books", rec)
        return rec

    def poll_trades(self) -> int:
        now_s = self.now() // NS
        min_ts = (self.trades_min_ts or now_s) - S.TRADES_OVERLAP_S
        rows = paged(self.h, "/markets/trades", "trades", {"min_ts": min_ts, "limit": 1000})
        keep = []
        for r in rows:
            if r["ticker"] in self.tracked and r["trade_id"] not in self.seen_trades:
                self.seen_trades[r["trade_id"]] = SEL.ts_ns(r["created_time"])
                keep.append(r)
                vb = self.vol_base.get(r["ticker"])
                if vb:
                    self.vol_base[r["ticker"]] = (vb[0], vb[1] + D(r["count_fp"]), vb[2])
        if keep:
            self.w.write("trades", {"t_ns": self.now(), "trades": keep, "source": "feed"})
        self.trades_min_ts = now_s
        self.trades_polls += 1
        horizon = (now_s - 3600) * NS
        self.seen_trades = {k: v for k, v in self.seen_trades.items() if v >= horizon}
        return len(keep)

    def poll_markets(self, tickers: list[str]) -> dict:
        out = {}
        for i in range(0, len(tickers), S.MARKETS_PER_CALL):
            for m in self.h.api("/markets", {"tickers": ",".join(tickers[i:i + S.MARKETS_PER_CALL]), "limit": 1000}).get("markets", []):
                out[m["ticker"]] = {k: m.get(k) for k in MARKET_FIELDS}
        if out:
            self.w.write("markets", {"t_ns": self.now(), "markets": out})
        return out

    def poll_feestate(self, tickers: list[str] | None = None, scope: str = "full") -> None:
        """Fee provenance for tracked markets: each event object (series + any fee override) and each series
        object, with its own receive time, plus the series fee-change history. Raw fee fields are kept."""
        ms = self.poll_markets(sorted(self.tracked) if tickers is None else tickers) if (self.tracked or tickers) else {}
        events = {}
        for e in sorted({m["event_ticker"] for m in ms.values()}):
            ev = self.h.api(f"/events/{e}").get("event") or {}
            events[e] = {"t_ns": self.now(), "series_ticker": ev.get("series_ticker"),
                         **{k: v for k, v in ev.items() if "fee" in k}}
        series = {}
        for s in sorted({v["series_ticker"] for v in events.values() if v.get("series_ticker")}):
            so = self.h.api(f"/series/{s}").get("series") or {}
            series[s] = {"t_ns": self.now(), **{k: v for k, v in so.items() if "fee" in k}}
        self.w.write("feestate", {"t_ns": self.now(), "scope": scope, "events": events, "series": series})

    def poll_fee_changes(self) -> None:
        ch = self.h.api("/series/fee_changes", {"show_historical": "true"})
        self.w.write("feestate", {"t_ns": self.now(), "scope": "fee_changes", "events": {}, "series": {},
                                  "fee_changes_t_ns": self.now(),
                                  "fee_changes": ch.get("series_fee_change_arr") or ch.get("series_fee_changes") or []})

    def schedule_full_fees(self) -> None:
        """6-hourly refresh: the fee-change history now (one call), and every tracked market's event/series fee
        objects queued for incremental fetching, so no single loop pass blocks book polling."""
        self.poll_fee_changes()
        queued = {t for t, _ in self.pending_fee_markets}
        self.pending_fee_markets += [(t, "full") for t in sorted(self.tracked) if t not in queued]

    def poll_new_fees(self) -> int:
        """Fee objects for up to FEES_NEW_PER_LOOP queued markets (interleaved with book polls)."""
        batch, self.pending_fee_markets = self.pending_fee_markets[:S.FEES_NEW_PER_LOOP], self.pending_fee_markets[S.FEES_NEW_PER_LOOP:]
        for scope in sorted({s for _, s in batch}):
            self.poll_feestate([t for t, s in batch if s == scope], scope=scope)
        return len(batch)

    def completeness(self) -> None:
        """Volume of each tracked market vs trades recorded since the last check; a gap > 1% triggers a
        per-ticker backfill from the previous check and is flagged (DESIGN §2, §6)."""
        ms = self.poll_markets(sorted(self.tracked)) if self.tracked else {}
        now = self.now()
        for t, m in ms.items():
            vol = D(str(m.get("volume_fp") or 0))
            base, traded, base_ns = self.vol_base.get(t, (None, D(0), now))
            if base is None:
                self.vol_base[t] = (vol, D(0), now)
                continue
            dv = vol - base
            gap = (dv - traded) / dv if dv > 0 else D(0)
            back = 0
            if gap > S.COMPLETENESS_GAP:
                rows = paged(self.h, "/markets/trades", "trades", {"ticker": t, "min_ts": base_ns // NS - S.TRADES_OVERLAP_S, "limit": 1000})
                new = [r for r in rows if r["trade_id"] not in self.seen_trades]
                for r in new:
                    self.seen_trades[r["trade_id"]] = SEL.ts_ns(r["created_time"])
                if new:
                    self.w.write("trades", {"t_ns": now, "trades": new, "source": "backfill"})
                back = len(new)
            self.w.write("completeness", {"t_ns": now, "ticker": t, "volume_delta": dv, "traded": traded, "gap": gap,
                                          "backfilled": back})
            self.vol_base[t] = (vol, D(0), now)

    def rules_watch(self) -> None:
        keys = {k for k in self.h.bucket_list("regulatory/notices/") if LIP_KEY.search(k)}
        new = sorted(keys - self.lip_keys) if self.lip_keys is not None else []
        self.w.write("rules", {"t_ns": self.now(), "lip_keys": sorted(keys), "new": new})
        self.lip_keys = keys


def epoch_due(last_epoch_ns: int | None, now_ns: int) -> int | None:
    """The most recent epoch boundary (00/06/12/18 UTC) not yet run, if any."""
    t = dt.datetime.fromtimestamp(now_ns / NS, dt.timezone.utc)
    hours = [h for h in S.EPOCH_HOURS_UTC if h <= t.hour]
    b = (t.replace(hour=max(hours), minute=0, second=0, microsecond=0) if hours else
         (t - dt.timedelta(days=1)).replace(hour=max(S.EPOCH_HOURS_UTC), minute=0, second=0, microsecond=0))
    b_ns = int(b.timestamp()) * NS
    return b_ns if last_epoch_ns is None or b_ns > last_epoch_ns else None


def check_dir(kinds: set, validation: bool, data_dir: str) -> None:
    """Validation data and prospective data can never share a directory."""
    if validation and ("validation" not in data_dir or kinds - {"validation"}):
        raise SystemExit("validation runs need a fresh directory whose path contains 'validation'")
    if not validation and ("validation" in kinds or "validation" in data_dir):
        raise SystemExit("refusing to mix validation and prospective data in one directory")


def run(data_dir: str, mode: str, code_hashes: dict, until_ns: int | None = None, validation: bool = False) -> None:  # pragma: no cover
    w = ST.Writer(data_dir)
    http = Http()
    c = Collector(http, w, rng=random.Random())
    now = time.time_ns()
    kinds = {r.get("kind") for r in ST.read(data_dir, "meta")}
    check_dir(kinds, validation, data_dir)
    first = "start" not in kinds
    restored = c.restore()
    w.write("meta", {"t_ns": now, "kind": "validation" if validation else ("start" if first else "restart"), "mode": mode,
                     "spec_version": S.SPEC_VERSION, "code_sha256": code_hashes, "restored_tracked": restored})
    if validation and not c.last_epoch_ns:
        c.epoch(epoch_due(None, now))             # validation only: exercise one epoch immediately
    elif first:
        c.last_epoch_ns = epoch_due(None, now)    # the first epoch is the NEXT 00/06/12/18 UTC boundary
    nxt = {"programs": 0, "trades": 0, "books": 0, "markets": 0, "fees": 0, "complete": 0, "rules": 0, "ops": 0}
    while until_ns is None or time.time_ns() < until_ns:
        t = time.monotonic()
        t_wall = time.time_ns()
        try:
            if mode == "full":
                e = epoch_due(c.last_epoch_ns, time.time_ns())
                if e is not None:
                    c.epoch(e)
            c.expire()
            if mode in ("full", "tail"):
                c.poll_new_fees()
                if t >= nxt["books"]:
                    c.poll_books()
                    nxt["books"] = t + c.rng.expovariate(1.0 / S.BOOK_POLL_MEAN_S)
                if t >= nxt["trades"]:
                    c.poll_trades(); nxt["trades"] = t + S.TRADES_POLL_S
                if t >= nxt["markets"]:
                    c.poll_markets(sorted(set(c.tracked) | set(c.ever))); nxt["markets"] = t + S.MARKETS_POLL_S
                if t >= nxt["fees"]:
                    c.schedule_full_fees(); nxt["fees"] = t + S.FEESTATE_POLL_S
                if t >= nxt["complete"]:
                    c.completeness(); nxt["complete"] = t + S.COMPLETENESS_S
            if mode == "full" and t >= nxt["programs"]:
                w.write("programs", {"t_ns": time.time_ns(), "active": paged(http, "/incentive_programs", "incentive_programs",
                                                                              {"status": "active", "type": "liquidity", "limit": 1000})})
                nxt["programs"] = t + S.PROGRAMS_POLL_S
            if t >= nxt["rules"]:
                c.rules_watch(); nxt["rules"] = t + S.RULES_WATCH_S
            if mode == "settlement" and t >= nxt["markets"]:
                ms = c.poll_markets(sorted(c.ever))
                c.tracked = {k: {"until_ns": 0, "programs": set(), "since_ns": 0} for k, m in ms.items()
                             if m.get("status") not in ("settled", "finalized")}
                c.poll_books(); c.tracked = {}
                nxt["markets"] = t + S.POST_SETTLEMENT_POLL_S
        except Exception as ex:                                  # noqa: BLE001  keep running; everything is logged
            w.write("ops", {"t_ns": time.time_ns(), "error": repr(ex)[:500]})
        took = time.monotonic() - t
        if took > S.LOOP_STALL_GAP_S:
            w.write("ops", {"t_ns": time.time_ns(), "kind": "collection_gap", "reason": "loop_stall", "start_ns": t_wall,
                            "end_ns": time.time_ns(), "note": "not compensated"})
        if t >= nxt["ops"]:
            w.write("ops", {"t_ns": time.time_ns(), **http.stats, "tracked": len(c.tracked), "ever": len(c.ever),
                            "trades_polls": c.trades_polls, "pending_fee_markets": len(c.pending_fee_markets)})
            nxt["ops"] = t + 60
        time.sleep(0.2)


def main():                                                      # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--mode", choices=("full", "tail", "settlement"), required=True)
    ap.add_argument("--i-have-reviewer-approval-to-start", action="store_true")
    ap.add_argument("--validation", action="store_true",
                    help="short operational validation into a quarantined directory (path must contain 'validation')")
    ap.add_argument("--until-utc", default=None)
    a = ap.parse_args()
    if a.validation:
        if "validation" not in a.data_dir or not a.until_utc:
            raise SystemExit("validation runs need --until-utc and a data dir whose path contains 'validation'")
    elif not a.i_have_reviewer_approval_to_start:
        raise SystemExit("M6 collection is NOT approved to start (PREREG_M6_PAPER.md). Refusing.")
    from .prereg import code_hashes
    until = int(dt.datetime.fromisoformat(a.until_utc.replace("Z", "+00:00")).timestamp()) * NS if a.until_utc else None
    run(a.data_dir, a.mode, code_hashes(), until, validation=a.validation)


if __name__ == "__main__":                                       # pragma: no cover
    main()
