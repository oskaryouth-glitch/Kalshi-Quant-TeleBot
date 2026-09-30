"""Gate for automated collection.

There are deliberately NO site-specific scrapers in this package. As of the
2026-09-30 review, StorageTreasures, Lockerfox and StorageAuctions.com all
prohibit automated collection in their terms; Bid13's position is unknown.
A collector for a source may only be written once that source's entry in
config/sources.yaml says ``automated_collection: authorized`` (API key or
written permission on file), and every request must go through
``PoliteClient``, which:

  * refuses any source not marked authorized
  * obeys robots.txt
  * rate-limits per host
  * identifies itself honestly (no browser impersonation)
  * never solves CAPTCHAs, logs in with scraped sessions, or retries around
    403/429 responses; those stop the run
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class CollectionNotAuthorized(PermissionError):
    pass


class AccessDenied(RuntimeError):
    """The source said no (403/429/CAPTCHA). Stop; do not retry around it."""


def assert_collection_authorized(sources: dict, source_key: str) -> dict:
    src = sources.get(source_key)
    if src is None:
        raise CollectionNotAuthorized(f"unknown source {source_key!r}")
    status = src.get("automated_collection")
    if status != "authorized":
        raise CollectionNotAuthorized(
            f"automated collection from {source_key!r} is {status!r}; record written permission or "
            "an API agreement in config/sources.yaml (automated_collection: authorized) first"
        )
    return src


@dataclass
class PoliteClient:
    sources: dict
    source_key: str
    user_agent: str  # e.g. "lockerlab-research/0.1 (+contact email)"
    min_interval_s: float = 10.0
    _last: dict = field(default_factory=dict)
    _robots: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert_collection_authorized(self.sources, self.source_key)
        if "mozilla" in self.user_agent.lower():
            raise ValueError("identify as lockerlab, not as a browser")

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
            rp.read()
            self._robots[base] = rp
        return rp.can_fetch(self.user_agent, url)

    def get(self, url: str, timeout: float = 30.0) -> bytes:
        if not self._allowed(url):
            raise CollectionNotAuthorized(f"robots.txt disallows {url}")
        host = urlsplit(url).netloc
        wait = self.min_interval_s - (time.monotonic() - self._last.get(host, -1e9))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise AccessDenied(f"{url}: HTTP {e.code}; stopping") from e
            raise
        finally:
            self._last[host] = time.monotonic()
        return body
