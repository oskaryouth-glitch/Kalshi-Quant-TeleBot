"""PRICE TEST 1 — M2-NO: already-decided NO markets (frozen; see PREREG.md §M2-NO).

Universe (frozen):
  * KXNBAWINS (2025-26 regular season; "at least k wins"; ENTITYOUTCOME), with games from KXNBAGAME;
  * KXNFLWINS (2026-27 regular season, markets settled so far; WINTOTAL), with games from KXNFLGAME.
  NCAAF is excluded ex ante: its regular-season schedule cannot be verified from Kalshi data.

NO-certainty: after game g of a team, wins W and games played P; NO is certain for "at least k" once
W + (G - P) < k (G = 82 NBA, 17 NFL; ties are played games with no win). t* = close_time of the
game market (Kalshi stops trading a game only once its result is known). Missing games can only
delay t*, never advance it. Extra (non-regular-season) games could advance it, so an NBA team
whose sequence does not contain exactly 82 decided games is invalid.

Price data after t* (hourly candlesticks, public trades) is read only by `measure()`.
"""
from __future__ import annotations

import collections as C
import statistics
import sys
from decimal import Decimal

import pt1_common as P

NBA_WINDOW = ("2025-10-21", "2026-04-13")   # close_time UTC date, regular season 2025-26
NFL_WINDOW = ("2026-09-09", "2026-09-30")   # 2026-27 season games settled at test time
SAFE_5_11 = Decimal("0.20")                 # fair YES value is 0 after certainty; ±$0.20 band
K1_MIN_NET_SAFE_CAPTURE = Decimal("250")    # $, all markets combined
K2_FLOOR = Decimal("0.01")                  # median post-t* time-median YES bid at/below the 1c floor


def settled(series: str) -> list[dict]:
    out = {}
    for path, extra in (("/markets", {"status": "settled"}), ("/historical/markets", {})):
        cur = None
        while True:
            p = {"series_ticker": series, "limit": 1000, **extra}
            if cur:
                p["cursor"] = cur
            d = P.get(path, p) or {}
            for m in d.get("markets", []):
                out[m["ticker"]] = m
            cur = d.get("cursor")
            if not cur or not d.get("markets"):
                break
    return list(out.values())


def team_games(game_series: str, window: tuple[str, str], tie_allowed: bool):
    """team -> list of (t_close, t_settle, won: bool, tie: bool, event). Returns (games, problems)."""
    ev = C.defaultdict(list)
    for m in settled(game_series):
        if window[0] <= m["close_time"][:10] <= window[1]:
            ev[m["event_ticker"]].append(m)
    games, problems = C.defaultdict(list), []
    for e, ms in ev.items():
        res = sorted(m["result"] for m in ms)
        vals = {m.get("settlement_value_dollars") for m in ms}
        if res == ["no", "yes"]:
            for m in ms:
                games[m["ticker"].rsplit("-", 1)[1]].append((P.ts(m["close_time"]), P.ts(m["settlement_ts"]), m["result"] == "yes", False, e))
        elif tie_allowed and res == ["scalar", "scalar"] and vals == {"0.5000"}:
            for m in ms:   # FOOTBALLGAMEWIN Amendment 3: tie without a Tie strike pays 0.50/0.50
                games[m["ticker"].rsplit("-", 1)[1]].append((P.ts(m["close_time"]), P.ts(m["settlement_ts"]), False, True, e))
        elif res == ["scalar", "scalar"]:
            problems.append(("game settled at fair price (not played as scheduled); excluded", e, sorted(vals)))
        else:
            problems.append(("unexpected game result pattern", e, res))
    for t in games:
        games[t].sort()
    return games, problems


def no_certainty(games: list, k: int, G: int, use_settle: bool = False):
    w = p = 0
    for tc, tset, won, tie, e in games:
        p += 1
        w += won
        if w + (G - p) < k:
            return (tset if use_settle else tc), e, w, p
    return None


def build(league: str):
    if league == "NBA":
        wins, (games, probs), G = settled("KXNBAWINS"), team_games("KXNBAGAME", NBA_WINDOW, False), 82
        team_of = lambda m: m["event_ticker"].split("-")[1]
    else:
        wins, (games, probs), G = settled("KXNFLWINS"), team_games("KXNFLGAME", NFL_WINDOW, True), 17
        team_of = lambda m: m["event_ticker"].split("-")[1][2:]
    rows, invalid = [], []
    for m in wins:
        team, k = team_of(m), m.get("floor_strike")
        if m.get("strike_type") != "greater_or_equal" or k is None:
            invalid.append((m["ticker"], "strike shape")); continue
        g = games.get(team)
        if not g:
            invalid.append((m["ticker"], f"no games for team {team}")); continue
        if league == "NBA" and len(g) != 82:
            invalid.append((m["ticker"], f"team {team} has {len(g)} decided games, not 82")); continue
        for variant in ("close", "settle"):
            nc = no_certainty(g, int(k), G, use_settle=(variant == "settle"))
            if nc is None:
                continue
            t_star, deciding, w, p = nc
            if m["result"] == "yes":
                invalid.append((m["ticker"], "NO-certain by formula but settled YES")); break
            rows.append({"league": league, "ticker": m["ticker"], "series": m["event_ticker"].split("-")[0], "team": team,
                         "k": int(k), "variant": variant, "t_star": t_star, "deciding_game": deciding,
                         "wins_at_t_star": w, "played_at_t_star": p, "close_ts": P.ts(m["close_time"]),
                         "result": m["result"], "window_h": (P.ts(m["close_time"]) - t_star) / 3600})
    return rows, invalid, probs


def measure(row: dict, fees: P.SeriesFees) -> dict:
    t0, t1 = row["t_star"], row["close_ts"]
    out = dict(row)
    if t1 <= t0:
        out.update(closed_at_or_before_certainty=True)
        return out
    cs = [c for c in P.candles(row["series"], row["ticker"], t0 - 3600, t1 + 3600) if t0 < c["end_period_ts"] <= t1 + 3600]
    bids = [P.dec((c.get("yes_bid") or {}).get("close")) or P.D0 for c in cs]
    tr = [t for t in P.trades(row["ticker"], t0 + 1, t1) if P.ts(t["created_time"]) > t0]
    agg = C.defaultdict(Decimal)
    for t in tr:
        y, n = P.dec(t["yes_price_dollars"]), P.dec(t["count_fp"])
        ftype, mult, exact = fees.at(P.ts(t["created_time"]))
        safe = "safe" if y <= SAFE_5_11 else "unsafe"
        gross = y * n
        if t["taker_side"] == "no":        # taker bought NO at 1 - y: the taker captured y per contract
            fd, fn = P.fee(P.D1 - y, n, mult, P.TAKER_COEF)
            role = "taker"
        else:                               # taker bought YES: a resting NO bid (maker) captured y
            fd, fn = P.fee(P.D1 - y, n, mult, P.MAKER_COEF) if ftype == "quadratic_with_maker_fees" else (P.D0, P.D0)
            role = "maker"
        agg[f"gross_{role}_{safe}"] += gross
        agg[f"contracts_{role}_{safe}"] += n
        agg[f"net_direct_{role}_{safe}"] += gross - fd
        agg[f"net_nondirect_{role}_{safe}"] += gross - fn
        if not exact:
            agg["fee_state_inexact_trades"] += 1
    out.update(closed_at_or_before_certainty=False, n_candles=len(cs), n_trades=len(tr),
               yes_bid_first=str(bids[0]) if bids else None,
               yes_bid_time_median=str(statistics.median(bids)) if bids else None,
               frac_hours_yes_bid_ge_2c=(sum(b >= Decimal("0.02") for b in bids) / len(bids)) if bids else None,
               max_yes_bid=str(max(bids)) if bids else None, **{k: str(v) for k, v in agg.items()})
    return out


def main():
    all_rows, all_invalid, all_probs = [], [], []
    for lg in ("NBA", "NFL"):
        r, i, p = build(lg)
        all_rows += r; all_invalid += i; all_probs += p
    P.save("m2_universe.json", {"rows": all_rows, "invalid": all_invalid, "game_problems": all_probs})
    if "--universe-only" in sys.argv:
        print(len(all_rows), "rows;", len(all_invalid), "invalid"); return
    fee_cache = {}
    results = []
    for row in all_rows:
        s = row["series"]
        if s not in fee_cache:
            fee_cache[s] = P.SeriesFees(s)
        results.append(measure(row, fee_cache[s]))
    P.save("m2_results.json", results)
    summarize(results)


def summarize(results):
    lines = []
    for variant in ("close", "settle"):
        rs = [r for r in results if r["variant"] == variant]
        open_ = [r for r in rs if not r["closed_at_or_before_certainty"]]
        net = sum(Decimal(r.get(f"net_direct_{role}_safe", "0")) for r in open_ for role in ("taker", "maker"))
        net_nd = sum(Decimal(r.get(f"net_nondirect_{role}_safe", "0")) for r in open_ for role in ("taker", "maker"))
        gross_all = sum(Decimal(r.get(f"gross_{role}_{s}", "0")) for r in open_ for role in ("taker", "maker") for s in ("safe", "unsafe"))
        gross_unsafe = sum(Decimal(r.get(f"gross_{role}_unsafe", "0")) for r in open_ for role in ("taker", "maker"))
        med_bids = [Decimal(r["yes_bid_time_median"]) for r in open_ if r.get("yes_bid_time_median") is not None]
        med = statistics.median(med_bids) if med_bids else None
        lines.append(f"[{variant}] NO-certain markets={len(rs)} open after t*={len(open_)} closed at/before t*={len(rs)-len(open_)}")
        lines.append(f"   window hours median={statistics.median([r['window_h'] for r in open_]) if open_ else None}")
        lines.append(f"   executed gross after t* (all)={gross_all}  of which 5.11-unsafe (yes>0.20)={gross_unsafe}")
        lines.append(f"   net 5.11-safe capture: direct={net} nondirect={net_nd}")
        lines.append(f"   median of per-market time-median YES bid after t* = {med}")
        if variant == "close":
            k1, k2 = net < K1_MIN_NET_SAFE_CAPTURE, (med is None or med <= K2_FLOOR)
            lines.append(f"   K1 (net safe capture < ${K1_MIN_NET_SAFE_CAPTURE}) = {k1};  K2 (median YES bid <= $0.01) = {k2}")
            lines.append(f"   DECISION: {'KILL' if (k1 or k2) else 'SURVIVE'}")
    txt = "\n".join(lines)
    (P.OUT / "m2_summary.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
