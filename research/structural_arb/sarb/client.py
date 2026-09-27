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
    """Token bucket: sustained `per_second`, bursts up to `burst` requests (Kalshi documents
    token buckets with burst capacity; unauthenticated limits are undocumented, so we stay far
    below the documented Basic authenticated read budget of 20 req/s)."""

    def __init__(self, per_second: float, burst: int = 1):
        self._rate = per_second
        self._cap = max(1.0, float(burst))
        self._tokens = self._cap
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self._cap, self._tokens + (now - self._last) * self._rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                time.sleep((1 - self._tokens) / self._rate)


class RequestStats:
    """Per-endpoint-class request counters and latencies (ops audit)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.count: dict = {}
        self.latency_ms: dict = {}

    @staticmethod
    def kind(path: str) -> str:
        if path.endswith("/orderbook"):
            return "orderbook"
        parts = path.strip("/").split("/")
        return parts[0] + ("/*" if len(parts) > 1 and parts[1] not in ("fee_changes", "status") else
                           ("/" + parts[1] if len(parts) > 1 else ""))

    def add(self, path: str, status: int, latency_ns: int):
        k = self.kind(path)
        with self.lock:
            self.count[(k, status)] = self.count.get((k, status), 0) + 1
            self.latency_ms.setdefault(k, []).append(latency_ns / 1e6)

    def snapshot_and_reset(self) -> dict:
        with self.lock:
            out = {"requests": {f"{k}|{st}": n for (k, st), n in sorted(self.count.items())}, "latency_ms": {}}
            for k, v in self.latency_ms.items():
                v = sorted(v)
                out["latency_ms"][k] = {"n": len(v), "p50": round(v[len(v) // 2], 1),
                                        "p95": round(v[min(len(v) - 1, int(len(v) * 0.95))], 1),
                                        "max": round(v[-1], 1)}
            self.reset()
            return out


class PublicClient:
    def __init__(self, base_url: str = config.PUBLIC_BASE_URL, session: requests.Session | None = None,
                 per_second: float = config.MAX_REQUESTS_PER_SECOND, timeout_s: float = 10.0,
                 burst: int = config.MAX_REQUEST_BURST):
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        # Strip anything a caller may have attached to a shared session.
        for h in list(self._session.headers):
            if h.lower() in _FORBIDDEN_HEADER_NAMES:
                del self._session.headers[h]
        self._limiter = _RateLimiter(per_second, burst)
        self.stats = RequestStats()
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
        self.stats.add(path, resp.status_code, recv_mono - sent_mono)
        h = getattr(resp, "headers", {}) or {}
        hdrs = tuple((k, h.get(k)) for k in ("x-cache", "age", "date") if h.get(k) is not None)
        return TimedResponse(path, params, resp.status_code, body, sent_utc, recv_utc, sent_mono, recv_mono, hdrs)

    def get_retry(self, path: str, params: dict | None = None, attempts: int = 4) -> TimedResponse:
        """For discovery/screening pages only. Leg re-fetches never retry: a failed leg is
        recorded as unavailable and the candidate is rejected."""
        r, delay = None, 0.5
        for _ in range(attempts):
            try:
                r = self.get(path, params)
            except requests.RequestException:
                r = None
            if r is not None and r.status == 200:
                return r
            time.sleep(delay)
            delay *= 2
        if r is None:
            raise requests.ConnectionError(f"GET {path} failed after {attempts} attempts")
        return r

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
