"""Per-market tables for RESULTS.md, derived offline from the frozen outputs (no network, no new
thresholds). Writes outputs/m2_per_market.csv and outputs/m6_per_program_<tag>.csv."""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

import pt1_common as P


def iso(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def m2():
    rows = [r for r in json.loads((P.OUT / "m2_results.json").read_text()) if r["variant"] == "close"]
    cols = ["league", "ticker", "k", "wins_at_t_star", "played_at_t_star", "deciding_game", "t_star_utc", "close_utc",
            "remaining_hours", "yes_bid_first", "no_ask_first", "yes_bid_time_median", "max_yes_bid",
            "frac_hours_yes_bid_ge_2c", "contracts_taker_safe", "contracts_maker_safe", "contracts_unsafe",
            "gross_safe", "gross_unsafe", "fees_direct_safe", "net_direct_safe", "net_nondirect_safe"]
    with (P.OUT / "m2_per_market.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in sorted(rows, key=lambda r: (r["league"], r["ticker"])):
            g = lambda k: D(r.get(k, "0"))                                    # noqa: E731
            gross_safe = g("gross_taker_safe") + g("gross_maker_safe")
            net_d = g("net_direct_taker_safe") + g("net_direct_maker_safe")
            first = r.get("yes_bid_first")
            w.writerow([r["league"], r["ticker"], r["k"], r["wins_at_t_star"], r["played_at_t_star"], r["deciding_game"],
                        iso(r["t_star"]), iso(r["close_ts"]), f"{r['window_h']:.1f}", first,
                        (str(1 - D(first)) if first is not None else None), r.get("yes_bid_time_median"),
                        r.get("max_yes_bid"), r.get("frac_hours_yes_bid_ge_2c"),
                        g("contracts_taker_safe"), g("contracts_maker_safe"),
                        g("contracts_taker_unsafe") + g("contracts_maker_unsafe"), gross_safe,
                        g("gross_taker_unsafe") + g("gross_maker_unsafe"), gross_safe - net_d, net_d,
                        g("net_nondirect_taker_safe") + g("net_nondirect_maker_safe")])


def m6(tag: str):
    p = P.OUT / f"m6_{tag}.json"
    if not p.exists():
        return
    rows = json.loads(p.read_text())["rows"]
    cols = ["stratum", "ticker", "program_id", "target", "period_reward", "period_days", "discount", "fee_type", "mode",
            "quote_yes", "quote_no", "others_yes_depth", "others_no_depth", "volume_24h", "x_min", "payout_at_xmin",
            "share_yes", "share_no", "capital_committed", "worst_fill_loss", "compatible", "x_at_budget",
            "payout_at_budget", "formula_only_1c_capital", "snapshot_utc"]
    with (P.OUT / f"m6_per_program_{tag}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])


if __name__ == "__main__":
    m2()
    for tag in (sys.argv[1:] or ["first", "second"]):
        m6(tag)
