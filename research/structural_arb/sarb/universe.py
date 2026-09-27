"""Universe assembly: markets -> semantics -> families -> structural templates, plus fee state.

Pure data plumbing. No relationship math lives here (see relationships.py / payoff.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal

from . import fees as FEES
from . import relationships as R
from . import semantics as SEM
from .evaluator import MarketMeta
from .payoff import Position


def iso_utc(ns: int) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(ns / 1e9, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_ns(s: str | None) -> int | None:
    import datetime as dt
    if not s:
        return None
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1e9)


def _dec(x) -> Decimal | None:
    try:
        d = Decimal(str(x))
    except Exception:
        return None
    return d


# ------------------------------------------------------------------------------ fee ledger

class FeeLedger:
    """GET /events/fee_changes returns ONLY future-scheduled overrides (verified 2026-09-27),
    so an override disappears from the API once it takes effect. The ledger stores every
    change ever observed. Series known to use event overrides get a conservative floor on M:
    the largest override multiplier ever observed in that series. This means an in-force
    override we never saw cannot make us understate fees."""

    def __init__(self, path: str):
        self.path = path
        self.changes: dict[str, dict] = {}
        if os.path.exists(path):
            with open(path) as fh:
                self.changes = json.load(fh).get("changes", {})

    def update(self, rows: list[dict], seen_iso: str) -> int:
        new = 0
        for r in rows:
            cid = r.get("id") or hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
            if cid not in self.changes:
                self.changes[cid] = {**r, "_first_seen": seen_iso}
                new += 1
        if new:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump({"changes": self.changes}, fh)
            os.replace(tmp, self.path)
        return new

    def event_changes(self) -> list[dict]:
        return list(self.changes.values())

    def series_override_floor(self, series: str) -> Decimal | None:
        ms = [Decimal(str(c["fee_multiplier_override"])) for c in self.changes.values()
              if c.get("series_ticker") == series and c.get("fee_multiplier_override") is not None]
        return max(ms) if ms else None


def resolve_leg_fee(series_ticker: str, event_ticker: str, at_iso: str, series_body: dict | None,
                    series_changes: list[dict], ledger: FeeLedger):
    try:
        rf = FEES.resolve_fee(series_ticker, event_ticker, at_iso, series_body, series_changes, ledger.event_changes())
    except FEES.UnsupportedFee as e:
        return e
    floor = ledger.series_override_floor(series_ticker)
    if floor is not None and floor > rf.multiplier:
        rf = FEES.ResolvedFee(rf.fee_type, floor, rf.source + f"+ledger_series_override_floor:{floor}")
    return rf


# ------------------------------------------------------------------------------ universe

@dataclass
class Universe:
    specs: dict[str, SEM.MarketSpec] = field(default_factory=dict)
    raw: dict[str, tuple[dict, dict]] = field(default_factory=dict)       # ticker -> (event, market)
    families: dict[str, R.Family] = field(default_factory=dict)
    structs: list[R.Structural] = field(default_factory=list)            # numeric (lazy) + categorical R1
    categorical: dict[str, list[str]] = field(default_factory=dict)       # MECNET event -> tickers
    reject_counts: dict[str, int] = field(default_factory=dict)
    built_utc_ns: int = 0
    build_seconds: float = 0.0

    def meta(self, ticker: str, fetched_mono_ns: int, market_override: dict | None = None) -> MarketMeta:
        ev, m = self.raw[ticker]
        m = market_override or m
        lp = _dec(m.get("last_price_dollars"))
        return MarketMeta(ticker, ev.get("series_ticker", ""), ev["event_ticker"], m.get("status", ""),
                          parse_iso_ns(m.get("close_time")), lp if lp and lp > 0 else None,
                          parse_iso_ns(m.get("latest_expiration_time")), fetched_mono_ns)

    def summary_ask(self, pos: Position) -> Decimal | None:
        """Screening ONLY (never used for evaluation): /events summary ask for the side."""
        m = self.raw[pos.ticker][1]
        a = _dec(m.get("yes_ask_dollars" if pos.side == "yes" else "no_ask_dollars"))
        return a if a is not None and 0 < a < 1 else None


class TemplateCache:
    """Caches parsed specs (by rules/strike fingerprint), Family objects and their templates
    (by family signature), so a rebuild only reparses what changed."""

    def __init__(self):
        self._c: dict[str, tuple] = {}
        self._spec: dict[str, tuple[str, SEM.MarketSpec]] = {}

    def spec(self, ev: dict, m: dict, series: dict | None, terms_sha: dict[str, str]) -> SEM.MarketSpec:
        s = (series or {}).get("series", series or {})
        fp_src = [m.get(k) for k in ("rules_primary", "rules_secondary", "strike_type", "floor_strike", "cap_strike",
                                     "custom_strike", "latest_expiration_time", "market_type",
                                     "notional_value_dollars")]
        url = s.get("contract_terms_url")
        fp_src += [ev.get("event_ticker"), ev.get("series_ticker"), ev.get("settlement_sources"), url,
                   terms_sha.get(url) if url else None]
        fp = hashlib.sha256(json.dumps(fp_src, sort_keys=True, default=str).encode()).hexdigest()
        hit = self._spec.get(m["ticker"])
        if hit and hit[0] == fp:
            return hit[1]
        sp = SEM.build_market_spec(ev, m, series, terms_sha)
        self._spec[m["ticker"]] = (fp, sp)
        return sp

    def family(self, sig: str, specs: list[SEM.MarketSpec]):
        if sig not in self._c:
            fam = R.Family(specs)
            self._c[sig] = (fam, R.numeric_family_templates(fam, lazy=True, include_pairs=False))
        return self._c[sig]

    def prune(self, live_sigs: set[str], live_tickers: set[str]):
        for k in list(self._c):
            if k not in live_sigs:
                del self._c[k]
        for t in list(self._spec):
            if t not in live_tickers:
                del self._spec[t]


def _family_signature(specs: list[SEM.MarketSpec]) -> str:
    key = [(s.ticker, id(s)) for s in sorted(specs, key=lambda s: s.ticker)]   # specs are cached by fingerprint
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()


def build_universe(events: list[dict], series_by_ticker: dict[str, dict], terms_sha: dict[str, str],
                   cache: TemplateCache) -> Universe:
    t0 = time.monotonic()
    u = Universe(built_utc_ns=time.time_ns())
    for ev in events:
        for m in ev.get("markets") or []:
            if m.get("status") != "active":
                continue
            u.raw[m["ticker"]] = (ev, m)
            sp = cache.spec(ev, m, series_by_ticker.get(ev.get("series_ticker")), terms_sha)
            u.specs[m["ticker"]] = sp
            u.reject_counts[sp.reject or "OK"] = u.reject_counts.get(sp.reject or "OK", 0) + 1
    live = set()
    for key, fs in SEM.group_families(list(u.specs.values())).items():
        if len(fs) < 2:
            continue
        sig = _family_signature(fs)
        live.add(sig)
        fam, templates = cache.family(sig, fs)
        u.families[key] = fam
        u.structs.extend(templates)
    # categorical MECNET events: every active market (at most one YES by the API definition),
    # unless the whole event is already a single numeric family
    for ev in events:
        if not ev.get("mutually_exclusive"):
            continue
        ts = sorted(m["ticker"] for m in ev.get("markets") or [] if m.get("status") == "active")
        if len(ts) < 2:
            continue
        fam_keys = {u.specs[t].family_key for t in ts if u.specs[t].reject is None}
        if len(fam_keys) == 1 and all(u.specs[t].reject is None for t in ts):
            continue
        u.categorical[ev["event_ticker"]] = ts
    cache.prune(live, set(u.raw))
    u.build_seconds = time.monotonic() - t0
    return u


def categorical_pair(event_ticker: str, a: str, b: str) -> R.Structural:
    out = [s for s in R.categorical_templates(event_ticker, [a, b], True) if s.relationship == "R1_EXCLUSIVE_PAIR"]
    return out[0]
