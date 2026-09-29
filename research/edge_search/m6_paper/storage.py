"""Append-only gzip JSONL streams, one file per stream per UTC receive day: <dir>/<stream>_<YYYYMMDD>.jsonl.gz.

Every record carries `t_ns`: local receive time, UTC nanoseconds. Streams:
  meta, programs, epoch, tracked, books, trades, markets, feestate, completeness, rules, ops
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import os
from decimal import Decimal

STREAMS = ("meta", "programs", "epoch", "tracked", "books", "trades", "markets", "feestate", "completeness", "rules", "ops")


def _default(o):
    if isinstance(o, Decimal):
        return str(o)
    raise TypeError(type(o))


def day_of(t_ns: int) -> str:
    return dt.datetime.fromtimestamp(t_ns / 1e9, dt.timezone.utc).strftime("%Y%m%d")


class Writer:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def write(self, stream: str, rec: dict) -> None:
        assert stream in STREAMS and "t_ns" in rec
        with gzip.open(os.path.join(self.root, f"{stream}_{day_of(rec['t_ns'])}.jsonl.gz"), "at", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=_default) + "\n")


def days(root: str, stream: str) -> list[str]:
    return sorted(os.path.basename(p)[len(stream) + 1:len(stream) + 9]
                  for p in glob.glob(os.path.join(root, f"{stream}_*.jsonl.gz")))


def read_day(root: str, stream: str, day: str):
    p = os.path.join(root, f"{stream}_{day}.jsonl.gz")
    if not os.path.exists(p):
        return
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def read(root: str, stream: str):
    for d in days(root, stream):
        yield from read_day(root, stream, d)
