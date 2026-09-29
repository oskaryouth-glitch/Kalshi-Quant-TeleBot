"""M6 paper experiment: frozen inference and decision rules (DESIGN §10 v2).

NO PEEKING (enforced here): an arm's profitability is computed only after the arm has reached its
formal checkpoint (or day 60) AND its settlement cutoff (checkpoint + 30 days) has passed in the data.
Before that, `decide` raises; use status.py for counts. Ranked arms (P30, P100, P200) and the random arm
(U) are evaluated and reported separately and never pooled.

Inference: cluster bootstrap over `event_ticker` clusters of the worst variant's decision set,
10,000 resamples, random.Random(20261001), clusters sorted by name before resampling;
LB95 = the 500th smallest resampled NET (order statistic ceil(0.05 * 10,000)).
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from decimal import Decimal as D

from . import sim as SIM
from . import spec as S

DAY = SIM.DAY


class NotYet(RuntimeError):
    pass


def bootstrap_lb95(nets: list[tuple[str, D]]) -> D:
    clusters: dict[str, D] = defaultdict(D)
    for ev, net in nets:
        clusters[ev] += net
    names = sorted(clusters)
    vals = [clusters[n] for n in names]
    rng = random.Random(S.BOOT_SEED)
    sums = sorted(sum((vals[rng.randrange(len(vals))] for _ in vals), D(0)) for _ in range(S.BOOT_N))
    return sums[math.ceil(0.05 * S.BOOT_N) - 1]


def verdict(net: D, lb: D, net_wo_best: D, n: int) -> str:
    if n < S.MIN_EPISODES:
        return "INSUFFICIENT_EVIDENCE"
    if net > 0 and lb > 0 and net_wo_best > 0:
        return "SURVIVE"
    if net <= 0:
        return "KILL"
    return "INCONCLUSIVE"


def decide(root: str, arm: str, data_end_ns: int | None = None) -> dict:
    """Formal result for one arm. Raises NotYet unless its checkpoint and settlement cutoff have passed."""
    rp = SIM.Replay(root).run(data_end_ns)
    st = rp.arm_status[arm]
    if st["decided_ns"] is None:
        raise NotYet(f"{arm}: formal checkpoint not reached; counts only (status.py)")
    if st["verdict_state"] == "INSUFFICIENT_EVIDENCE":
        return {"arm": arm, "verdict": "INSUFFICIENT_EVIDENCE", "decision_day": S.MAX_DAY, "counts": st.get("counts")}
    cutoff = st["decided_ns"] + S.SETTLEMENT_CUTOFF_DAYS * DAY
    if rp.last_t < cutoff:
        raise NotYet(f"{arm}: settlement cutoff {cutoff} not yet in the data")
    rp = SIM.Replay(root).run(cutoff)                  # valuation state exactly at the cutoff
    ledger = {(r["variant"], r["eid"]): r for r in SIM.episode_ledger(rp, cutoff)}
    per = {}
    for v in S.VARIANTS:
        rows = [ledger[(v, eid)] for eid in st["decision_sets"][v]]
        per[v] = {"n": len(rows), "net": sum((r["net"] for r in rows), D(0)), "rows": rows}
    worst = min(S.VARIANTS, key=lambda v: (per[v]["net"], S.VARIANTS.index(v)))
    rows = per[worst]["rows"]
    net = per[worst]["net"]
    lb = bootstrap_lb95([(r["event_ticker"], r["net"]) for r in rows])
    best = max((r["net"] for r in rows), default=D(0))
    breach_eids = [r["eid"] for r in rows if not r["tracked_ok"]]
    out = {"arm": arm, "TRACKING_BREACHES": len(breach_eids), "tracking_breach_episodes": breach_eids,
           "decision_day": st["decision_day"], "worst_variant": worst,
           "net_by_variant": {v: str(per[v]["net"]) for v in S.VARIANTS}, "n_by_variant": {v: per[v]["n"] for v in S.VARIANTS},
           "net": str(net), "lb95": str(lb), "net_without_best": str(net - best),
           "reward_conservative": str(sum((r["reward_conservative"] for r in rows), D(0))),
           "reward_primary": str(sum((r["reward_primary"] for r in rows), D(0))),
           "trading_pnl": str(sum((r["trading_pnl"] for r in rows), D(0))),
           "trading_pnl_nondirect_fees": str(sum((r["trading_pnl_nondirect"] for r in rows), D(0))),
           "fees": str(sum((r["fees"] for r in rows), D(0))), "fills": sum(r["n_fills"] for r in rows)}
    if arm == "U":
        out["verdict"] = "REPORTED_ONLY"
        out["mean_net_per_episode"] = str(net / len(rows)) if rows else None
    else:
        out["verdict"] = verdict(net, lb, net - best, len(rows))
        acct = rp.states[worst].accounts[arm]
        span = max(1, (rp.last_t - rp.start_ns))
        avg_cap = acct.cap_integral / span
        out["capital"] = {"average_committed": str(avg_cap), "max_committed": str(acct.cap_max), "K": str(S.ACCOUNTS[arm]),
                          "capital_cost_4pct_sensitivity": str(avg_cap * S.CAPITAL_COST_APR * D(span) / D(365 * DAY))}
    return out


def m6_overall(results: dict[str, dict]) -> str:
    ranked = [results[a]["verdict"] for a in S.ACCOUNTS]
    if "SURVIVE" in ranked:
        return "SURVIVE"
    if all(v == "KILL" for v in ranked):
        return "KILL"
    return "INCONCLUSIVE"
