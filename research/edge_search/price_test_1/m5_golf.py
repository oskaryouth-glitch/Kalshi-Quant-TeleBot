"""PRICE TEST 1 — M5-GOLF: pricing/calibration of "top N (including ties)" fields (frozen; PREREG.md §M5).

Payout identity (GOLFFINISH): S = sum_i YES_payout_i = #{i : official position_i <= N} (competition
ranking; boundary ties are Yes) + sum of discretionary fair prices for players who withdrew before
tee-off. S >= N in every completed tournament and is not bounded above by N.
Pricing statistic: the whole field priced at a fixed pre-tournament time t_s:
    A = sum ask_i (cost to buy one YES of every listed player), B = sum bid_i, M = sum mid_i.
Calibration: E[S] should lie in [B - F_sell, A + F_buy]. Per valid event:
    U = S - A - F_buy   (> 0 on average: the whole field was cheaper than its payout, beyond friction)
    O = B - F_sell - S  (> 0 on average: the whole field was dearer than its payout, beyond friction)
Coverage: an observation is valid only if the number of listed players who teed off (markets that
settled yes/no, i.e. not at a pre-tee-off fair price) equals the official field size from
inputs/golf_coverage.csv (sourced; see PREREG). Anything else invalidates the observation.
"""
from __future__ import annotations

import csv
import math
import statistics
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pt1_common as P
from m2_no import settled

SERIES = {"KXPGATOP10": 10, "KXPGATOP5": 5, "KXPGATOP20": 20}   # KXPGATOP10 is the primary test
PRIMARY = "KXPGATOP10"
MIN_VALID = 8
COVERAGE = Path(__file__).resolve().parent / "inputs" / "golf_coverage.csv"
# one-sided 95% and two-sided 95% Student-t critical values, df 1..40 (df > 40 -> normal)
T95 = [6.314, 2.920, 2.353, 2.132, 2.015, 1.943, 1.895, 1.860, 1.833, 1.812, 1.796, 1.782, 1.771, 1.761, 1.753,
       1.746, 1.740, 1.734, 1.729, 1.725, 1.721, 1.717, 1.714, 1.711, 1.708, 1.706, 1.703, 1.701, 1.699, 1.697,
       1.696, 1.694, 1.692, 1.691, 1.690, 1.688, 1.687, 1.686, 1.685, 1.684]
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
        2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
        2.040, 2.037, 2.035, 2.032, 2.030, 2.028, 2.026, 2.024, 2.023, 2.021]


def tcrit(df: int, table: list, z: float) -> float:
    return table[df - 1] if 1 <= df <= len(table) else z


def coverage() -> dict:
    rows = {}
    with COVERAGE.open() as f:
        for r in csv.DictReader(f):
            rows[r["tournament_code"]] = r
    return rows


def snapshot_ts(first_round_date: str) -> int:
    d = datetime.strptime(first_round_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - timedelta(days=1)
    return int(d.replace(hour=16).timestamp())


def price_event(series: str, event_ms: list[dict], t_s: int, fees: P.SeriesFees) -> dict:
    ftype, mult, exact = fees.at(t_s)
    A = B = M = S = Fbd = Fsd = Fbn = Fsn = Decimal(0)
    two_sided = vol = 0
    for m in event_ms:
        cs = [c for c in P.candles(series, m["ticker"], t_s - 72 * 3600, t_s) if c["end_period_ts"] <= t_s]
        c = cs[-1] if cs else {}
        bid = P.dec((c.get("yes_bid") or {}).get("close")) or Decimal(0)
        ask = P.dec((c.get("yes_ask") or {}).get("close"))
        ask = ask if ask and ask > 0 else Decimal(1)
        two_sided += (bid > 0 and ask < 1)
        vol += sum(float(x.get("volume") or 0) for x in cs if x["end_period_ts"] > t_s - 86400)
        A += ask; B += bid; M += (ask + bid) / 2
        S += P.dec(m.get("settlement_value_dollars")) or Decimal(0)
        if ask < 1:
            fd, fn = P.fee(ask, Decimal(1), mult, P.TAKER_COEF); Fbd += fd; Fbn += fn
        if bid > 0:
            fd, fn = P.fee(Decimal(1) - bid, Decimal(1), mult, P.TAKER_COEF); Fsd += fd; Fsn += fn
    return {"A": A, "B": B, "M": M, "S": S, "F_buy_direct": Fbd, "F_sell_direct": Fsd, "F_buy_nondirect": Fbn,
            "F_sell_nondirect": Fsn, "n_markets": len(event_ms), "n_two_sided": two_sided, "volume_24h": vol,
            "fee_type": ftype, "fee_multiplier": mult, "fee_exact": exact,
            "U": S - A - Fbd, "O": B - Fsd - S, "U_nondirect": S - A - Fbn, "O_nondirect": B - Fsn - S}


def stats(xs: list[float]) -> dict:
    n = len(xs)
    if n < 2:
        return {"n": n}
    m, sd = statistics.mean(xs), statistics.stdev(xs)
    se = sd / math.sqrt(n)
    return {"n": n, "mean": m, "sd": sd, "lb95_one_sided": m - tcrit(n - 1, T95, 1.645) * se,
            "ci95": (m - tcrit(n - 1, T975, 1.96) * se, m + tcrit(n - 1, T975, 1.96) * se)}


def main():
    cov = coverage()
    results, invalid = [], []
    for series, N in SERIES.items():
        fees = P.SeriesFees(series)
        ev = {}
        for m in settled(series):
            ev.setdefault(m["event_ticker"], []).append(m)
        for e, ms in sorted(ev.items()):
            code = e.split("-", 1)[1]
            teed = sum(1 for m in ms if m["result"] in ("yes", "no"))
            c = cov.get(code)
            if c is None or not c.get("official_field_size") or not c.get("first_round_date"):
                invalid.append((e, "no sourced official field size / first-round date")); continue
            if teed != int(c["official_field_size"]):
                invalid.append((e, f"coverage mismatch: listed teed-off {teed} vs official {c['official_field_size']}")); continue
            if not all(m["result"] in ("yes", "no", "scalar") for m in ms):
                invalid.append((e, "unsettled market")); continue
            t_s = snapshot_ts(c["first_round_date"])
            r = price_event(series, ms, t_s, fees)
            r.update(series=series, N=N, event=e, t_s=t_s, teed=teed)
            results.append(r)
    P.save("m5_results.json", {"results": results, "invalid": invalid})
    lines = []
    for series, N in SERIES.items():
        rs = [r for r in results if r["series"] == series]
        su, so = stats([float(r["U"]) for r in rs]), stats([float(r["O"]) for r in rs])
        tie = stats([float(r["S"] - r["M"]) for r in rs])
        lines.append(f"{series} (N={N}) valid events={len(rs)}")
        lines.append(f"   U = S - A - F_buy : {su}")
        lines.append(f"   O = B - F_sell - S: {so}")
        lines.append(f"   S - M (tie reflection): {tie}")
        lines.append(f"   mean M - N = {statistics.mean([float(r['M']) - N for r in rs]) if rs else None};"
                     f" mean S - N = {statistics.mean([float(r['S']) - N for r in rs]) if rs else None}")
        if series == PRIMARY:
            if len(rs) < MIN_VALID:
                lines.append(f"   DECISION: INCONCLUSIVE (valid events {len(rs)} < {MIN_VALID})")
            else:
                kill = su["lb95_one_sided"] <= 0 and so["lb95_one_sided"] <= 0
                lines.append(f"   DECISION: {'KILL (no mispricing beyond bid/ask + fees)' if kill else 'SURVIVE'}")
    lines.append(f"invalid observations: {len(invalid)}")
    txt = "\n".join(lines)
    (P.OUT / "m5_summary.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
