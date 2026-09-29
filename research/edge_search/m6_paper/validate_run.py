"""Operational check of a VALIDATION data directory (no episodes, rewards or P&L; Replay refuses this data).

Reports: meta records (validation starts/restarts, restored tracking), request/429/error counts, recorded
collection gaps, per-stream record counts with a full gzip integrity read, book-poll cadence, clock skew
between local receive times and exchange trade timestamps, and whether every record's code manifest
matches the frozen one.

usage: python -m m6_paper.validate_run VALIDATION_DIR EXPECTED_MANIFEST
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import statistics
import sys

from . import prereg
from . import selection as SEL
from . import storage as ST

NS = 1_000_000_000


def main(root: str, expected: str) -> dict:
    out: dict = {"dir": root}
    metas = list(ST.read(root, "meta"))
    out["meta_kinds"] = [m.get("kind") for m in metas]
    out["all_validation"] = all(k == "validation" for k in out["meta_kinds"])
    out["restarts"] = len(metas) - 1
    out["restored_tracked_on_restart"] = [m.get("restored_tracked") for m in metas[1:]]
    man = {prereg.hashlib.sha256("".join(f"{v}  {k}\n" for k, v in sorted(m.get("code_sha256", {}).items())).encode()).hexdigest()
           for m in metas}
    out["meta_manifest_matches"] = man == {expected}
    out["disk_code_manifest_matches"] = prereg.verify(expected)
    integrity, counts = True, {}
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl.gz"))):
        name = os.path.basename(p).split("_")[0]
        try:
            with gzip.open(p, "rt") as fh:
                n = sum(1 for line in fh if json.loads(line))
        except Exception as e:                                      # noqa: BLE001
            integrity, n = False, f"CORRUPT: {e!r}"
        counts[name] = counts.get(name, 0) + n if isinstance(n, int) else n
    out["records_by_stream"], out["gzip_integrity_ok"] = counts, integrity
    ops = list(ST.read(root, "ops"))
    hb = [o for o in ops if "requests" in o]
    if hb:
        last = hb[-1]
        out["requests"], out["http_429"], out["errors"] = last["requests"], last["http_429"], last["errors"]
        out["rate_429"] = round(last["http_429"] / max(1, last["requests"]), 4)
    out["loop_exceptions"] = [o["error"] for o in ops if "error" in o][:10]
    out["collection_gaps"] = [{k: o[k] for k in ("reason", "start_ns", "end_ns")} | {"s": (o["end_ns"] - o["start_ns"]) / NS}
                              for o in ops if o.get("kind") == "collection_gap"]
    polls = [r["t_ns"] for r in ST.read(root, "books")]
    if len(polls) > 2:
        gaps = [(b - a) / NS for a, b in zip(polls, polls[1:])]
        out["book_polls"] = len(polls)
        out["book_poll_interval_s"] = {"mean": round(statistics.mean(gaps), 2), "max": round(max(gaps), 1)}
    lags = []
    for rec in ST.read(root, "trades"):
        for tr in rec["trades"]:
            lags.append((rec["t_ns"] - SEL.ts_ns(tr["created_time"])) / NS)
    if lags:
        out["trade_receive_minus_exchange_s"] = {"min": round(min(lags), 2), "median": round(statistics.median(lags), 2)}
        out["clock_ok"] = min(lags) > -2.0          # a local clock behind the exchange would show negative lags
    print(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":                                        # pragma: no cover
    main(sys.argv[1], sys.argv[2])
