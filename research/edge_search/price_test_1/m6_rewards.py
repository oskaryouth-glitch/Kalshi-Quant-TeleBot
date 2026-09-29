"""PRICE TEST 1 — M6-REWARDS: minimum capital for a small participant (frozen; PREREG.md §M6).

Scoring = Liquidity Incentive Program terms filed 2026-07-15 (effective 2026-07-30), as modified
2026-07-30. For each side (a YES ask counts as a NO bid): walk bid levels from the best down,
accumulating size. Reference Price = first level where cumulative >= Target/5; stop once
cumulative >= Target; if never, the side has no qualifying bids and the snapshot is excluded.
score(bid) = DF^(ticks below the Reference, 0 if at/above) x size, normalised per side. A user's
snapshot score = own YES share + own NO share (<= 2). Payout = period score x Reward x
(non-excluded / total snapshots), paid only if >= $1.00.

Purpose-consistent configuration (frozen): equal size x on both sides; quote at the current best
YES bid and best NO bid when their combined spread is <= 10c; otherwise quote a 10c-wide market
centred on the current mid (0.50 if a side is empty); never cross. A "1c/1c" formula-only
configuration is reported but excluded (inconsistent with the Program's purpose; CRO revocation).

Capital simultaneously committed C*(x) = x*b_yes + x*b_no (resting, 'sum' reservation)
    + max(x*b_yes, x*b_no) (worst plausible fill: the whole larger side filled and held, with the
    side re-posted to stay eligible) + maker fee on that fill. Zero volume is NOT treated as
    zero fill risk. Worst plausible filled-inventory loss L*(x) = max(x*b_yes, x*b_no) + maker fee.
"""
from __future__ import annotations

import random
import statistics
import sys
import time
from decimal import Decimal, ROUND_FLOOR

import pt1_common as P

SEED = 20260929
PER_STRATUM = 30
V_SMALL = Decimal("1000")
PER_MARKET_BUDGET = V_SMALL / 5          # $200: at least five markets per very small account
PAYOUT_FLOOR = Decimal("1.00")
KILL_IF_COMPATIBLE_FRACTION_BELOW = 0.10
MAX_X = 20000


def grid_ticks(ranges: list[dict], lo: Decimal, hi: Decimal) -> int:
    """Number of price-grid steps from lo up to hi (lo <= hi)."""
    n = Decimal(0)
    for r in ranges:
        s, e, st = Decimal(r["start"]), Decimal(r["end"]), Decimal(r["step"])
        a, b = max(lo, s), min(hi, e)
        if b > a:
            n += (b - a) / st
    return int(n.to_integral_value())


def snap_down(p: Decimal, ranges: list[dict]) -> Decimal:
    for r in ranges:
        s, e, st = Decimal(r["start"]), Decimal(r["end"]), Decimal(r["step"])
        if s <= p <= e:
            return s + ((p - s) / st).to_integral_value(rounding=ROUND_FLOOR) * st
    return p.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)


def side_share(levels: list[tuple[Decimal, Decimal]], my_price: Decimal, x: Decimal, T: Decimal, d: Decimal,
               ranges: list[dict]):
    """levels: others' bids [(price, size)]. Returns my normalised share or None if excluded."""
    book = {}
    for p, s in levels:
        book[p] = book.get(p, Decimal(0)) + s
    book[my_price] = book.get(my_price, Decimal(0)) + x
    cum, ref, visited = Decimal(0), None, []
    for p in sorted(book, reverse=True):
        cum += book[p]
        visited.append(p)
        if ref is None and cum >= T / 5:
            ref = p
        if cum >= T:
            break
    if cum < T:
        return None
    w = lambda p: Decimal(1) if p >= ref else d ** grid_ticks(ranges, p, ref)
    total = sum(book[p] * w(p) for p in visited)
    mine = x * w(my_price) if my_price in visited else Decimal(0)
    return mine / total if total > 0 else None


def configure(book: dict, market: dict):
    ranges = market.get("price_ranges") or [{"start": "0", "end": "1", "step": "0.01"}]
    yb = sorted(((Decimal(p), Decimal(q)) for p, q in (book.get("yes_dollars") or [])), reverse=True)
    nb = sorted(((Decimal(p), Decimal(q)) for p, q in (book.get("no_dollars") or [])), reverse=True)
    by, bn = (yb[0][0] if yb else None), (nb[0][0] if nb else None)
    if by is not None and bn is not None and by + bn >= Decimal("0.90"):
        return by, bn, "join_best", yb, nb, ranges
    if by is not None and bn is not None:
        mid = (by + (1 - bn)) / 2
    elif by is not None:
        mid = min(by + Decimal("0.05"), Decimal("0.94"))
    elif bn is not None:
        mid = max(1 - bn - Decimal("0.05"), Decimal("0.06"))
    else:
        mid = Decimal("0.50")
    py = snap_down(max(mid - Decimal("0.05"), Decimal("0.01")), ranges)
    pn = snap_down(max((1 - mid) - Decimal("0.05"), Decimal("0.01")), ranges)
    return py, pn, "improve_to_10c", yb, nb, ranges


def evaluate(prog: dict, market: dict, book: dict, fee_type: str, mult: Decimal) -> dict:
    T = Decimal(prog["target_size_fp"]); d = Decimal(prog["discount_factor_bps"]) / 10000
    R = Decimal(prog["period_reward"]) / 10000
    py, pn, mode, yb, nb, ranges = configure(book, market)

    def payout(x: int):
        X = Decimal(x)
        sy, sn = side_share(yb, py, X, T, d, ranges), side_share(nb, pn, X, T, d, ranges)
        if sy is None or sn is None:
            return Decimal(0), sy, sn
        return R * (sy + sn) / 2, sy, sn

    def capital(x: int):
        X = Decimal(x)
        big = max(X * py, X * pn)
        mf = P.fee(py if X * py >= X * pn else pn, X, mult, P.MAKER_COEF)[0] if fee_type == "quadratic_with_maker_fees" else Decimal(0)
        return X * py + X * pn + big + mf, big + mf

    lo, hi = 1, 1
    while hi <= MAX_X and payout(hi)[0] < PAYOUT_FLOOR:
        lo, hi = hi, hi * 2
    xmin = None
    if hi <= MAX_X or payout(MAX_X)[0] >= PAYOUT_FLOOR:
        hi = min(hi, MAX_X)
        while lo < hi:
            mid = (lo + hi) // 2
            if payout(mid)[0] >= PAYOUT_FLOOR:
                hi = mid
            else:
                lo = mid + 1
        xmin = lo if payout(lo)[0] >= PAYOUT_FLOOR else None
    out = {"ticker": market["ticker"], "program_id": prog["id"], "target": str(T), "discount": str(d), "period_reward": str(R),
           "period_days": (P.ts(prog["end_date"]) - P.ts(prog["start_date"])) / 86400, "mode": mode,
           "quote_yes": str(py), "quote_no": str(pn), "fee_type": fee_type,
           "others_yes_depth": str(sum(q for _, q in yb)), "others_no_depth": str(sum(q for _, q in nb)),
           "volume_24h": market.get("volume_24h_fp"), "x_min": xmin}
    if xmin is not None:
        pay, sy, sn = payout(xmin); C, L = capital(xmin)
        out.update(payout_at_xmin=str(pay), share_yes=str(sy), share_no=str(sn), capital_committed=str(C), worst_fill_loss=str(L),
                   compatible=bool(C <= PER_MARKET_BUDGET))
    else:
        out.update(compatible=False)
    # budget-limited: largest x with C*(x) <= $200, and its payout
    xb = 0
    step = 1 << 14
    while step:
        if xb + step <= MAX_X and capital(xb + step)[0] <= PER_MARKET_BUDGET:
            xb += step
        step >>= 1
    if xb:
        out.update(x_at_budget=xb, payout_at_budget=str(payout(xb)[0]))
    # formula-only 1c/1c (excluded from the decision): capital if a lone provider posts Target at 1c both sides
    out["formula_only_1c_capital"] = str(T * Decimal("0.01") * 3)
    return out


def sample():
    progs, cur = [], None
    while True:
        p = {"status": "active", "type": "liquidity", "limit": 1000}
        if cur:
            p["cursor"] = cur
        d = P.get("/incentive_programs", p)
        progs += d.get("incentive_programs", [])
        cur = d.get("next_cursor")
        if not cur or not d.get("incentive_programs"):
            break
    now = time.time()
    progs = [g for g in progs if P.ts(g["start_date"]) <= now < P.ts(g["end_date"]) - 3600 and g.get("target_size_fp")]
    tick = sorted({g["market_ticker"] for g in progs})
    mk = {}
    for i in range(0, len(tick), 50):
        d = P.get("/markets", {"tickers": ",".join(tick[i:i + 50]), "limit": 1000})
        for m in d.get("markets", []):
            mk[m["ticker"]] = m
    progs = [g for g in progs if mk.get(g["market_ticker"], {}).get("status") == "active"]
    zero = sorted((g for g in progs if Decimal(mk[g["market_ticker"]].get("volume_24h_fp") or "0") == 0), key=lambda g: g["id"])
    nonz = sorted((g for g in progs if Decimal(mk[g["market_ticker"]].get("volume_24h_fp") or "0") > 0), key=lambda g: g["id"])
    rng = random.Random(SEED)
    pick = rng.sample(zero, min(PER_STRATUM, len(zero))) + rng.sample(nonz, min(PER_STRATUM, len(nonz)))
    return pick, mk, {"live_programs": len(progs), "zero_volume": len(zero), "nonzero_volume": len(nonz)}


def run(tag: str, pick=None, mk=None):
    meta = {}
    if pick is None:
        pick, mk, meta = sample()
    series_fee = {}
    rows = []
    for g in pick:
        m = mk[g["market_ticker"]]
        ev = P.get(f"/events/{m['event_ticker']}", allow_404=True) or {}
        st = (ev.get("event") or {}).get("series_ticker")
        if st and st not in series_fee:
            s = P.get(f"/series/{st}")["series"]; series_fee[st] = (s.get("fee_type"), P.dec(s.get("fee_multiplier")))
        ft, mult = series_fee.get(st, ("quadratic", Decimal(1)))
        e = ev.get("event") or {}
        if e.get("fee_type_override"):
            ft, mult = e["fee_type_override"], P.dec(e.get("fee_multiplier_override")) or mult
        book = (P.get(f"/markets/{m['ticker']}/orderbook") or {}).get("orderbook_fp") or {}
        r = evaluate(g, m, book, ft, mult)
        r["stratum"] = "zero_volume" if Decimal(m.get("volume_24h_fp") or "0") == 0 else "nonzero_volume"
        r["snapshot_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rows.append(r)
    P.save(f"m6_{tag}.json", {"meta": meta, "rows": rows, "sample": pick, "markets": {g['market_ticker']: mk[g['market_ticker']] for g in pick}})
    return rows


def summarize(rows, tag):
    lines = [f"[{tag}] sampled programs={len(rows)}"]
    for strat in ("zero_volume", "nonzero_volume", None):
        rs = [r for r in rows if strat is None or r["stratum"] == strat]
        comp = [r for r in rs if r.get("compatible")]
        caps = [Decimal(r["capital_committed"]) for r in rs if r.get("capital_committed")]
        lines.append(f"   {strat or 'ALL'}: n={len(rs)} compatible(C*<=$200 & payout>=$1)={len(comp)} "
                     f"({len(comp)/len(rs):.0%}) median C* where finite={statistics.median(caps) if caps else None} "
                     f"x_min undefined={sum(r['x_min'] is None for r in rs)}")
    frac = sum(bool(r.get("compatible")) for r in rows) / len(rows) if rows else 0
    lines.append(f"   DECISION: {'KILL' if frac < KILL_IF_COMPATIBLE_FRACTION_BELOW else 'SURVIVE (capital-compatible)'}"
                 f" (compatible fraction {frac:.0%}; kill threshold {KILL_IF_COMPATIBLE_FRACTION_BELOW:.0%})")
    txt = "\n".join(lines)
    (P.OUT / f"m6_summary_{tag}.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    if "--second-pass" in sys.argv:
        import json
        prev = json.loads((P.OUT / "m6_first.json").read_text())
        summarize(run("second", prev["sample"], prev["markets"]), "second")
    else:
        summarize(run("first"), "first")
