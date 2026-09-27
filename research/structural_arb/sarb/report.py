"""Aggregate the research log: counts by relationship x status x rejection reason, and edge
distributions. Negative results are reported with the same prominence as positive ones."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal

from . import research_log


def summarize(records) -> dict:
    by_status: Counter = Counter()
    by_rel_status: Counter = Counter()
    reasons: Counter = Counter()
    raw_vs_edge = defaultdict(list)
    for r in records:
        by_status[r["status"]] += 1
        by_rel_status[(r["relationship"], r["status"])] += 1
        for reason in r.get("reasons", []):
            reasons[(r["relationship"], reason)] += 1
        if r.get("raw_inconsistency") is not None:
            raw_vs_edge[r["relationship"]].append(
                (Decimal(r["raw_inconsistency"]), Decimal(r["edge"]) if r.get("edge") is not None else None))
    killed_by_costs = {
        rel: sum(1 for raw, edge in pairs if raw > 0 and edge is not None and edge <= 0)
        for rel, pairs in raw_vs_edge.items()
    }
    return {"by_status": dict(by_status), "by_relationship_status": {f"{a}|{b}": n for (a, b), n in by_rel_status.items()},
            "reasons": {f"{a}|{b}": n for (a, b), n in reasons.most_common()},
            "raw_positive_but_edge_nonpositive": killed_by_costs}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log_path")
    a = ap.parse_args(argv)
    s = summarize(research_log.read(a.log_path))
    for k, v in s.items():
        print(f"== {k}")
        for kk, vv in (v.items() if isinstance(v, dict) else []):
            print(f"  {kk}: {vv}")


if __name__ == "__main__":
    main()
