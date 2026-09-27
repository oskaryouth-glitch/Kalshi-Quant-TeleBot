"""Read-only, unauthenticated Kalshi public-data client.

Safety properties (enforced by tests/test_client.py):
  * only HTTP GET is ever issued; there is no method for any other verb;
  * only an allowlist of public market-data paths may be requested;
  * no Authorization / API-key headers are ever sent, and no credentials are read;
  * every response carries local send/receive timestamps (UTC ns and monotonic ns).
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests

from . import config

_ALLOWED_PATHS = (
    re.compile(r"^/exchange/status$"),
    re.compile(r"^/series$"),
    re.compile(r"^/series/fee_changes$"),
    re.compile(r"^/series/[A-Za-z0-9._-]+$"),
    re.compile(r"^/events$"),
    re.compile(r"^/events/[A-Za-z0-9._-]+$"),
    re.compile(r"^/markets$"),
    re.compile(r"^/markets/[A-Za-z0-9._-]+$"),
    re.compile(r"^/markets/[A-Za-z0-9._-]+/orderbook$"),
)

_FORBIDDEN_HEADER_NAMES = {"authorization", "kalshi-access-key", "kalshi-access-signature",
                           "kalshi-access-timestamp"}


class ForbiddenRequest(RuntimeError):
    pass


@dataclass(frozen=True)
class TimedResponse:
    path: str
    params: dict
    status: int
    body: Any
    sent_utc_ns: int
    recv_utc_ns: int
    sent_mono_ns: int
    recv_mono_ns: int
    headers: tuple = ()          # (x-cache, age, date) as served -- CDN staleness audit

    @property
    def latency_ns(self) -> int:
        return self.recv_mono_ns - self.sent_mono_ns


def check_path(path: str) -> None:
    if not any(p.match(path) for p in _ALLOWED_PATHS):
        raise ForbiddenRequest(f"path not on public read-only allowlist: {path!r}")


class _RateLimiter:
    def __init__(self, per_second: float):
        self._interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
                now = self._next
            self._next = now + self._interval


class PublicClient:
    def __init__(self, base_url: str = config.PUBLIC_BASE_URL, session: requests.Session | None = None,
                 per_second: float = config.MAX_REQUESTS_PER_SECOND, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        # Strip anything a caller may have attached to a shared session.
        for h in list(self._session.headers):
            if h.lower() in _FORBIDDEN_HEADER_NAMES:
                del self._session.headers[h]
        self._limiter = _RateLimiter(per_second)
        self._timeout = timeout_s

    def get(self, path: str, params: dict | None = None) -> TimedResponse:
        check_path(path)
        params = dict(params or {})
        self._limiter.wait()
        sent_utc, sent_mono = time.time_ns(), time.monotonic_ns()
        resp = self._session.request("GET", self.base_url + path, params=params,
                                     headers={"Accept": "application/json"}, timeout=self._timeout)
        recv_utc, recv_mono = time.time_ns(), time.monotonic_ns()
        try:
            body = resp.json()
        except ValueError:
            body = {"_non_json": resp.text[:2000]}
        h = getattr(resp, "headers", {}) or {}
        hdrs = tuple((k, h.get(k)) for k in ("x-cache", "age", "date") if h.get(k) is not None)
        return TimedResponse(path, params, resp.status_code, body, sent_utc, recv_utc, sent_mono, recv_mono, hdrs)

    # --- convenience wrappers (all GET) ---
    def exchange_status(self) -> TimedResponse:
        return self.get("/exchange/status")

    def series(self, series_ticker: str) -> TimedResponse:
        return self.get(f"/series/{series_ticker}")

    def fee_changes(self, **params) -> TimedResponse:
        return self.get("/series/fee_changes", params)

    def market(self, ticker: str) -> TimedResponse:
        return self.get(f"/markets/{ticker}")

    def orderbook(self, ticker: str, depth: int | None = None) -> TimedResponse:
        return self.get(f"/markets/{ticker}/orderbook", {"depth": depth} if depth else None)

    def iter_events(self, status: str = "open", with_nested_markets: bool = True, limit: int = 200,
                    max_pages: int = 1000, **extra):
        """Yield TimedResponse pages of /events following the cursor."""
        cursor = None
        for _ in range(max_pages):
            params = {"status": status, "limit": limit,
                      "with_nested_markets": str(with_nested_markets).lower(), **extra}
            if cursor:
                params["cursor"] = cursor
            page = self.get("/events", params)
            yield page
            cursor = (page.body or {}).get("cursor") if isinstance(page.body, dict) else None
            if page.status != 200 or not cursor:
                return
