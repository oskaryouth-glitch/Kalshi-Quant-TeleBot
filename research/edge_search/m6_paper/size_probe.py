"""Storage-growth probe (pre-deployment; data deleted; no episodes, rewards or P&L computed).

Runs the real collector code at the frozen request rate for one epoch plus `--minutes` of book/trade
polling into a temporary directory, measures compressed bytes per stream, extrapolates daily growth for
the tracked-set sizes given, and deletes the directory.

usage: python -m m6_paper.size_probe [--minutes 5]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import shutil
import tempfile
import time

from . import collector as C
from . import spec as S
from . import storage as ST


def main(minutes: float = 5.0) -> dict:
    root = tempfile.mkdtemp(prefix="m6_size_validation_")
    out = {}
    try:
        http = C.Http()
        c = C.Collector(http, ST.Writer(root), rng=random.Random(1))
        t0 = time.time()
        c.epoch(C.epoch_due(None, time.time_ns()))
        out["epoch_s"] = round(time.time() - t0, 1)
        out["tracked"] = len(c.tracked)
        polls, nxt_b, nxt_t = 0, 0.0, 0.0
        t1 = time.time()
        while time.time() - t1 < minutes * 60:
            now = time.monotonic()
            if now >= nxt_b:
                c.poll_books(); polls += 1
                nxt_b = now + c.rng.expovariate(1.0 / S.BOOK_POLL_MEAN_S)
            if now >= nxt_t:
                c.poll_trades(); nxt_t = now + S.TRADES_POLL_S
            c.poll_new_fees()
            time.sleep(0.2)
        span = time.time() - t1
        sizes = {}
        for p in glob.glob(os.path.join(root, "*.jsonl.gz")):
            k = os.path.basename(p).split("_")[0]
            sizes[k] = sizes.get(k, 0) + os.path.getsize(p)
        out.update(book_polls=polls, poll_span_s=round(span, 1), bytes_by_stream=sizes, http=dict(http.stats),
                   rate_429=round(http.stats["http_429"] / max(1, http.stats["requests"]), 4))
        per_day_books = sizes.get("books", 0) / span * 86400 / max(1, out["tracked"])      # per tracked market-day
        per_day_trades = sizes.get("trades", 0) / span * 86400 / max(1, out["tracked"])
        epoch_bytes = sizes.get("epoch", 0)
        est = {}
        for n in (100, 300, 600):
            est[n] = round((per_day_books + per_day_trades) * n + 4 * epoch_bytes + 5e6, 0)   # +5 MB/day other streams
        out["bytes_per_tracked_market_day"] = {"books": round(per_day_books), "trades": round(per_day_trades)}
        out["epoch_record_bytes"] = epoch_bytes
        out["estimated_bytes_per_day_by_tracked_markets"] = est
        out["estimated_GB_90_days_at_600"] = round(est[600] * 90 / 1e9, 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        out["data_deleted"] = True
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=5.0)
    main(ap.parse_args().minutes)
