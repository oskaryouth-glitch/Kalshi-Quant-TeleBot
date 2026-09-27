"""Two-phase forward collector (read-only, unauthenticated, public endpoints only).

Protocol (DESIGN.md §E.2; parameters frozen in config.py):
  cycle (target CYCLE_TARGET_S):
    0. GET /exchange/status; page GET /events?status=open&with_nested_markets=true
       (refresh /series list, registry terms hashes and fee changes on their own cadences)
    1. SCREEN with /events summary quotes. These decide only WHAT to fetch; they are never
       used as prices for evaluation.
         - numeric R1/R3 templates, locking pairs (relationships.screen_pairs), categorical
           MECNET top pairs
         - summary raw = max(nominal, L) - sum(summary asks) > 0 -> candidate
    2. PHASE 2 (per candidate, highest summary raw first, capped per cycle; skipped ones are
       counted): run the independent checker, then GET /markets/{t} for each leg (fresh status
       and last price), then its order books back-to-back, then evaluate.
    3. PHASE 3: if the phase-2 record is persistence-eligible, wait PERSISTENCE_REFETCH_DELAY_S,
       re-fetch metadata and books, and evaluate with persistence_confirmed=True.
    4. AUDIT: AUDIT_FAMILIES_PER_CYCLE random families are fetched from books regardless of the
       screen, to measure how many real inconsistencies the summary screen misses.
Streams (data/, git-ignored, gzip JSONL): candidates, rule511, books, statscreen, counts, ops,
universe, plus the fee ledger JSON.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import logging
import os
import random
import time
import uuid
from dataclasses import asdict
from decimal import Decimal

import requests

from . import config
from .fee_ledger import FeeLedger, FeeUnresolved
from . import relationships as R
from . import terms as TERMS
from . import universe as U
from .client import PublicClient
from .evaluator import BookObs, evaluate
from .orderbook import OrderBookFormatError, parse_orderbook
from .payoff import Position
from .research_log import _default

log = logging.getLogger("sarb.collector")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class Streams:
    def __init__(self, data_dir: str):
        self.dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def path(self, kind: str) -> str:
        return os.path.join(self.dir, f"sarb_{kind}_{dt.datetime.now(dt.timezone.utc):%Y%m%d}.jsonl.gz")

    def write(self, kind: str, obj) -> None:
        if not isinstance(obj, dict):
            obj = asdict(obj)
        with gzip.open(self.path(kind), "at", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, sort_keys=True, default=_default) + "\n")


def _now_iso() -> str:
    return U.iso_utc(time.time_ns())


class Collector:
    def __init__(self, client: PublicClient, data_dir: str = DATA_DIR, seed: int | None = None,
                 terms_fetch=None):
        self.c = client
        self.out = Streams(data_dir)
        self.cache = U.TemplateCache()
        self.ledger = FeeLedger(os.path.join(data_dir, "sarb_fee_ledger.jsonl"))
        self.series: dict[str, dict] = {}
        self.series_changes: list[dict] = []
        self.terms_sha: dict[str, str] = {}
        self._last = {"series": float("-inf"), "terms": float("-inf"), "fees": float("-inf")}
        self.rng = random.Random(seed)
        self.terms_fetch = terms_fetch or (lambda url: requests.get(url, timeout=30).content)
        self._stat_last: dict = {}

    def _statscreen(self, key, rec: dict, counts) -> None:
        """Summary-only statistical hits recur every cycle; counts are kept per cycle, but the
        detail record is re-written at most every STATSCREEN_REWRITE_S per key."""
        now = time.monotonic()
        last = self._stat_last.get(key)
        if last is None or now - last >= config.STATSCREEN_REWRITE_S:
            self._stat_last[key] = now
            self.out.write("statscreen", rec)
            counts["STATSCREEN|written"] += 1
        else:
            counts["STATSCREEN|deduplicated"] += 1

    # ------------------------------------------------------------------ refreshers
    def _refresh(self, now: float) -> dict:
        info = {}
        if now - self._last["series"] >= config.SERIES_REFRESH_S or not self.series:
            r = self.c.get_retry("/series", {"limit": 1000})
            if r.status == 200:
                self.series = {s["ticker"]: {"series": s} for s in r.body.get("series", [])}
                self._last["series"] = now
            info["series_refreshed"] = r.status
        if now - self._last["terms"] >= config.TERMS_REFRESH_S:
            for url in TERMS.REGISTRY:
                try:   # fixed allowlist of Kalshi contract-terms PDFs (public GET, no auth)
                    self.terms_sha[url] = hashlib.sha256(self.terms_fetch(url)).hexdigest()
                except Exception as e:
                    self.terms_sha.pop(url, None)
                    info.setdefault("terms_errors", []).append(f"{url}:{e!r}"[:200])
            self._last["terms"] = now
            info["terms_sha"] = dict(self.terms_sha)
        if now - self._last["fees"] >= config.FEE_CHANGES_REFRESH_S:
            r = self.c.get_retry("/series/fee_changes", {"show_historical": "true"})
            if r.status == 200:
                info["series_changes_new"] = self.ledger.add_series_changes(r.body.get("series_fee_change_arr", []))
            rows, cur = [], None
            for _ in range(100):
                p = {"limit": 1000, **({"cursor": cur} if cur else {})}
                rr = self.c.get_retry("/events/fee_changes", p)
                if rr.status != 200:
                    break
                rows += rr.body.get("event_fee_changes", [])
                cur = rr.body.get("cursor")
                if not cur:
                    break
            info["event_changes_new"] = self.ledger.add_event_changes(rows)
            self._last["fees"] = now
        return info

    def _events(self) -> tuple[list[dict], int]:
        evs, cur, pages = [], None, 0
        fetched_mono = time.monotonic_ns()
        for _ in range(1000):
            p = {"status": "open", "limit": 200, "with_nested_markets": "true", **({"cursor": cur} if cur else {})}
            r = self.c.get_retry("/events", p)
            pages += 1
            time.sleep(config.EVENTS_PAGE_MIN_INTERVAL_S)
            if r.status != 200:
                raise RuntimeError(f"events page status {r.status}")
            evs += r.body.get("events", [])
            # List-page events are NOT fed to the fee ledger: whether the list endpoint includes the
            # override fields is unverified, so only single-object GET /events/{e} observations count.
            cur = r.body.get("cursor")
            if not cur:
                break
        return evs, fetched_mono

    # ------------------------------------------------------------------ fetch helpers
    def _fetch_legs(self, u: U.Universe, tickers: list[str], phase: str, group: str):
        """Metadata first, then books back-to-back (minimises book skew)."""
        metas = {}
        for t in tickers:
            r = self.c.get(f"/markets/{t}")
            m = (r.body or {}).get("market") if r.status == 200 else None
            metas[t] = u.meta(t, r.recv_mono_ns, m if m else {"status": f"HTTP_{r.status}"})
            self.out.write("books", {"kind": "market", "phase": phase, "group": group, "ticker": t,
                                     "status": r.status, "sent_utc_ns": r.sent_utc_ns, "recv_utc_ns": r.recv_utc_ns,
                                     "headers": dict(r.headers), "body": r.body})
        books = {}
        for t in tickers:
            try:
                r = self.c.orderbook(t)
            except requests.RequestException as e:
                books[t] = BookObs(None, 0, 0, 0, 0, 0, None, repr(e))
                continue
            try:
                ob = parse_orderbook(t, r.body) if r.status == 200 else None
                err = None if ob else f"HTTP_{r.status}"
            except OrderBookFormatError as e:
                ob, err = None, f"FORMAT:{e}"
            books[t] = BookObs(ob, r.status, r.sent_mono_ns, r.recv_mono_ns, r.sent_utc_ns, r.recv_utc_ns,
                               dict(r.headers).get("x-cache"), err)
            self.out.write("books", {"kind": "orderbook", "phase": phase, "group": group, "ticker": t,
                                     "status": r.status, "sent_utc_ns": r.sent_utc_ns, "recv_utc_ns": r.recv_utc_ns,
                                     "sent_mono_ns": r.sent_mono_ns, "recv_mono_ns": r.recv_mono_ns,
                                     "headers": dict(r.headers), "body": r.body})
        return metas, books

    def _fees(self, u: U.Universe, tickers: list[str], phase: str, group: str) -> tuple[dict, int]:
        """Observe the event and series objects of every leg NOW (after the books), then resolve
        the fee in force at the snapshot time via the time-versioned ledger. Returns (fees, t)."""
        evs = sorted({u.raw[t][0]["event_ticker"] for t in tickers})
        sers = sorted({u.raw[t][0].get("series_ticker", "") for t in tickers})
        now_utc = time.time_ns()
        fresh = lambda layer, k: (lambda c: c is not None and now_utc - c[0] < config.OBSERVATION_REUSE_S * 1e9)(  # noqa: E731
            self.ledger.confirmed.get((layer, k)))
        evs = [e for e in evs if not fresh("event", e)]
        sers = [x for x in sers if not fresh("series", x)]
        for e in evs:
            r = self.c.get(f"/events/{e}")
            if r.status == 200 and isinstance(r.body, dict) and r.body.get("event"):
                self.ledger.observe_event(r.body["event"], r.recv_utc_ns)
            self.out.write("books", {"kind": "event", "phase": phase, "group": group, "ticker": e, "status": r.status,
                                     "recv_utc_ns": r.recv_utc_ns,
                                     "fee_fields": {k: (r.body.get("event") or {}).get(k) for k in
                                                    ("fee_type_override", "fee_multiplier_override")}
                                     if isinstance(r.body, dict) else None})
        for sr in sers:
            r = self.c.get(f"/series/{sr}")
            if r.status == 200 and isinstance(r.body, dict) and r.body.get("series"):
                self.ledger.observe_series(r.body, r.recv_utc_ns)
            self.out.write("books", {"kind": "series", "phase": phase, "group": group, "ticker": sr, "status": r.status,
                                     "recv_utc_ns": r.recv_utc_ns,
                                     "fee_fields": {k: (r.body.get("series") or {}).get(k) for k in ("fee_type", "fee_multiplier")}
                                     if isinstance(r.body, dict) else None})
        t = time.time_ns()
        out = {}
        for tk in tickers:
            ev, _ = u.raw[tk]
            try:
                out[tk] = self.ledger.resolve(ev.get("series_ticker", ""), ev["event_ticker"], t)
            except FeeUnresolved as e:
                out[tk] = e
        return out, t

    def _log_record(self, rec, phase: str, group: str, cycle: str, extra: dict) -> None:
        rec.extra.update({"phase": phase, "group": group, "cycle": cycle, "price_source": "orderbook", **extra})
        self.out.write("candidates", rec)
        if rec.extra.get("rule_5_11", {}).get("blocked_by_rule_5_11"):
            self.out.write("rule511", rec)

    # ------------------------------------------------------------------ phases
    def _phase2_3(self, u: U.Universe, st: R.Structural, summary_raw: Decimal, cycle: str, ops: dict, counts: dict):
        R.check(st)
        key = f"P2|{st.relationship}|"
        if st.relationship_class != "GUARANTEED" or any(n.startswith("BUG") for n in st.notes):
            counts[key + "CHECKER_NOT_LOCKED" if not st.notes else key + "CHECKER_BUG"] += 1
            if st.notes:
                self.out.write("statscreen", {"cycle": cycle, "relationship": st.relationship, "notes": st.notes,
                                              "positions": [(p.ticker, p.side) for p in st.positions]})
            return
        group = uuid.uuid4().hex
        legs = [p.ticker for p in st.positions]
        t0 = time.monotonic_ns()
        metas, books = self._fetch_legs(u, legs, "P2", group)
        fees, t_fee = self._fees(u, legs, "P2", group)
        out, rec = evaluate(st, books, metas, fees, self._exchange_active, time.monotonic_ns(), t_fee, None)
        ok_books = [b for b in books.values() if b.recv_mono_ns]
        if ok_books:
            ops["p2_leg_fetch_ms"].append((max(b.recv_mono_ns for b in ok_books) - t0) / 1e6)
            ops["p2_book_skew_ms"].append((max(b.recv_mono_ns for b in ok_books) - min(b.sent_mono_ns for b in ok_books)) / 1e6)
        counts[key + (rec.status if rec else out)] += 1
        if rec is None:
            return
        self._log_record(rec, "P2", group, cycle, {"summary_raw": str(summary_raw)})
        if not rec.extra.get("persistence_eligible"):
            return
        p2_last = max(b.recv_mono_ns for b in ok_books)
        wait = config.PERSISTENCE_REFETCH_DELAY_S - (time.monotonic_ns() - p2_last) / 1e9
        if wait > 0:
            time.sleep(wait)
        metas3, books3 = self._fetch_legs(u, legs, "P3", group)
        fees3, t_fee3 = self._fees(u, legs, "P3", group)
        out3, rec3 = evaluate(st, books3, metas3, fees3, self._exchange_active, time.monotonic_ns(), t_fee3, True)
        ok3 = [b for b in books3.values() if b.recv_mono_ns]
        if ok3:
            ops["p3_delay_ms"].append((min(b.sent_mono_ns for b in ok3) - p2_last) / 1e6)
        counts[f"P3|{st.relationship}|" + (rec3.status if rec3 else out3)] += 1
        if rec3 is not None:
            self._log_record(rec3, "P3", group, cycle, {"summary_raw": str(summary_raw)})

    def _audit(self, u: U.Universe, fetched_mono: int, cycle: str, counts: dict, screen: dict):
        fams = [f for f in u.families.values() if 2 <= len(f.specs) <= config.AUDIT_MAX_MARKETS_PER_FAMILY]
        for fam in self.rng.sample(fams, min(config.AUDIT_FAMILIES_PER_CYCLE, len(fams))):
            group = uuid.uuid4().hex
            tickers = sorted(fam.specs)
            books = {}
            for t in tickers:
                r = self.c.orderbook(t)
                try:
                    ob = parse_orderbook(t, r.body) if r.status == 200 else None
                except OrderBookFormatError:
                    ob = None
                books[t] = BookObs(ob, r.status, r.sent_mono_ns, r.recv_mono_ns, r.sent_utc_ns, r.recv_utc_ns,
                                   dict(r.headers).get("x-cache"))
                self.out.write("books", {"kind": "orderbook", "phase": "AUDIT", "group": group, "ticker": t,
                                         "status": r.status, "sent_utc_ns": r.sent_utc_ns, "recv_utc_ns": r.recv_utc_ns,
                                         "headers": dict(r.headers), "body": r.body})
            metas = {t: u.meta(t, fetched_mono) for t in tickers}
            fees, t_fee = self._fees(u, tickers, "AUDIT", group)
            for st in R.numeric_family_templates(fam):          # eager: all templates incl. pairs
                out, rec = evaluate(st, books, metas, fees, self._exchange_active, time.monotonic_ns(), t_fee, None)
                sk = screen.get((st.relationship, st.positions))
                counts[f"AUDIT|{st.relationship}|{rec.status if rec else out}"] += 1
                if out == "LOGGED":
                    counts[f"AUDIT_SCREEN|{'summary_flagged' if sk else 'summary_missed'}"] += 1
                    self._log_record(rec, "AUDIT", group, cycle, {"summary_flagged": bool(sk)})

    # ------------------------------------------------------------------ cycle
    def run_cycle(self) -> dict:
        cycle = uuid.uuid4().hex
        t0 = time.monotonic()
        from collections import Counter
        counts: Counter = Counter()
        ops = {"p2_leg_fetch_ms": [], "p2_book_skew_ms": [], "p3_delay_ms": []}
        st_r = self.c.get_retry("/exchange/status")
        self._exchange_active = bool((st_r.body or {}).get("trading_active")) if st_r.status == 200 else False
        refresh = self._refresh(time.monotonic())
        evs, fetched_mono = self._events()
        t_ev = time.monotonic()
        u = U.build_universe(evs, self.series, self.terms_sha, self.cache)
        self.out.write("universe", {"cycle": cycle, "utc": _now_iso(), "events": len(evs), "markets": len(u.raw),
                                    "families": len(u.families), "templates_r1_r3": len(u.structs),
                                    "categorical_events": len(u.categorical), "reject_counts": u.reject_counts,
                                    "build_s": round(u.build_seconds, 2), "refresh": refresh,
                                    "fee_ledger_changes": sum(len(v) for v in self.ledger.changes.values()),
                                    "terms_verified_markets": sum(1 for s in u.specs.values() if s.terms_status == "TERMS_VERIFIED")})
        # ---- SCREEN
        queue, screen = [], {}
        for st in u.structs:
            asks = [u.summary_ask(p) for p in st.positions]
            if any(a is None for a in asks):
                counts[f"SCREEN|{st.relationship}|NO_ASK"] += 1
                continue
            raw = Decimal(max(st.nominal_locked, st.locked).numerator) / Decimal(max(st.nominal_locked, st.locked).denominator) - sum(asks)
            if raw <= 0:
                counts[f"SCREEN|{st.relationship}|CONSISTENT"] += 1
                continue
            counts[f"SCREEN|{st.relationship}|FLAGGED_{st.relationship_class}"] += 1
            screen[(st.relationship, st.positions)] = raw
            if st.relationship_class == "GUARANTEED":
                queue.append((raw, st))
            else:
                R.check(st)
                self._statscreen((st.relationship, st.positions), {"cycle": cycle, "utc": _now_iso(), "relationship": st.relationship,
                                              "price_source": "events_summary_screen_only", "summary_raw_nominal": str(raw),
                                              "locked": str(st.locked), "argmin_state": st.argmin_state,
                                              "positions": [(p.ticker, p.side, str(a)) for p, a in zip(st.positions, asks)],
                                              "family_key": st.family_key, "terms_verified": st.terms_verified}, counts)
        for fam in u.families.values():
            for st in R.screen_pairs(fam, lambda t, side: u.summary_ask(Position(t, side))):
                raw = 1 - sum(u.summary_ask(p) for p in st.positions)
                counts[f"SCREEN|{st.relationship}|FLAGGED_GUARANTEED"] += 1
                screen[(st.relationship, st.positions)] = raw
                queue.append((raw, st))
        for ev, ts in u.categorical.items():
            no_asks = sorted((a, t) for t in ts for a in [u.summary_ask(Position(t, "no"))] if a is not None)[:3]
            for i in range(len(no_asks)):
                for j in range(i + 1, len(no_asks)):
                    raw = 1 - no_asks[i][0] - no_asks[j][0]
                    if raw > 0:
                        st = U.categorical_pair(ev, no_asks[i][1], no_asks[j][1])
                        counts["SCREEN|R1_EXCLUSIVE_PAIR_MECNET|FLAGGED_GUARANTEED"] += 1
                        queue.append((raw, st))
            yes = [u.summary_ask(Position(t, "yes")) for t in ts]
            if all(a is not None for a in yes) and sum(yes) < 1:
                counts["SCREEN|R1_LONG_MECNET|FLAGGED_STATISTICAL"] += 1
                self._statscreen(("R1_LONG_MECNET", ev), {"cycle": cycle, "utc": _now_iso(), "relationship": "R1_LONG_MECNET",
                                              "price_source": "events_summary_screen_only",
                                              "summary_raw_nominal": str(1 - sum(yes)), "locked": "0",
                                              "argmin_state": "NONE(no listed winner)", "event": ev}, counts)
        counts["SCREEN|categorical_events"] = len(u.categorical)
        t_screen = time.monotonic()
        # ---- PHASE 2/3 (budget order: largest summary raw first)
        queue.sort(key=lambda x: x[0], reverse=True)
        for raw, st in queue[:config.MAX_PHASE2_CANDIDATES_PER_CYCLE]:
            self._phase2_3(u, st, raw, cycle, ops, counts)
        counts["PHASE2|skipped_budget"] = max(0, len(queue) - config.MAX_PHASE2_CANDIDATES_PER_CYCLE)
        t_p2 = time.monotonic()
        # ---- AUDIT
        self._audit(u, fetched_mono, cycle, counts, screen)
        t_end = time.monotonic()
        req = self.c.stats.snapshot_and_reset()
        n_req = sum(req["requests"].values())
        ops_rec = {"cycle": cycle, "utc": _now_iso(), "cycle_s": round(t_end - t0, 2),
                   "events_s": round(t_ev - t0, 2), "screen_s": round(t_screen - t_ev, 2),
                   "phase23_s": round(t_p2 - t_screen, 2), "audit_s": round(t_end - t_p2, 2),
                   "requests_total": n_req, "req_per_s": round(n_req / max(1e-9, t_end - t0), 2),
                   "http_429": sum(v for k, v in req["requests"].items() if k.endswith("|429")),
                   "rate_limit_cooldowns_total": self.c._limiter.cooldowns,
                   "http_non200": {k: v for k, v in req["requests"].items() if not k.endswith("|200")},
                   **req, **{k: v for k, v in ops.items()}}
        self.out.write("ops", ops_rec)
        self.out.write("counts", {"cycle": cycle, "utc": _now_iso(), "counts": dict(counts)})
        return {"cycle": cycle, "counts": dict(counts), "ops": ops_rec}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Read-only two-phase structural scanner (no auth, no orders).")
    ap.add_argument("--duration-s", type=float, default=600)
    ap.add_argument("--data-dir", default=DATA_DIR)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    c = Collector(PublicClient(), a.data_dir, a.seed)
    end = time.monotonic() + a.duration_s
    while time.monotonic() < end:
        t = time.monotonic()
        try:
            r = c.run_cycle()
            o = r["ops"]
            log.info("cycle %s: %.1fs req=%d (%.2f/s) 429=%d p2=%d", r["cycle"][:8], o["cycle_s"], o["requests_total"],
                     o["req_per_s"], o["http_429"], len(o["p2_leg_fetch_ms"]))
        except Exception as e:     # recorded, never silently swallowed
            log.exception("cycle failed")
            Streams(a.data_dir).write("ops", {"utc": _now_iso(), "cycle_error": repr(e)[:500]})
        rest = config.CYCLE_TARGET_S - (time.monotonic() - t)
        if rest > 0 and time.monotonic() + rest < end:
            time.sleep(rest)


if __name__ == "__main__":
    main()
