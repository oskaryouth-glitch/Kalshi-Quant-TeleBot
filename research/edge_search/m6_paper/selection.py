"""Frozen market selection (DESIGN §4). Pure functions of one epoch's recorded data.

Epoch data (recorded raw by the collector): the live liquidity programs, the market object of every
program market, the full order book of every program market, the series list (fee type / multiplier)
and the event -> series map. Fee state for SELECTION = the market's series fee state (exact series from
the event list); an unknown series is treated as maker fees at M = 1 (conservative). Event-level fee
overrides are not available in bulk and are applied to fills, not to selection (PREREG, disclosed).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal as D

from . import accounting as A
from . import lip
from . import spec as S

NS = 1_000_000_000


def ts_ns(s: str) -> int:
    import datetime as dt
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return int(t.timestamp()) * NS + t.microsecond * 1000


@dataclass
class Candidate:
    program_id: str
    ticker: str
    event_ticker: str
    start_ns: int
    end_ns: int
    reward: D            # Time Period Reward, dollars
    target: D
    discount: D
    x: int               # x15
    py: D
    pn: D
    mode: str
    cstar: D
    lstar: D
    reserve: D           # max(x*py, x*pn): fill reserve held in `committed`
    projected: D
    reward_per_day: D
    score: D
    volume_24h: D
    fee_type: str
    fee_mult: D
    price_ranges: list


def epoch_day(epoch_ns: int) -> int:
    """UTC day number (days since 1970-01-01) of an epoch: the Arm U seed offset."""
    return epoch_ns // (86400 * NS)


def fee_state(market: dict, series_fee: dict, event_series: dict) -> tuple[str, D]:
    s = series_fee.get(event_series.get(market.get("event_ticker")))
    if not s:
        return S.UNKNOWN_FEE_STATE
    return s.get("fee_type") or S.UNKNOWN_FEE_STATE[0], D(str(s.get("fee_multiplier") if s.get("fee_multiplier") is not None else 1))


def eligible(program: dict, market: dict | None, now_ns: int) -> bool:
    if program.get("incentive_type", "liquidity") != "liquidity" or not program.get("target_size_fp"):
        return False
    if not market or market.get("status") != "active" or market.get("mve_collection_ticker"):
        return False
    start, end = ts_ns(program["start_date"]), ts_ns(program["end_date"])
    return start <= now_ns and end - now_ns >= S.MIN_REMAINING_S * NS


def evaluate(program: dict, market: dict, book: dict, fee: tuple[str, D], now_ns: int) -> Candidate | None:
    T, d = D(program["target_size_fp"]), D(program["discount_factor_bps"]) / 10000
    R = D(program["period_reward"]) / 10000                       # centi-cents -> dollars
    start, end = ts_ns(program["start_date"]), ts_ns(program["end_date"])
    rem = D(max(0, end - now_ns)) / D(max(1, end - start))
    ranges = market.get("price_ranges") or lip.DEFAULT_RANGES
    py, pn, mode = lip.configure(book, ranges)
    yb, nb = lip.levels(book, "yes"), lip.levels(book, "no")

    def pay(x: int) -> D:
        X = D(x)
        sy, sn = lip.side_share(yb, [(py, X)], T, d, ranges), lip.side_share(nb, [(pn, X)], T, d, ranges)
        return D(0) if sy is None or sn is None else R * rem * (sy + sn) / 2

    lo, hi = 1, 1
    while hi <= S.MAX_X and pay(hi) < S.PAYOUT_TARGET:
        lo, hi = hi, hi * 2
    if hi > S.MAX_X:
        if pay(S.MAX_X) < S.PAYOUT_TARGET:
            return None
        hi = S.MAX_X
    while lo < hi:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if pay(mid) >= S.PAYOUT_TARGET else (mid + 1, hi)
    x = D(lo)
    big_price = py if x * py >= x * pn else pn
    reserve = max(x * py, x * pn)
    mf = A.maker_fee(fee[0], fee[1], big_price, x)
    cstar = x * py + x * pn + reserve + mf
    days_left = D(max(1, end - now_ns)) / D(86400 * NS)
    projected = pay(lo)
    rpd = projected / days_left
    return Candidate(program["id"], market["ticker"], market["event_ticker"], start, end, R, T, d, lo, py, pn, mode,
                     cstar, reserve + mf, reserve, projected, rpd, rpd / cstar, D(market.get("volume_24h_fp") or 0),
                     fee[0], fee[1], ranges)


def candidates(epoch: dict) -> list[Candidate]:
    """All evaluable eligible programs of one recorded epoch."""
    now = epoch["epoch_ns"]
    out = []
    for g in epoch["programs"]:
        m = epoch["markets"].get(g.get("market_ticker"))
        b = epoch["books"].get(g.get("market_ticker"))
        if b is None or not eligible(g, m, now):
            continue
        c = evaluate(g, m, b, fee_state(m, epoch["series_fee"], epoch["event_series"]), now)
        if c is not None:
            out.append(c)
    return out


def ranked(cands: list[Candidate]) -> list[Candidate]:
    """One program per market (highest score, ties by program id), sorted by score desc, ties by id."""
    best: dict[str, Candidate] = {}
    for c in sorted(cands, key=lambda c: (-c.score, c.program_id)):
        best.setdefault(c.ticker, c)
    return sorted(best.values(), key=lambda c: (-c.score, c.program_id))


def admit(ranking: list[Candidate], held_markets: set[str], committed: D, K: D) -> list[Candidate]:
    """Arm P greedy admission (DESIGN §4.3)."""
    out = []
    for c in ranking:
        if c.ticker in held_markets:
            continue
        if committed + c.cstar <= K:
            out.append(c)
            committed += c.cstar
            held_markets = held_markets | {c.ticker}
    return out


def u_draw(cands: list[Candidate], epoch_ns: int, epoch_day: int) -> list[Candidate]:
    """Arm U (DESIGN §4.4): programs started within the previous 24 h with C* <= $200; 10 per 24-h-volume
    stratum, random.Random(20261001 + epoch_day), candidates sorted by program id before drawing."""
    pool = [c for c in ranked(cands) if epoch_ns - S.U_START_WINDOW_S * NS < c.start_ns <= epoch_ns
            and c.cstar <= S.U_MAX_CSTAR]
    zero = sorted((c for c in pool if c.volume_24h == 0), key=lambda c: c.program_id)
    nonz = sorted((c for c in pool if c.volume_24h > 0), key=lambda c: c.program_id)
    rng = random.Random(S.U_SEED_BASE + epoch_day)
    return rng.sample(zero, min(S.U_PER_STRATUM, len(zero))) + rng.sample(nonz, min(S.U_PER_STRATUM, len(nonz)))
