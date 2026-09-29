"""sha256 of every frozen file (recorded in PREREG_M6_PAPER.md and in the collector's `meta` stream)."""
from __future__ import annotations

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = ("DESIGN.md", "spec.py", "lip.py", "selection.py", "fills.py", "accounting.py", "sim.py", "analysis.py",
          "collector.py", "storage.py", "status.py", "prereg.py", "smoke_check.py", "__init__.py",
          "tests/conftest.py", "tests/test_lip_accounting.py", "tests/test_fills.py", "tests/test_selection.py",
          "tests/test_sim.py", "tests/test_collector_analysis.py")


def manifest_sha256() -> str:
    """One hash over every frozen file's hash (sorted by path)."""
    h = code_hashes()
    return hashlib.sha256("".join(f"{v}  {k}\n" for k, v in sorted(h.items())).encode()).hexdigest()


def code_hashes() -> dict[str, str]:
    return {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in FROZEN}


if __name__ == "__main__":
    for k, v in code_hashes().items():
        print(f"{v}  {k}")
    print(f"{manifest_sha256()}  MANIFEST")
