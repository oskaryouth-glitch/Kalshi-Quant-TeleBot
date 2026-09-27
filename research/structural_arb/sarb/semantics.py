"""Strike-to-interval mapping with a conservative semantic-uncertainty envelope.

Why an envelope: the structured API fields are an ENCODING that doesn't always agree literally
with the market's own rules text. Observed 2026-09-27 (see DESIGN.md §A):
  * KXINXU  fields `greater_or_equal 7550`   vs text "above 7549.9999"
  * KXNFLCAREERRSHYDS fields `greater 13999.5` vs text "at least 14,000"
  * POPVOTEMOV fields use negative strikes for one party (sign convention) -> rejected
  * "between" inclusivity is only defined in some contract terms.
Every plausible reading is a candidate true YES-set R_i for X (the Expiration Value):
    inner = ∩ R_i  (YES surely pays)      outer = ∪ R_i  (YES possibly pays)
In the payoff checker, a YES leg is credited only on `inner`, and a NO leg only outside
`outer`. Each market appears at most once in a portfolio and payoff is additive, so
min_X(worst-case payoff) is at most the min under ANY consistent choice of readings. The
envelope is therefore conservative.

X is modelled as REAL-valued unless contract terms prove a reporting precision. None of the
verified terms do: crypto uses an average of 60 prices, and temperature uses "full precision
reported". Bucket gaps such as (72499.99, 72500) are therefore real outcome states.

Markets whose text cannot be parsed into exactly one comparator, or whose text contradicts the
fields, are REJECTED. They are never guessed.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from .payoff import Interval
from . import terms as terms_mod

NUMERIC_STRIKE_TYPES = ("greater", "greater_or_equal", "less", "less_or_equal", "between")

_UNIT = r"(?:\s*(?:%|°\s*(?:fahrenheit|celsius|f|c)?|percent(?:age points)?|degrees(?:\s+(?:fahrenheit|celsius))?))?"
_SCALE = r"(?:\s*(?P<scale{n}>thousand|million|billion|trillion|k\b|m\b|b\b))?"
_NUM = (r"(?P<neg{n}>-\s*)?(?:c\$|us\$|\$)?\s*(?P<num{n}>\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?)"
        + _SCALE + _UNIT)


def _num(n: int) -> str:
    return _NUM.format(n=n)


_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("BETWEEN", re.compile(r"\bbetween\s+" + _num(1) + r"\s*(?:-|–|—|to|and)\s*" + _num(2))),
    ("BETWEEN_INCL", re.compile(_num(1) + r"\s*to\s*" + _num(2) + r",?\s*inclusive")),
    ("GE", re.compile(r"\b(?:at least|greater than or equal to|no less than|at or above|equal to or (?:greater than|above))\s+" + _num(1))),
    ("LE", re.compile(r"\b(?:at most|less than or equal to|no more than|at or below|equal to or (?:less than|below))\s+" + _num(1))),
    ("GE", re.compile(_num(1) + r"\s+or\s+(?:more|higher|above|greater)\b")),
    ("GE", re.compile(r"(?<![\w.])" + _num(1) + r"\+")),
    ("LE", re.compile(_num(1) + r"\s+or\s+(?:fewer|less|lower|below)\b")),
    ("GT", re.compile(r"\b(?:strictly greater than|strictly higher than|strictly above|greater than|higher than|more than|above|over|exceeds|exceeding|in excess of)\s+" + _num(1))),
    ("LT", re.compile(r"\b(?:strictly less than|strictly lower than|strictly below|less than|lower than|fewer than|below|under)\s+" + _num(1))),
    ("EXACT", re.compile(r"\bexactly\s+" + _num(1))),
]

_PATH_RE = re.compile(
    r"\b(ever|at any (?:time|point)|any time|anytime|on any|in any|any of the|at some point|hits?|"
    r"reach(?:es|ed)?|touch(?:es|ed)?|during|through|within|"
    r"(?:before|by) (?:the end|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\b")

_SCALES = {None: 1, "thousand": 10**3, "k": 10**3, "million": 10**6, "m": 10**6,
           "billion": 10**9, "b": 10**9, "trillion": 10**12}


class SemanticsError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class TextCondition:
    kind: str                         # GT GE LT LE BETWEEN BETWEEN_INCL EXACT
    values: tuple[Fraction, ...]      # with scale words applied ("$170 billion" -> 1.7e11)
    span: tuple[int, int]
    unscaled: tuple[Fraction, ...] = ()
    scale: str | None = None


def _parse_value(m: re.Match, n: int) -> tuple[Fraction, Fraction]:
    """Returns (scaled, unscaled)."""
    raw = m.group(f"num{n}").replace(",", "")
    try:
        v = Fraction(str(Decimal(raw)))
    except InvalidOperation as e:
        raise SemanticsError("NUMBER_PARSE", raw) from e
    if m.group(f"neg{n}") and n == 1:
        v = -v
    return v * _SCALES[m.group(f"scale{n}")], v


def parse_condition(text: str) -> TextCondition:
    low = text.lower()
    found: list[TextCondition] = []
    for kind, pat in _PATTERNS:
        for m in pat.finditer(low):
            pv = [_parse_value(m, 1)] + ([_parse_value(m, 2)] if kind.startswith("BETWEEN") else [])
            scales = {m.group(f"scale{i + 1}") for i in range(len(pv))}
            found.append(TextCondition(kind, tuple(a for a, _ in pv), m.span(), tuple(b for _, b in pv),
                                       "/".join(sorted(x for x in scales if x)) or None))
    # drop matches strictly contained in another match (e.g. 'greater than' inside 'greater than or equal to')
    kept = [c for c in found if not any(o is not c and o.span[0] <= c.span[0] and c.span[1] <= o.span[1]
                                        and (o.span != c.span) for o in found)]
    if not kept:
        raise SemanticsError("NO_COMPARATOR", text[:160])
    if len({(c.kind, c.values) for c in kept}) > 1:
        raise SemanticsError("AMBIGUOUS_COMPARATOR", str(sorted((c.kind, [str(x) for x in c.values]) for c in kept)))
    return min(kept, key=lambda c: c.span)


def _F(x) -> Fraction:
    return Fraction(str(Decimal(str(x))))


def field_reading(strike_type: str, floor, cap) -> Interval:
    if strike_type == "greater" and floor is not None and cap is None:
        return Interval(_F(floor), False, None, False)
    if strike_type == "greater_or_equal" and floor is not None and cap is None:
        return Interval(_F(floor), True, None, False)
    if strike_type == "less" and cap is not None and floor is None:
        return Interval(None, False, _F(cap), False)
    if strike_type == "less_or_equal" and cap is not None and floor is None:
        return Interval(None, False, _F(cap), True)
    if strike_type == "between" and floor is not None and cap is not None and _F(floor) <= _F(cap):
        return Interval(_F(floor), True, _F(cap), True)   # field docs: min/max value leading to YES
    raise SemanticsError("FIELD_SHAPE", f"{strike_type} floor={floor} cap={cap}")


def text_readings(c: TextCondition, between_inclusive: bool | None) -> list[Interval]:
    v = c.values
    if c.kind == "GT":
        return [Interval(v[0], False, None, False)]
    if c.kind == "GE":
        return [Interval(v[0], True, None, False)]
    if c.kind == "LT":
        return [Interval(None, False, v[0], False)]
    if c.kind == "LE":
        return [Interval(None, False, v[0], True)]
    if c.kind in ("BETWEEN", "BETWEEN_INCL"):
        lo, hi = min(v), max(v)
        if c.kind == "BETWEEN_INCL" or between_inclusive is True:
            return [Interval(lo, True, hi, True)]
        if between_inclusive is False:
            return [Interval(lo, False, hi, False)]
        return [Interval(lo, a, hi, b) for a in (True, False) for b in (True, False)]
    raise SemanticsError("UNSUPPORTED_COMPARATOR", c.kind)


def _direction(kind_or_type: str) -> str:
    if kind_or_type in ("GT", "GE", "greater", "greater_or_equal"):
        return "up"
    if kind_or_type in ("LT", "LE", "less", "less_or_equal"):
        return "down"
    return "range"


def _close(a: Fraction, b: Fraction) -> bool:
    """Plausibly the same strike (guards against capturing the wrong number). Offsets such as
    13999.5 vs 14000 or 7549.9999 vs 7550 are encodings; the envelope absorbs them."""
    d = abs(a - b)
    return d <= 1 or d <= Fraction(1, 1000) * max(abs(a), abs(b))


def intersect(ivs: list[Interval]) -> Interval | None:
    lo, lo_c, hi, hi_c = None, False, None, False
    for iv in ivs:
        if iv.lo is not None:
            if lo is None or iv.lo > lo:
                lo, lo_c = iv.lo, iv.lo_closed
            elif iv.lo == lo:
                lo_c = lo_c and iv.lo_closed
        if iv.hi is not None:
            if hi is None or iv.hi < hi:
                hi, hi_c = iv.hi, iv.hi_closed
            elif iv.hi == hi:
                hi_c = hi_c and iv.hi_closed
    if lo is not None and hi is not None and (lo > hi or (lo == hi and not (lo_c and hi_c))):
        return None
    return Interval(lo, lo_c, hi, hi_c)


@dataclass(frozen=True)
class Envelope:
    inner: tuple[Interval, ...]      # union; YES surely pays for X in inner
    outer: tuple[Interval, ...]      # union; YES possibly pays for X in outer

    def sure_yes(self, x: Fraction) -> bool:
        return any(iv.contains(x) for iv in self.inner)

    def maybe_yes(self, x: Fraction) -> bool:
        return any(iv.contains(x) for iv in self.outer)

    def breakpoints(self) -> set[Fraction]:
        return {b for iv in self.inner + self.outer for b in iv.breakpoints()}


@dataclass
class MarketSpec:
    ticker: str
    event_ticker: str
    series_ticker: str
    strike_type: str | None
    envelope: Envelope | None = None
    direction: str | None = None
    template: str | None = None
    path_dependent: bool = False
    family_key: str | None = None
    terms: terms_mod.VerifiedTerms | None = None
    terms_status: str = "TERMS_UNVERIFIED"
    no_data_all_no: bool = True
    readings: list[str] = field(default_factory=list)
    reject: str | None = None
    market_fp: str | None = None        # fingerprint of the market fields the spec was built from
    terms_url: str | None = None
    terms_sha: str | None = None        # hash observed when the spec was built (None if not checked)


MARKET_FP_FIELDS = ("ticker", "rules_primary", "rules_secondary", "strike_type", "floor_strike", "cap_strike",
                    "custom_strike", "functional_strike", "latest_expiration_time", "market_type",
                    "notional_value_dollars")


def market_fingerprint(market: dict) -> str:
    """Any change to these fields after a template was built invalidates it (collector gate)."""
    return hashlib.sha256(json.dumps([market.get(k) for k in MARKET_FP_FIELDS], sort_keys=True,
                                     default=str).encode()).hexdigest()


def build_market_spec(event: dict, market: dict, series: dict | None, terms_sha: dict[str, str]) -> MarketSpec:
    """event: /events item (event-level fields); market: nested market; series: /series body.
    terms_sha: contract_terms_url -> sha256 fetched in this run."""
    st = market.get("strike_type")
    s = (series or {}).get("series", series or {})
    url = s.get("contract_terms_url")
    vt, tstatus = terms_mod.lookup(url, terms_sha.get(url) if url else None)
    spec = MarketSpec(market["ticker"], event["event_ticker"], event.get("series_ticker", ""), st,
                      terms=vt, terms_status=tstatus,
                      no_data_all_no=(vt is None or vt.no_data == "ALL_NO"),
                      market_fp=market_fingerprint(market), terms_url=url,
                      terms_sha=terms_sha.get(url) if url else None)
    try:
        if market.get("market_type") != "binary":
            raise SemanticsError("NOT_BINARY", str(market.get("market_type")))
        if Decimal(str(market.get("notional_value_dollars", "0"))) != 1:
            raise SemanticsError("NOTIONAL_NOT_1", str(market.get("notional_value_dollars")))
        if st not in NUMERIC_STRIKE_TYPES:
            raise SemanticsError("NON_NUMERIC_STRIKE", str(st))
        text = market.get("rules_primary") or ""
        cond = parse_condition(text)
        fr = field_reading(st, market.get("floor_strike"), market.get("cap_strike"))
        tdir, fdir = _direction(cond.kind), _direction(st)
        # A bounded text range may encode a half-line field (e.g. vote share "44% to 100%,
        # inclusive" vs field >= 44). Allowed only if the field's finite endpoint is matched below.
        if tdir != fdir and not (tdir == "range" and fdir in ("up", "down")):
            raise SemanticsError("TEXT_FIELD_DIRECTION_CONFLICT", f"{cond.kind} vs {st}")
        # Units: the fields are sometimes in scaled units ("$170 billion" vs floor 170). Use the
        # text values (scaled or unscaled) that match EVERY finite field endpoint, or reject.
        chosen = None
        for label, vals in (("scaled", cond.values), ("unscaled", cond.unscaled)):
            c2 = TextCondition(cond.kind, vals, cond.span, cond.unscaled, cond.scale)
            trs = text_readings(c2, vt.between_inclusive if vt else None)
            ok = True
            for fe, te in ((fr.lo, [t.lo for t in trs]), (fr.hi, [t.hi for t in trs])):
                if fe is not None and not all(t is not None and _close(fe, t) for t in te):
                    ok = False
            if ok:
                chosen = (label, trs)
                break
        if chosen is None:
            raise SemanticsError("TEXT_FIELD_VALUE_CONFLICT",
                                 f"field [{fr.lo},{fr.hi}] vs text {[str(x) for x in cond.values]}")
        trs = chosen[1]
        readings = [fr] + trs
        inner = intersect(readings)
        spec.envelope = Envelope((inner,) if inner else (), tuple(readings))
        spec.readings = [repr(r) for r in readings]
        spec.direction = _direction(st)
        tmpl = re.sub(r"\s+", " ", (text[:cond.span[0]] + "<COND>" + text[cond.span[1]:]).strip().lower())
        spec.template = tmpl
        spec.path_dependent = bool(_PATH_RE.search(tmpl))
        if spec.path_dependent and spec.direction == "range":
            raise SemanticsError("PATH_DEPENDENT_RANGE", "between on a path-dependent statistic")
        key = {
            "terms_url": url, "template": tmpl,
            "rules_secondary": re.sub(r"\s+", " ", (market.get("rules_secondary") or "").strip()),
            "custom_strike": market.get("custom_strike"),
            "latest_expiration_time": market.get("latest_expiration_time"),
            "settlement_sources": event.get("settlement_sources") or s.get("settlement_sources"),
            "direction_class": spec.direction if spec.path_dependent else "single_statistic",
            "units": (chosen[0], cond.scale),
        }
        spec.family_key = hashlib.sha256(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:16]
    except SemanticsError as e:
        spec.reject = e.code
    return spec


def group_families(specs: list[MarketSpec]) -> dict[str, list[MarketSpec]]:
    fam: dict[str, list[MarketSpec]] = {}
    for sp in specs:
        if sp.reject is None and sp.family_key:
            fam.setdefault(sp.family_key, []).append(sp)
    return fam
