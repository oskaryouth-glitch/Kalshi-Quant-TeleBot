"""In-flight monitor: completed-episode COUNTS per arm and variant, arm checkpoint state and data-integrity
checks. It never computes or prints rewards, P&L or any profitability (DESIGN §10 v2, no peeking).

usage: python -m m6_paper.status DATA_DIR
"""
from __future__ import annotations

import json
import sys

from . import sim as SIM
from . import spec as S
from . import storage as ST

NS = SIM.NS


def integrity(root: str) -> dict:
    """Cumulative collector downtime (heartbeat gaps > 5 min) and the longest trade-feed silence."""
    hb = [r["t_ns"] for r in ST.read(root, "ops") if "requests" in r]
    down = sum(b - a for a, b in zip(hb, hb[1:]) if b - a > 300 * NS)
    polls = [r.get("trades_polls") for r in ST.read(root, "ops") if "trades_polls" in r]
    times = [r["t_ns"] for r in ST.read(root, "ops") if "trades_polls" in r]
    longest, start = 0, None
    for (t, p), (t2, p2) in zip(zip(times, polls), zip(times[1:], polls[1:])):
        if p2 == p:
            start = t if start is None else start
            longest = max(longest, t2 - start)
        else:
            start = None
    return {"downtime_s": down / NS, "longest_trade_feed_silence_s": longest / NS,
            "INVALID": down > S.INVALID_DOWNTIME_S * NS or longest > S.INVALID_TRADE_FEED_LOSS_S * NS}


def main(root: str) -> dict:
    rp = SIM.Replay(root).run()
    out = {"data_start_ns": rp.start_ns, "day0_ns": rp.day0, "last_event_ns": rp.last_t,
           "day": (rp.last_t - rp.day0) / SIM.DAY, "completed_episodes": rp.counts(),
           "arms": {a: {k: v for k, v in s.items() if k in ("verdict_state", "decided_ns", "decision_day", "counts")}
                    for a, s in rp.arm_status.items()},
           "tracking_breaches": len(rp.world.breaches), "integrity": integrity(root)}
    print(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":                                    # pragma: no cover
    main(sys.argv[1])
