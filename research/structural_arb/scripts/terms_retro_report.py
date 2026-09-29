"""Report (never rewrite) how recorded lock-like candidates relabel under amendment-aware terms verification.

usage: python scripts/terms_retro_report.py DATA_DIR [DATA_DIR ...] [--grace-days N] [--ledger OUT.jsonl]

Lists the public regulatory bucket and GET /series once (public, unauthenticated), then prints, per data
directory, recorded status -> retro status counts with reasons (sarb/terms_retro.py). Data files are
only read. With --ledger, also writes one JSON line per recorded lock-like candidate (relabelled or
not), bound to its raw record by the sha256 of the original line, so the relabel is an overlay on
the unchanged raw data and its provenance.
"""
from __future__ import annotations

import argparse
import collections
import glob
import gzip
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarb import filings as FL          # noqa: E402
from sarb import terms_retro as TR      # noqa: E402
from sarb.client import PublicClient    # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--grace-days", type=float, default=0.0)
    ap.add_argument("--ledger", default=None)
    a = ap.parse_args(argv)
    bucket = [f for pre in FL.PREFIXES for f in FL.http_list(pre)]
    r = PublicClient().get_retry("/series", {"limit": 1000})
    if r.status != 200:
        raise SystemExit(f"/series HTTP {r.status}")
    series_terms = {s["ticker"]: s.get("contract_terms_url") for s in r.body.get("series", [])}
    out, ledger = {}, []
    for d in a.dirs:
        c = collections.Counter()
        for f in sorted(glob.glob(os.path.join(d, "sarb_candidates_*.jsonl.gz"))):
            with gzip.open(f, "rt") as fh:
                for n, line in enumerate(fh, 1):
                    rec = json.loads(line)
                    new, why = TR.retro_status(rec, bucket, series_terms, a.grace_days * 86400)
                    if rec.get("status") in TR.LOCK_LIKE:
                        c[f"{rec['status']} -> {new} ({why or 'stands'}) [{rec.get('relationship')}]"] += 1
                        ledger.append({"data_dir": os.path.basename(os.path.normpath(d)), "file": os.path.basename(f),
                                       "line": n, "raw_line_sha256": hashlib.sha256(line.encode()).hexdigest(),
                                       "candidate_id": rec.get("candidate_id"), "logged_utc_ns": rec.get("logged_utc_ns"),
                                       "config_version": rec.get("config_version"), "relationship": rec.get("relationship"),
                                       "event_tickers": rec.get("event_tickers"), "original_status": rec.get("status"),
                                       "retro_status": new, "reason": why})
        out[d] = dict(sorted(c.items()))
    print(json.dumps(out, indent=1))
    if a.ledger:
        with open(a.ledger, "w") as fh:
            for row in ledger:
                fh.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
