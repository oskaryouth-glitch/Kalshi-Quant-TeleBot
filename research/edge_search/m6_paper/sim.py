"""M6 paper experiment: deterministic, causal, offline replay of the recorded streams (DESIGN §4-§10 v2).

All three fill variants (V_T, V_P, V_C) are replayed in lockstep over the same event sequence, because
the stopping rule (§10) is applied jointly: an arm reaches its formal checkpoint at the first daily
checkpoint (day >= 35) at which ALL THREE variants have >= 20 completed episodes; it then stops entering.

Event order: recorded records by time; ties broken feestate < markets < tracked < trades < books < epoch.
Trades are ordered by exchange `created_time`, everything else by receive time `t_ns`. A quoting decision
at a book poll uses only that poll and earlier data; orders go live LATENCY after the poll.

Money is Decimal throughout. Nothing here places orders or touches the network.
"""
from __future__ import annotations

import datetime as dt
import heapq
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal as D

from . import accounting as A
from . import fills as F
from . import lip
from . import selection as SEL
from . import spec as S
from . import storage as ST

NS = 1_000_000_000
DAY = 86400 * NS
PRIO = {"feestate": 0, "markets": 1, "tracked": 2, "trade": 3, "books": 4, "epoch": 5}
MARKOUT_H = (10, 60, 300, 1800, 7200)
TRACK_GRACE_NS = 600 * NS        # the tracked record follows its epoch record by the epoch's collection time


def covered(interval_ns: int) -> int:
    """Reward coverage of one inter-poll interval: counted in full if <= GAP_S, otherwise NOT AT ALL. A longer
    silence (e.g. the ~2-minute selection pause) is a gap and is never compensated (reviewer, 2026-09-29)."""
    return max(0, interval_ns) if interval_ns <= S.GAP_S * NS else 0


def day0_of(start_ns: int) -> int:
    """Day 0 = the first 00:00 UTC after collection starts."""
    return (start_ns // DAY + 1) * DAY


# ============================================================================ shared market data
class World:
    """Market data shared by every variant: books, market state, fee state, tracking, trades between polls."""

    def __init__(self):
        self.book: dict[str, dict] = {}
        self.book_ver: dict[str, int] = defaultdict(int)
        self.levels_prev: dict[str, dict] = {}
        self.last_poll: dict[str, int] = {}
        self.traded_since_poll: dict[str, dict] = defaultdict(lambda: defaultdict(D))
        self.market: dict[str, dict] = {}
        self.settled_at: dict[str, tuple[int, D]] = {}     # ticker -> (first observed ns, YES settlement value)
        self.inactive_at: dict[str, int] = {}              # ticker -> latest non-active observation (receive ns)
        self.status_obs: dict[str, list] = defaultdict(list)   # ticker -> [(receive ns, status)] for status != active
        self.tracked_since: dict[str, int] = {}
        self.fee_series_hist: dict[str, list] = defaultdict(list)   # series -> [(observed ns, raw fee fields)]
        self.fee_event_hist: dict[str, list] = defaultdict(list)    # event  -> [(observed ns, raw fields)]
        self.fee_changes_hist: list = []                            # [(observed ns, fee-change list)]
        self.breaches: list = []
        self.trade_gaps: list = []

    @staticmethod
    def side_levels(book: dict) -> dict:
        return {"yes": {p: q for p, q in lip.levels(book, "yes")}, "no": {p: q for p, q in lip.levels(book, "no")}}

    def on_markets(self, t: int, rec: dict) -> None:
        for k, m in rec["markets"].items():
            self.market[k] = m
            if m.get("status") != "active":
                self.inactive_at[k] = t
                self.status_obs[k].append((t, m.get("status")))
            if m.get("status") in ("settled", "finalized") and k not in self.settled_at:
                v = m.get("settlement_value_dollars")
                if v is None:
                    v = {"yes": "1", "no": "0"}.get(m.get("result"))
                if v is not None:
                    self.settled_at[k] = (t, D(str(v)))

    def on_feestate(self, t: int, rec: dict) -> None:
        for s, v in rec.get("series", {}).items():
            self.fee_series_hist[s].append((v.get("t_ns", t), v))
        for e, v in rec.get("events", {}).items():
            self.fee_event_hist[e].append((v.get("t_ns", t), v))
        if "fee_changes" in rec:
            self.fee_changes_hist.append((rec.get("fee_changes_t_ns", t), rec["fee_changes"]))

    @staticmethod
    def _latest(hist: list, t: int):
        best = None
        for obs, v in hist:
            if obs <= t:
                best = (obs, v)
        return best

    def fee_state(self, ticker: str, t: int, cutoff: int | None = None) -> tuple[str, D, dict]:
        """Fee state for a fill in `ticker` at time t, with provenance.

        cutoff=None -> KNOWN: only observations made at or before t (what a participant knew at the fill).
        cutoff=X    -> APPLICABLE: the fee in force at t as reconstructable from everything observed by X:
                       the series state observed at/before t (else the first observation by X), adjusted by the
                       fee-change history known at X for changes scheduled up to t; the event override observed
                       at/before t (else the first observation by X). If a change is scheduled between t and a
                       later-only series observation, the state at t is undetermined -> conservative default.
        Unknown -> maker fees at M = 1 (conservative). Selection never calls this (it uses its epoch's series state)."""
        horizon = t if cutoff is None else cutoff
        prov = {"basis": "known" if cutoff is None else "applicable", "t_ns": t}
        m = self.market.get(ticker) or {}
        ev_hist = self.fee_event_hist.get(m.get("event_ticker"), [])
        ev = self._latest(ev_hist, t) or (next(((o, v) for o, v in ev_hist if o <= horizon), None) if cutoff else None)
        s = ev[1].get("series_ticker") if ev else None
        s_hist = self.fee_series_hist.get(s, []) if s else []
        st = self._latest(s_hist, t) or (next(((o, v) for o, v in s_hist if o <= horizon), None) if cutoff else None)
        if not st:
            return (*S.UNKNOWN_FEE_STATE, {**prov, "status": "unknown_series_state"})
        ftype, mult = st[1].get("fee_type"), st[1].get("fee_multiplier")
        prov.update(series=s, series_obs_ns=st[0], event_obs_ns=ev[0] if ev else None)
        ch = self._latest(self.fee_changes_hist, horizon)
        applied = []
        if ch:
            prov["fee_changes_obs_ns"] = ch[0]
            for c in sorted((c for c in ch[1] if c.get("series_ticker") == s), key=lambda c: c.get("scheduled_ts", "")):
                sched = SEL.ts_ns(c["scheduled_ts"])
                if st[0] < sched <= t:
                    ftype, mult = c.get("fee_type", ftype), c.get("fee_multiplier", mult)
                    applied.append(c["scheduled_ts"])
                elif t < sched <= st[0]:           # series observed only after a change that postdates t
                    return (*S.UNKNOWN_FEE_STATE, {**prov, "status": "undetermined_change_between_fill_and_observation"})
        prov["changes_applied"] = applied
        if ev and ev[1].get("fee_type_override"):
            ftype = ev[1]["fee_type_override"]
            mult = ev[1].get("fee_multiplier_override") if ev[1].get("fee_multiplier_override") is not None else mult
            prov["event_override"] = True
        if not ftype:
            return (*S.UNKNOWN_FEE_STATE, {**prov, "status": "no_fee_type"})
        return ftype, D(str(mult if mult is not None else 1)), {**prov, "status": "ok", "fee_type": ftype, "fee_multiplier": str(mult)}

    def first_non_active(self, ticker: str, since_ns: int, t: int) -> tuple[int, str] | None:
        """The first observation of status != active received in [since_ns, t], or None (A7, reviewer-approved:
        permanent termination at the first observation during the episode; never backdated)."""
        for obs, st in self.status_obs.get(ticker, ()):
            if since_ns <= obs <= t:
                return obs, st
        return None

    def close_ns(self, ticker: str) -> int | None:
        m = self.market.get(ticker) or {}
        return SEL.ts_ns(m["close_time"]) if m.get("close_time") else None

    def best(self, ticker: str) -> tuple[D | None, D | None]:
        b = self.book.get(ticker) or {}
        y, n = lip.levels(b, "yes"), lip.levels(b, "no")
        return (y[0][0] if y else None), (n[0][0] if n else None)


# ============================================================================ per-variant state
@dataclass
class Episode:
    eid: str
    arm: str
    account: str
    variant: str
    cand: SEL.Candidate
    entry_ns: int
    end_ns: int                  # program end (quoting may stop earlier)
    ended_ns: int | None = None
    end_reason: str = ""
    samples: list = field(default_factory=list)        # (t_ns, snapshot score)
    cover_ns: int = 0
    last_poll_ns: int | None = None
    fills: list = field(default_factory=list)
    repricings: int = 0
    tracked_ok: bool = True
    end_status: str | None = None          # observed status that terminated the episode (A7)
    end_observed_ns: int | None = None     # receive time of that observation


@dataclass
class Account:
    name: str
    arm: str
    K: D | None
    positions: dict = field(default_factory=dict)      # ticker -> Position
    active: dict = field(default_factory=dict)         # ticker -> Episode
    orders: dict = field(default_factory=lambda: defaultdict(list))   # ticker -> [Order]
    cap_integral: D = D(0)                             # $ * ns
    cap_max: D = D(0)
    cap_last_ns: int | None = None

    def pos(self, ticker: str) -> A.Position:
        return self.positions.setdefault(ticker, A.Position())

    def committed(self) -> D:
        resting = sum((o.size * o.price for os in self.orders.values() for o in os if o.size > 0), D(0))
        inv = sum((p.inventory_cost for p in self.positions.values()), D(0))
        return resting + inv + sum((e.cand.reserve for e in self.active.values()), D(0))

    def tick_capital(self, t: int) -> None:
        c = self.committed()
        if self.cap_last_ns is not None and t > self.cap_last_ns:
            self.cap_integral += c * (t - self.cap_last_ns)
        self.cap_last_ns = t
        self.cap_max = max(self.cap_max, c)


class VariantState:
    def __init__(self, variant: str, world: World):
        self.v, self.w = variant, world
        self.accounts: dict[str, Account] = {k: Account(k, k, K) for k, K in S.ACCOUNTS.items()}
        self.episodes: list[Episode] = []
        self.oid = 0
        self.by_ticker: dict[str, set[str]] = defaultdict(set)     # ticker -> accounts that ever quoted it
        self.ends: list = []                                        # heap (time, seq, account, ticker, eid)
        self.seq = 0

    # ------------------------------------------------------------------ entries
    def enter(self, acct: Account, c: SEL.Candidate, t: int) -> Episode:
        e = Episode(f"{self.v}:{acct.name}:{c.program_id}:{t}", acct.arm, acct.name, self.v, c, t, c.end_ns)
        acct.active[c.ticker] = e
        self.by_ticker[c.ticker].add(acct.name)
        close = (self.w.market.get(c.ticker) or {}).get("close_time")
        self.seq += 1
        heapq.heappush(self.ends, (min(c.end_ns, SEL.ts_ns(close)) if close else c.end_ns, self.seq, acct.name, c.ticker, e.eid))
        self.episodes.append(e)
        return e

    def new_u_account(self, c: SEL.Candidate, t: int) -> Account:
        name = f"U:{c.program_id}:{t}"
        a = Account(name, "U", None)
        self.accounts[name] = a
        return a

    # ------------------------------------------------------------------ episode end
    def expire(self, t: int, full: bool = False) -> None:
        """End episodes whose program end or market close has passed (heap), or, with full=True (after a
        market-state update), whose market became inactive."""
        todo = set()
        while self.ends and self.ends[0][0] <= t:
            _, _, a, ticker, _ = heapq.heappop(self.ends)
            todo.add(a)
        if full:
            todo |= {a for tk in self.w.inactive_at for a in self.by_ticker.get(tk, ())}
        for name in todo:
            acct = self.accounts[name]
            for ticker, e in list(acct.active.items()):
                cands = []
                if e.end_ns <= t:
                    cands.append((e.end_ns, "program_end", None, None))
                close = self.w.close_ns(ticker)
                if close is not None and close <= t:
                    cands.append((max(e.entry_ns, close), "market_close_time", None, None))
                obs = self.w.first_non_active(ticker, e.entry_ns, t)
                if obs is not None:
                    cands.append((obs[0], "market_status_non_active", obs[1], obs[0]))
                if not cands:
                    continue
                end, why, e.end_status, e.end_observed_ns = min(cands, key=lambda c: c[0])
                if e.last_poll_ns is not None:
                    e.cover_ns += covered(end - e.last_poll_ns)
                e.ended_ns, e.end_reason = end, why
                acct.tick_capital(end)
                acct.orders[ticker] = []
                del acct.active[ticker]
                acct.tick_capital(end)

    # ------------------------------------------------------------------ trades
    def on_trade(self, t: int, trade: dict) -> None:
        ticker = trade["ticker"]
        for name in self.by_ticker.get(ticker, ()):
            acct = self.accounts[name]
            os = acct.orders.get(ticker)
            if not os:
                continue
            res = F.match_trade(os, trade, t)
            if not res:
                continue
            acct.tick_capital(t)
            ftype, mult, prov = self.w.fee_state(ticker, t)              # causally KNOWN at the fill
            for o, n, kind in res:
                f = A.Fill(t, o.side, o.price, n, A.maker_fee(ftype, mult, o.price, n, S.DIRECT_G),
                           A.maker_fee(ftype, mult, o.price, n, S.NONDIRECT_G), o.episode, kind)
                f.markouts = {}
                f.fee_known_direct, f.fee_known_prov = f.fee_direct, prov
                acct.pos(ticker).apply(f)
                e = acct.active.get(ticker)
                if e is not None and e.eid == o.episode:
                    e.fills.append(f)
            acct.orders[ticker] = [o for o in os if o.size > 0]
            acct.tick_capital(t)

    # ------------------------------------------------------------------ book polls
    def on_poll(self, t: int, ticker: str, traded_at: dict, levels_prev: dict | None) -> None:
        book = self.w.book.get(ticker)
        if book is None:
            return
        levels_now = World.side_levels(book)
        for name in sorted(self.by_ticker.get(ticker, ())):
            acct = self.accounts[name]
            os = acct.orders.get(ticker)
            if os and levels_prev is not None:
                F.queue_update(os, levels_prev, levels_now, traded_at, self.v)
            for f in acct.pos(ticker).fills if ticker in acct.positions else []:
                self._markouts(f, t, ticker)
            e = acct.active.get(ticker)
            if e is None:
                continue
            c = e.cand
            live = [o for o in acct.orders.get(ticker, []) if o.t_eff_ns <= t and o.size > 0]
            score = lip.snapshot_score(book, [(o.price, o.size) for o in live if o.side == "yes"],
                                       [(o.price, o.size) for o in live if o.side == "no"], c.target, c.discount, c.price_ranges)
            prev = e.last_poll_ns if e.last_poll_ns is not None else e.entry_ns
            e.cover_ns += covered(t - prev)
            e.last_poll_ns = t
            e.samples.append((t, score))
            self._quote(acct, e, book, levels_now, t)

    def _markouts(self, f, t: int, ticker: str) -> None:
        if len(f.markouts) == len(MARKOUT_H):
            return
        yb, nb = self.w.best(ticker)
        if yb is None or nb is None:
            return
        mid = (yb + (1 - nb)) / 2
        for h in MARKOUT_H:
            if h not in f.markouts and t >= f.t_ns + h * NS:
                f.markouts[h] = (mid - f.price) if f.side == "yes" else ((1 - mid) - f.price)

    def _quote(self, acct: Account, e: Episode, book: dict, levels_now: dict, t: int) -> None:
        c = e.cand
        ticker = c.ticker
        py, pn = lip.configure(book, c.price_ranges)[:2]
        q = acct.pos(ticker).q
        x = D(c.x)
        desired = {"yes": max(D(0), min(x, x - q)), "no": max(D(0), min(x, x + q))}
        target = {"yes": py, "no": pn}
        order_sides = ("no", "yes") if q > 0 else ("yes", "no")         # the side reducing |q| first
        os = acct.orders[ticker]
        for side in order_sides:
            mine = [o for o in os if o.side == side and o.size > 0]
            if any(o.price != target[side] for o in mine):
                e.repricings += 1
                for o in mine:
                    o.size = D(0)
                mine = []
            cur = sum((o.size for o in mine), D(0))
            if cur > desired[side]:                                       # cancel excess newest-first
                excess = cur - desired[side]
                for o in sorted(mine, key=lambda o: (o.placed_ns, o.oid), reverse=True):
                    cut = min(o.size, excess)
                    o.size -= cut
                    excess -= cut
                    if excess <= 0:
                        break
            elif cur < desired[side]:
                n = (desired[side] - cur).to_integral_value(rounding=ROUND_FLOOR)
                if acct.K is not None:
                    avail = acct.K - acct.committed()
                    n = min(n, (avail / target[side]).to_integral_value(rounding=ROUND_FLOOR) if avail > 0 else D(0))
                if n >= 1:
                    self.oid += 1
                    os.append(F.Order(self.oid, side, target[side], n, levels_now.get(side, {}).get(target[side], D(0)),
                                      t, t + S.LATENCY_NS, e.eid))
        acct.orders[ticker] = [o for o in os if o.size > 0]
        acct.tick_capital(t)


# ============================================================================ the replay
class Replay:
    def __init__(self, root: str):
        self.root = root
        metas = list(ST.read(root, "meta"))
        if any(r.get("kind") == "validation" for r in metas):
            raise RuntimeError("validation data can never enter the prospective experiment")
        meta = next(r for r in metas if r.get("kind") == "start")
        self.start_ns = meta["t_ns"]
        self.day0 = day0_of(self.start_ns)
        self.world = World()
        self.states = {v: VariantState(v, self.world) for v in S.VARIANTS}
        self.arm_status = {a: {"decided_ns": None, "verdict_state": "RUNNING", "decision_sets": {}}
                           for a in (*S.ACCOUNTS, "U")}
        self.next_checkpoint_day = S.CHECKPOINT_DAY
        self.last_t = self.start_ns

    # ------------------------------------------------------------------ events
    def events(self):
        """Merged, ordered event stream. Trades are sorted by created_time within a 1-day receive lookahead."""
        streams = [self._stream(name) for name in ("feestate", "markets", "tracked", "books", "epoch")]
        streams.append(self._trade_events())
        yield from heapq.merge(*streams, key=lambda x: (x[0], x[1], x[2]))

    def _stream(self, name: str):
        for i, r in enumerate(ST.read(self.root, name)):
            yield (r["t_ns"], PRIO[name], i, name, r)

    def _trade_events(self):
        days = ST.days(self.root, "trades")
        seen = set()
        for i, d in enumerate(days):
            rows = []
            for dd in days[i:i + 2]:                       # created on day d; received on d or d+1 (backfill <= 20 min old)
                for rec in ST.read_day(self.root, "trades", dd):
                    for tr in rec["trades"]:
                        c = SEL.ts_ns(tr["created_time"])
                        if ST.day_of(c) == d and tr["trade_id"] not in seen:
                            seen.add(tr["trade_id"])
                            rows.append((c, tr))
            rows.sort(key=lambda x: (x[0], x[1]["trade_id"]))
            for j, (c, tr) in enumerate(rows):
                yield (c, PRIO["trade"], j, "trade", tr)

    def entries_open(self, arm: str, t: int) -> bool:
        d = self.arm_status[arm]["decided_ns"]
        return (d is None or t < d) and t < self.day0 + S.MAX_DAY * DAY

    def run(self, until_ns: int | None = None) -> "Replay":
        for t, _, _, kind, rec in self.events():
            if until_ns is not None and t > until_ns:
                break
            self._checkpoints(t)
            for st in self.states.values():
                st.expire(t)
            getattr(self, "_on_" + kind)(t, rec)
            self.last_t = max(self.last_t, t)
        self._checkpoints(until_ns if until_ns is not None else self.last_t)
        return self

    def _on_feestate(self, t, rec):
        self.world.on_feestate(t, rec)

    def _on_markets(self, t, rec):
        self.world.on_markets(t, rec)
        for st in self.states.values():
            st.expire(t, full=True)

    def _on_tracked(self, t, rec):
        for a in rec.get("add", []):
            self.world.tracked_since.setdefault(a["ticker"], t)

    def _on_trade(self, t, tr):
        side, price, count = F.consumed_side(tr)
        self.world.traded_since_poll[tr["ticker"]][(side, price)] += count
        for st in self.states.values():
            st.on_trade(t, tr)

    def _on_books(self, t, rec):
        w = self.world
        for k, b in rec.get("books", {}).items():
            w.book[k] = b
            w.book_ver[k] += 1
        for k in list(rec.get("books", {})) + list(rec.get("same", [])):
            prev = w.levels_prev.get(k)
            traded = dict(w.traded_since_poll.pop(k, {}))
            for st in self.states.values():
                st.on_poll(t, k, traded, prev)
            if k in w.book:
                w.levels_prev[k] = World.side_levels(w.book[k])
            w.last_poll[k] = t

    def _on_epoch(self, t, rec):
        cands = SEL.candidates(rec)
        ranking = SEL.ranked(cands)
        is_u = dt.datetime.fromtimestamp(rec["epoch_ns"] / NS, dt.timezone.utc).hour == S.U_EPOCH_HOUR_UTC
        draws = SEL.u_draw(cands, rec["epoch_ns"], SEL.epoch_day(rec["epoch_ns"])) if is_u else []
        for st in self.states.values():
            for name, K in S.ACCOUNTS.items():
                if not self.entries_open(name, t):
                    continue
                acct = st.accounts[name]
                for c in SEL.admit(ranking, set(acct.active), acct.committed(), K):
                    st.enter(acct, c, t)
                    acct.tick_capital(t)
            if self.entries_open("U", t):
                for c in draws:
                    st.enter(st.new_u_account(c, t), c, t)

    # ------------------------------------------------------------------ stopping rule (§10 v2)
    def _checkpoints(self, t: int) -> None:
        while self.next_checkpoint_day <= S.MAX_DAY and t >= self.day0 + self.next_checkpoint_day * DAY:
            cp = self.day0 + self.next_checkpoint_day * DAY
            for st in self.states.values():
                st.expire(cp, full=True)
            for arm, s in self.arm_status.items():
                if s["decided_ns"] is not None:
                    continue
                sets = {v: [e for e in self.states[v].episodes if e.arm == arm and e.ended_ns is not None and e.ended_ns <= cp]
                        for v in S.VARIANTS}
                if all(len(x) >= S.MIN_EPISODES for x in sets.values()):
                    s.update(decided_ns=cp, verdict_state="DECIDED", decision_day=self.next_checkpoint_day,
                             decision_sets={v: [e.eid for e in x] for v, x in sets.items()})
                elif self.next_checkpoint_day == S.MAX_DAY:
                    s.update(decided_ns=cp, verdict_state="INSUFFICIENT_EVIDENCE", decision_day=S.MAX_DAY,
                             counts={v: len(x) for v, x in sets.items()})
            self.next_checkpoint_day += 1

    def breaches(self) -> dict:
        """Tracking breaches per variant (A9): entered markets whose tracking record did not arrive within
        TRACK_GRACE_NS of entry. Reported prominently; never excluded or repaired."""
        out = {}
        for v, st in self.states.items():
            out[v] = [e.eid for e in st.episodes
                      if self.world.tracked_since.get(e.cand.ticker, 1 << 62) > e.entry_ns + TRACK_GRACE_NS]
        return out

    def counts(self) -> dict:
        """Completed-episode counts per arm and variant (the only in-flight output; no profitability)."""
        out = {}
        for arm in self.arm_status:
            out[arm] = {v: sum(1 for e in self.states[v].episodes if e.arm == arm and e.ended_ns is not None)
                        for v in S.VARIANTS}
        return out


# ============================================================================ valuation (used by analysis only)
def batch_of(t_ns: int) -> int:
    """Fixed UTC batch index (A5, reviewer): 6-hour blocks [00:00,06:00) [06:00,12:00) [12:00,18:00) [18:00,24:00).
    The Unix epoch is 00:00 UTC, so floor division by 6 h aligns exactly to these boundaries."""
    return t_ns // (S.BATCH_S * NS)


def batch_means_input(samples, halves) -> dict:
    """Observations grouped by fixed 6-hour UTC block; every observation of one block is ONE batch, however many
    clock hours it spans. A batch counts if it holds at least one observation (existing rule, preserved)."""
    batches = defaultdict(list)
    for (t, _), h in zip(samples, halves):
        batches[batch_of(t)].append(h)
    return batches


def payout(e: Episode) -> dict:
    c = e.cand
    period = D(max(1, c.end_ns - c.start_ns))
    frac = D(e.cover_ns) / period
    if not e.samples:
        return {"p_hat": D(0), "se": None, "primary": D(0), "conservative": D(0)}
    halves = [s / 2 for _, s in e.samples]
    mean = sum(halves, D(0)) / len(halves)
    p_hat = c.reward * frac * mean
    batches = batch_means_input(e.samples, halves)
    bm = [sum(b, D(0)) / len(b) for b in batches.values()]
    se = (D(statistics.stdev([float(x) for x in bm])) / D(math.sqrt(len(bm)))) * c.reward * frac if len(bm) >= 2 else None
    cent = lambda x: (x * 100).to_integral_value(rounding=ROUND_FLOOR) / 100              # noqa: E731
    primary = cent(p_hat) if p_hat >= S.PAYOUT_FLOOR else D(0)
    conservative = cent(p_hat) if se is not None and p_hat - S.Z_CONSERVATIVE * se >= S.PAYOUT_FLOOR else D(0)
    return {"p_hat": p_hat, "se": se, "primary": primary, "conservative": conservative}


def episode_ledger(rp: Replay, cutoff_ns: int) -> list[dict]:
    """Per-episode NET for every variant, with settlement known by `cutoff_ns` (else liquidation marks)."""
    rows = []
    w = rp.world
    for v, st in rp.states.items():
        for acct in st.accounts.values():
            for ticker, pos in acct.positions.items():
                s = w.settled_at.get(ticker)
                settled = s[1] if s and s[0] <= cutoff_ns else None
                yb, nb = w.best(ticker)
                _, mult, _ = w.fee_state(ticker, cutoff_ns, cutoff_ns)        # taker fee for liquidation marks
                vy, vn, how = A.contract_values(settled, yb, nb, pos.q, mult)
                for f in pos.fills:
                    # P&L uses the fee ultimately APPLICABLE at the fill (reconstructed by the cutoff); the
                    # causally known fee is kept for provenance and reported as a sensitivity
                    ftype, fm, prov = w.fee_state(ticker, f.t_ns, cutoff_ns)
                    f.fee_direct = A.maker_fee(ftype, fm, f.price, f.count, S.DIRECT_G)
                    f.fee_nondirect = A.maker_fee(ftype, fm, f.price, f.count, S.NONDIRECT_G)
                    f.fee_applicable_prov = prov
                    f.value_basis, f.pnl_direct, f.pnl_nondirect = how, A.fill_pnl(f, vy, vn, True), A.fill_pnl(f, vy, vn, False)
                    f.pnl_known_fee = (vy if f.side == "yes" else vn) * f.count - f.price * f.count - f.fee_known_direct
        for e in st.episodes:
            p = payout(e)
            trading = sum((f.pnl_direct for f in e.fills), D(0))
            rows.append({"variant": v, "eid": e.eid, "arm": e.arm, "account": e.account, "program_id": e.cand.program_id,
                         "ticker": e.cand.ticker, "event_ticker": e.cand.event_ticker, "entry_ns": e.entry_ns,
                         "ended_ns": e.ended_ns, "end_reason": e.end_reason, "end_status": e.end_status,
                         "end_observed_ns": e.end_observed_ns, "x": e.cand.x, "cstar": e.cand.cstar,
                         "reward_primary": p["primary"], "reward_conservative": p["conservative"], "p_hat": p["p_hat"],
                         "p_se": p["se"], "trading_pnl": trading,
                         "trading_pnl_nondirect": sum((f.pnl_nondirect for f in e.fills), D(0)),
                         "fees": sum((f.fee_direct for f in e.fills), D(0)),
                         "fees_known_at_fill": sum((f.fee_known_direct for f in e.fills), D(0)),
                         "trading_pnl_known_fee": sum((f.pnl_known_fee for f in e.fills), D(0)),
                         "fee_status_applicable": sorted({f.fee_applicable_prov.get("status") for f in e.fills}),
                         "selection_fee": e.cand.fee_provenance, "n_fills": len(e.fills),
                         "contracts": sum((f.count for f in e.fills), D(0)), "n_samples": len(e.samples),
                         "cover_s": e.cover_ns / NS, "repricings": e.repricings,
                         "tracked_ok": w.tracked_since.get(e.cand.ticker, 1 << 62) <= e.entry_ns + TRACK_GRACE_NS,
                         "net": p["conservative"] + trading})
    return rows
