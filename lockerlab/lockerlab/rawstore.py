"""Content-addressed, write-once storage for raw evidence (captures, photos).

Files are stored at ``<root>/<sha[:2]>/<sha>`` and made read-only. Because the
path is the hash, a file can't be silently replaced: ``get`` re-verifies it.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path


class CorruptEvidence(RuntimeError):
    pass


class RawStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, sha: str) -> Path:
        return self.root / sha[:2] / sha

    def put(self, data: bytes) -> tuple[str, str]:
        """Store bytes; return (sha256, path relative to root). Idempotent."""
        sha = hashlib.sha256(data).hexdigest()
        dest = self._path(sha)
        if dest.exists():
            self.get(sha)  # verify the existing copy is intact
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dest.parent)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                os.replace(tmp, dest)
            except BaseException:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
            os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return sha, str(dest.relative_to(self.root))

    def get(self, sha: str) -> bytes:
        data = self._path(sha).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise CorruptEvidence(f"raw evidence {sha} fails its hash check")
        return data
