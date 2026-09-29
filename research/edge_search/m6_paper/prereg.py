"""sha256 of every frozen file (recorded in PREREG_M6_PAPER.md and in the collector's `meta` stream)."""
from __future__ import annotations

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = ("DESIGN.md", "INTERPRETATIONS.md", "deploy/README.md", "spec.py", "lip.py", "selection.py", "fills.py", "accounting.py", "sim.py", "analysis.py",
          "collector.py", "storage.py", "status.py", "prereg.py", "smoke_check.py", "size_probe.py", "validate_run.py",
          "__init__.py", "deploy/m6-paper-collector.service", "deploy/preflight.sh", "deploy/install.sh", "deploy/validate.sh",
          "tests/conftest.py", "tests/test_lip_accounting.py", "tests/test_fills.py", "tests/test_selection.py",
          "tests/test_sim.py", "tests/test_collector_analysis.py", "tests/test_v3_changes.py",
          "tests/test_v4_amendments.py")


def manifest_sha256() -> str:
    """One hash over every frozen file's hash (sorted by path)."""
    h = code_hashes()
    return hashlib.sha256("".join(f"{v}  {k}\n" for k, v in sorted(h.items())).encode()).hexdigest()


def code_hashes() -> dict[str, str]:
    return {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in FROZEN}


def verify(expected_manifest: str) -> bool:
    """True iff the files on disk hash to the frozen manifest (used by the deployment scripts)."""
    return manifest_sha256() == expected_manifest


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--verify":
        ok = verify(sys.argv[2])
        print(("MANIFEST OK " if ok else "MANIFEST MISMATCH ") + manifest_sha256())
        raise SystemExit(0 if ok else 1)
    for k, v in code_hashes().items():
        print(f"{v}  {k}")
    print(f"{manifest_sha256()}  MANIFEST")
