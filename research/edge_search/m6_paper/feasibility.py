"""M6 static capital feasibility at K = $30 / $100 / $200 (REPORTED ONLY; not the paper experiment).

One snapshot of every live liquidity program and its market's full order book (public GETs only; no
orders, no credentials). For each program, using the PT1-frozen scoring and quoting functions:
  x15  = smallest equal per-side size whose projected payout over the REMAINING period is >= $1.50
         (static book, full uptime: the experiment's frozen entry-size rule, DESIGN.md §4.2)
  C*   = x15*(p_y + p_n) + max(x15*p_y, x15*p_n) + maker fee on that fill (PT1 definition)
  L*   = max(x15*p_y, x15*p_n) + maker fee (worst plausible one-side fill, lost if it resolves against us)
  score = projected reward per day / C*
Greedy per K by score (one program per market). Primary view = the experiment's frozen Arm P entry rule
(>= 24 h of the program remaining at entry); the unrestricted view (>= 1 h) is reported for contrast.
Fee state: series fee type/multiplier from GET /series by event-ticker prefix (unknown -> maker fees at M=1,
conservative); event-level overrides are not read. Static: no fills, no competitor response, no adverse selection. Output: outputs/feasibility_<utc>.json/.txt
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "price_test_1"))
import pt1_common as P                                        # noqa: E402
from m6_rewards import configure, side_share                   # noqa: E402  (PT1-frozen functions)

KS = (D(30), D(100), D(200))
MARGIN = D("1.50")
MAX_X = 20000


def programs():
    out, cur = [], None
    while True:
        d = P.get("/incentive_programs", {"status": "active", "type": "liquidity", "limit": 1000, **({"cursor": cur} if cur else {})})
        out += d.get("incentive_programs", [])
        cur = d.get("next_cursor")
        if not cur or not d.get("incentive_programs"):
            return out


def fetch_markets(tickers):
    mk = {}
    for i in range(0, len(tickers), 50):
        for m in (P.get("/markets", {"tickers": ",".join(tickers[i:i + 50]), "limit": 1000}) or {}).get("markets", []):
            mk[m["ticker"]] = m
    return mk


def fetch_books(tickers):
    books = {}
    for i in range(0, len(tickers), 100):
        q = "&".join(f"tickers={t}" for t in tickers[i:i + 100])
        d = P.get("/markets/orderbooks?" + q) or {}
        for b in d.get("orderbooks", []):
            books[b["ticker"]] = b.get("orderbook_fp") or {}
    return books


def evaluate(g, m, book, now):
    T = D(g["target_size_fp"]); d = D(g["discount_factor_bps"]) / 10000; R = D(g["period_reward"]) / 10000
    start, end = P.ts(g["start_date"]), P.ts(g["end_date"])
    rem = D(max(0, end - now)) / D(max(1, end - start))
    py, pn, mode, yb, nb, ranges = configure(book, m)

    def pay(x):
        sy, sn = side_share(yb, py, D(x), T, d, ranges), side_share(nb, pn, D(x), T, d, ranges)
        return D(0) if sy is None or sn is None else R * rem * (sy + sn) / 2

    lo, hi = 1, 1
    while hi <= MAX_X and pay(hi) < MARGIN:
        lo, hi = hi, hi * 2
    if hi > MAX_X:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if pay(mid) >= MARGIN else (mid + 1, hi)
    x = D(lo)
    big = max(x * py, x * pn)
    ftype = m.get("_fee_type", "quadratic")
    mf = P.fee(py if x * py >= x * pn else pn, x, D(m.get("_fee_mult", 1)), P.MAKER_COEF)[0] if ftype == "quadratic_with_maker_fees" else D(0)
    C = x * py + x * pn + big + mf
    days_left = D(max(1, end - now)) / 86400
    return {"program_id": g["id"], "ticker": m["ticker"], "event": m["event_ticker"], "x15": int(x), "quote_yes": str(py),
            "quote_no": str(pn), "mode": mode, "C_star": C, "L_star": big + mf, "projected_payout": pay(lo),
            "reward_per_day": pay(lo) / days_left, "days_left": float(days_left), "close_time": m.get("close_time"),
            "volume_24h": m.get("volume_24h_fp"), "score": (pay(lo) / days_left) / C}


def main():
    now = int(time.time())
    progs = [g for g in programs() if g.get("target_size_fp") and P.ts(g["start_date"]) <= now < P.ts(g["end_date"]) - 3600]
    tick = sorted({g["market_ticker"] for g in progs})
    mk = fetch_markets(tick)
    progs = [g for g in progs if mk.get(g["market_ticker"], {}).get("status") == "active"]
    books = fetch_books(sorted({g["market_ticker"] for g in progs}))
    series = {x["ticker"]: x for x in (P.get("/series") or {}).get("series", [])}
    for m in mk.values():          # series fee state by event-ticker prefix; unknown -> maker fees (conservative)
        s = series.get(m["event_ticker"].split("-")[0])
        m["_fee_type"] = s.get("fee_type") if s else "quadratic_with_maker_fees"
        m["_fee_mult"] = (s.get("fee_multiplier") if s else None) or 1
    rows, skipped = [], Counter()
    for g in progs:
        b = books.get(g["market_ticker"])
        if b is None:
            skipped["no_book"] += 1
            continue
        r = evaluate(g, mk[g["market_ticker"]], b, now)
        if r is None:
            skipped["no_x_up_to_20000"] += 1
            continue
        rows.append(r)
    # one program per market: the best-scoring one
    best = {}
    for r in sorted(rows, key=lambda r: (-r["score"], r["program_id"])):
        best.setdefault(r["ticker"], r)
    ranked_all = sorted(best.values(), key=lambda r: (-r["score"], r["program_id"]))
    out_all = {}
    for label, min_days in (("entry_rule_remaining_ge_24h", 1.0), ("any_remaining_ge_1h", 0.0)):
        ranked = [r for r in ranked_all if r["days_left"] >= min_days]
        out_all[label] = report(ranked, rows, progs, skipped, now, label)
    OUT = HERE / "outputs"
    OUT.mkdir(exist_ok=True)
    tag = time.strftime("%Y%m%dT%H%M", time.gmtime(now))
    (OUT / f"feasibility_{tag}.json").write_text(json.dumps({k: v[0] for k, v in out_all.items()}, indent=1, default=str))
    txt = "\n\n".join(v[1] for v in out_all.values())
    (OUT / f"feasibility_{tag}.txt").write_text(txt)
    print(txt)


def report(ranked, rows, progs, skipped, now, label):
    out = {"snapshot_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "live_programs": len(progs),
           "evaluated": len(rows), "markets": len(ranked), "skipped": dict(skipped), "per_K": {}}
    lines = [f"[{label}] snapshot {out['snapshot_utc']}: live programs {len(progs)}, evaluated {len(rows)}, distinct markets {len(ranked)}, skipped {dict(skipped)}"]
    for K in KS:
        afford = [r for r in ranked if r["C_star"] <= K]
        sel, used = [], D(0)
        for r in ranked:
            if used + r["C_star"] <= K:
                sel.append(r); used += r["C_star"]
        rpd = sum(r["reward_per_day"] for r in sel)
        wc = sum(r["L_star"] for r in sel)
        far = sum(1 for r in sel if r["close_time"] and P.ts(r["close_time"]) - now > 30 * 86400)
        out["per_K"][str(K)] = {"affordable_individually": len(afford), "selected": len(sel), "committed": str(used),
                                "static_reward_per_day": str(rpd), "static_reward_per_day_per_dollar": str(rpd / used if used else 0),
                                "worst_case_one_side_fill_loss": str(wc), "selected_closing_after_30d": far,
                                "selected": [{k: (str(v) if isinstance(v, D) else v) for k, v in r.items()} for r in sel]}
        lines.append(f"K=${K}: affordable individually {len(afford)}; greedy selects {len(sel)} programs, committed ${used:.2f}, "
                     f"static reward ${rpd:.2f}/day (${rpd / used if used else 0:.4f}/day per $), worst-case one-side-fill loss "
                     f"${wc:.2f}, selected markets closing > 30 d out: {far}")
        for r in sel[:12]:
            lines.append(f"     {r['ticker'][:40]:40s} x={r['x15']:>4} quotes {r['quote_yes']}/{r['quote_no']} C*=${r['C_star']:.2f} "
                         f"L*=${r['L_star']:.2f} ${r['reward_per_day']:.3f}/day, {r['days_left']:.1f} d left, vol24h {r['volume_24h']}, close {r['close_time'][:10] if r['close_time'] else None}")
    cs = sorted(float(r["C_star"]) for r in ranked)
    q = lambda p: cs[int(p * (len(cs) - 1))] if cs else None                      # noqa: E731
    lines.append(f"C*(x15) across markets: p10 ${q(.1):.2f}, p50 ${q(.5):.2f}, p90 ${q(.9):.2f}; <= $30: {sum(c <= 30 for c in cs)}, "
                 f"<= $100: {sum(c <= 100 for c in cs)}, <= $200: {sum(c <= 200 for c in cs)} of {len(cs)}")
    return out, "\n".join(lines)


if __name__ == "__main__":
    main()
