"""Pre-start technical smoke check (DESIGN §0: allowed before the freeze; data deleted unread).

Runs the REAL collector code against the live public API once: one epoch, 3 book polls, 3 trade polls,
one fee-state poll, one completeness pass and one rules-watch listing, into a temporary directory. It
checks only field formats, record integrity, request counts and timings, never episodes, rewards or
P&L (the simulator is not run), then deletes the directory. Public GETs only; no orders.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from decimal import Decimal as D

from . import collector as C
from . import lip
from . import selection as SEL
from . import storage as ST


def main() -> dict:
    root = tempfile.mkdtemp(prefix="m6_smoke_")
    out: dict = {}
    try:
        http = C.Http()
        c = C.Collector(http, ST.Writer(root))
        t0 = time.time()
        now = time.time_ns()
        rec = c.epoch(C.epoch_due(None, now))
        out["epoch_s"] = round(time.time() - t0, 1)
        out["programs"], out["markets"], out["books"] = len(rec["programs"]), len(rec["markets"]), len(rec["books"])
        out["missing_books"] = len(rec["missing_books"])
        out["event_series"], out["series_fee"] = len(rec["event_series"]), len(rec["series_fee"])
        out["tracked_after_epoch"] = len(c.tracked)
        # formats the simulator relies on
        b = next(iter(rec["books"].values()))
        lip.levels(b, "yes"), lip.levels(b, "no")
        out["book_format_ok"] = all(isinstance(p, str) and isinstance(q, str) for bk in rec["books"].values()
                                    for side in ("yes_dollars", "no_dollars") for p, q in (bk.get(side) or []))
        cands = SEL.candidates(rec)
        out["evaluable_candidates"] = len(cands)
        out["program_fields_ok"] = all(k in rec["programs"][0] for k in ("id", "market_ticker", "start_date", "end_date",
                                                                         "period_reward", "target_size_fp", "discount_factor_bps"))
        t1 = time.time()
        polls = [c.poll_books() for _ in range(3)]
        out["book_poll_s_each"] = round((time.time() - t1) / 3, 2)
        out["book_poll_changed"] = [len(p["books"]) for p in polls]
        out["book_poll_missing"] = [len(p["missing"]) for p in polls]
        trades = [c.poll_trades() or 0 for _ in range(3) if not time.sleep(5)]
        out["trades_kept_per_poll"] = trades
        tr = [t for r in ST.read(root, "trades") for t in r["trades"]]
        out["trade_format_ok"] = all({"ticker", "trade_id", "created_time", "taker_side", "count_fp",
                                      "yes_price_dollars", "no_price_dollars"} <= set(t) for t in tr)
        out["taker_sides"] = sorted({t["taker_side"] for t in tr})
        c.poll_feestate()
        fs = list(ST.read(root, "feestate"))[-1]
        out["feestate_events"], out["feestate_series"] = len(fs["events"]), len(fs["series"])
        out["fee_types"] = sorted({v.get("fee_type") for v in fs["series"].values()} - {None})
        c.completeness()
        out["completeness_rows"] = sum(1 for _ in ST.read(root, "completeness"))
        c.rules_watch()
        out["lip_filings_listed"] = len(list(ST.read(root, "rules"))[-1]["lip_keys"])
        ms = list(ST.read(root, "markets"))[-1]["markets"]
        out["market_fields_ok"] = all(m.get("status") is not None and "close_time" in m for m in ms.values())
        out["http"] = dict(http.stats)
        out["elapsed_s"] = round(time.time() - t0, 1)
        out["req_per_s"] = round(http.stats["requests"] / max(1e-9, time.time() - t0), 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        out["data_deleted"] = True
    print(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    main()
