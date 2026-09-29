"""Shared helpers for PRICE TEST 1 (frozen with the pre-registration; see PREREG.md).

Read-only, unauthenticated GETs against the public Kalshi Trade API only. There are no order,
portfolio or authenticated endpoints here.
"""
from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

API = "https://api.elections.kalshi.com/trade-api/v2"
OUT = Path(__file__).resolve().parent / "outputs"
D0, D1 = Decimal(0), Decimal(1)
TAKER_COEF, MAKER_COEF = Decimal("0.07"), Decimal("0.0175")   # fee schedule (structural_arb/sources)
DIRECT_G, NONDIRECT_G = Decimal("0.0001"), Decimal("0.01")
_last = [0.0]


def get(path: str, params: dict | None = None, allow_404: bool = False) -> dict | None:
    """Paced (<= 4 req/s) GET with retry on 429/5xx."""
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(8):
        wait = 0.25 - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404) and allow_404:   # endpoint tier mismatch (live vs historical)
                return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 30))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):   # post-freeze fix: connection resets
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError("GET failed repeatedly: " + url)


def dec(x) -> Decimal | None:
    if x is None or x == "":
        return None
    return Decimal(str(x))


def ts(iso: str) -> int:
    from datetime import datetime
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def ceil_to(x: Decimal, q: Decimal) -> Decimal:
    return (x / q).to_integral_value(rounding=ROUND_CEILING) * q


def fee(price: Decimal, count: Decimal, mult: Decimal, coef: Decimal) -> tuple[Decimal, Decimal]:
    """Fee for ONE fill of `count` contracts bought at `price` (the price paid for the side bought).
    trade_fee = ceil_6dp(M*coef*C*P*(1-P)); net fee for a single on-grid fill = ceil_g(trade_fee)
    (fee-rounding docs; structural_arb bound B2). Returns (direct g=$0.0001, non-direct g=$0.01)."""
    if mult == 0 or count == 0:
        return D0, D0
    tf = ceil_to(mult * coef * count * price * (D1 - price), Decimal("0.000001"))
    return ceil_to(tf, DIRECT_G), ceil_to(tf, NONDIRECT_G)


class SeriesFees:
    """Fee type and multiplier in force at time t, from GET /series/{s} and the series fee-change
    history (GET /series/fee_changes?show_historical=true). Event-level overrides are read from
    the event object where present (fields containing 'fee')."""

    def __init__(self, series: str):
        s = get(f"/series/{series}")["series"]
        self.current = (s.get("fee_type"), dec(s.get("fee_multiplier")))
        h = get("/series/fee_changes", {"series_ticker": series, "show_historical": "true"}) or {}
        rows = h.get("series_fee_change_arr") or h.get("series_fee_changes") or []
        self.changes = sorted((ts(r["scheduled_ts"]), r["fee_type"], dec(r["fee_multiplier"])) for r in rows)

    def at(self, t: int) -> tuple[str, Decimal, bool]:
        """(fee_type, multiplier, exact). exact=False when t precedes the first recorded change
        (the pre-change value is not published): the current value is then used and flagged."""
        past = [c for c in self.changes if c[0] <= t]
        if past:
            return past[-1][1], past[-1][2], True
        return self.current[0], self.current[1], not self.changes


def trades(ticker: str, min_ts: int, max_ts: int) -> list[dict]:
    """All public trades for `ticker` with min_ts <= created_time <= max_ts, live + historical tiers."""
    out = {}
    for path in ("/markets/trades", "/historical/trades"):
        cur = None
        while True:
            p = {"ticker": ticker, "min_ts": min_ts, "max_ts": max_ts, "limit": 1000}
            if cur:
                p["cursor"] = cur
            d = get(path, p, allow_404=True) or {}
            for t in d.get("trades", []):
                out[t["trade_id"]] = t
            cur = d.get("cursor")
            if not cur or not d.get("trades"):
                break
    return sorted(out.values(), key=lambda t: t["created_time"])


def _norm_candle(c: dict) -> dict:
    """Post-freeze data-access fix (RESULTS.md): the live candlestick endpoint names its fields
    `close_dollars` / `volume_fp` / `open_interest_fp`, the historical one `close` / `volume` /
    `open_interest`. Map the live names onto the historical ones; values are unchanged."""
    out = dict(c)
    for k in ("yes_bid", "yes_ask", "price"):
        v = c.get(k)
        if isinstance(v, dict):
            out[k] = {(kk[:-len("_dollars")] if kk.endswith("_dollars") else kk): vv for kk, vv in v.items()}
    for a, b in (("volume_fp", "volume"), ("open_interest_fp", "open_interest")):
        if a in c and b not in c:
            out[b] = c[a]
    return out


def candles(series: str, ticker: str, start_ts: int, end_ts: int, interval: int = 60) -> list[dict]:
    """Candlesticks (period `interval` minutes) with end_period_ts in [start_ts, end_ts]. Tries the
    live endpoint, then the historical one; chunks long windows."""
    out = {}
    step = interval * 60 * 4000
    a = start_ts
    while a <= end_ts:
        b = min(end_ts, a + step)
        for path in (f"/series/{series}/markets/{ticker}/candlesticks", f"/historical/markets/{ticker}/candlesticks"):
            d = get(path, {"start_ts": a, "end_ts": b, "period_interval": interval}, allow_404=True)
            if d and d.get("candlesticks"):
                for c in d["candlesticks"]:
                    out[c["end_period_ts"]] = _norm_candle(c)
                break
        a = b + 1
    return [out[k] for k in sorted(out)]


def save(name: str, obj) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, indent=1, default=str))
    return p
