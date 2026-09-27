"""Independent state-space payoff verifier.

Given a portfolio of YES/NO positions on events defined over one or more real-valued
underlyings, enumerate every distinguishable outcome ("atom") and compute the portfolio payoff
in each. A relationship template's closed-form locked payoff is trusted only if it matches
`min_payoff` from this brute-force check (see tests/test_payoff.py).

Atoms: for the sorted set of all strike breakpoints b_1 < ... < b_k of an underlying, the atoms
are (-inf,b_1), {b_1}, (b_1,b_2), {b_2}, ..., {b_k}, (b_k,+inf). Each is represented by one
point (the breakpoint itself or an interior point), which is exact for events built from
intervals with those breakpoints, including open/closed endpoint (> vs >=) distinctions.

Exact arithmetic via fractions.Fraction. Void/cancellation states are NOT modelled here yet;
they are added after the settlement-rules review (DESIGN.md §3.8).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping, Sequence

State = Mapping[str, Fraction]


def F(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(str(x))


@dataclass(frozen=True)
class Interval:
    lo: Fraction | None = None      # None = -inf
    lo_closed: bool = False
    hi: Fraction | None = None      # None = +inf
    hi_closed: bool = False

    def contains(self, x: Fraction) -> bool:
        if self.lo is not None and (x < self.lo or (x == self.lo and not self.lo_closed)):
            return False
        if self.hi is not None and (x > self.hi or (x == self.hi and not self.hi_closed)):
            return False
        return True

    def breakpoints(self) -> tuple[Fraction, ...]:
        return tuple(b for b in (self.lo, self.hi) if b is not None)


# Convenience constructors (strike semantics are asserted by the caller, not inferred here).
def gt(a) -> Interval: return Interval(F(a), False, None, False)
def ge(a) -> Interval: return Interval(F(a), True, None, False)
def lt(b) -> Interval: return Interval(None, False, F(b), False)
def le(b) -> Interval: return Interval(None, False, F(b), True)
def closed_open(a, b) -> Interval: return Interval(F(a), True, F(b), False)
def closed(a, b) -> Interval: return Interval(F(a), True, F(b), True)


class Event:
    def __call__(self, s: State) -> bool: raise NotImplementedError
    def breakpoints(self) -> dict[str, set[Fraction]]: raise NotImplementedError


@dataclass(frozen=True)
class OnUnderlying(Event):
    underlying: str
    intervals: tuple[Interval, ...]          # union

    def __call__(self, s: State) -> bool:
        x = s[self.underlying]
        return any(iv.contains(x) for iv in self.intervals)

    def breakpoints(self):
        return {self.underlying: {b for iv in self.intervals for b in iv.breakpoints()}}


def on(underlying: str, *intervals: Interval) -> OnUnderlying:
    return OnUnderlying(underlying, tuple(intervals))


def _merge(*dicts):
    out: dict[str, set] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, set()).update(v)
    return out


@dataclass(frozen=True)
class And(Event):
    parts: tuple[Event, ...]
    def __call__(self, s): return all(p(s) for p in self.parts)
    def breakpoints(self): return _merge(*(p.breakpoints() for p in self.parts))


@dataclass(frozen=True)
class Not(Event):
    inner: Event
    def __call__(self, s): return not self.inner(s)
    def breakpoints(self): return self.inner.breakpoints()


def atoms(breaks: set[Fraction]) -> list[Fraction]:
    bs = sorted(breaks)
    if not bs:
        return [Fraction(0)]
    pts = [bs[0] - 1]
    for i, b in enumerate(bs):
        pts.append(b)
        pts.append((b + bs[i + 1]) / 2 if i + 1 < len(bs) else b + 1)
    return pts


def state_space(events: Sequence[Event]) -> list[dict[str, Fraction]]:
    bp = _merge(*(e.breakpoints() for e in events))
    keys = sorted(bp)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(atoms(bp[k]) for k in keys))]


@dataclass(frozen=True)
class Position:
    event: Event
    side: str            # 'yes' pays 1 if event occurs; 'no' pays 1 if it does not
    qty: Fraction = Fraction(1)

    def payoff(self, s: State) -> Fraction:
        occurred = self.event(s)
        if self.side == "yes":
            return self.qty if occurred else Fraction(0)
        if self.side == "no":
            return Fraction(0) if occurred else self.qty
        raise ValueError(self.side)


@dataclass(frozen=True)
class PayoffReport:
    states: tuple[dict, ...]
    payoffs: tuple[Fraction, ...]

    @property
    def min_payoff(self) -> Fraction: return min(self.payoffs)
    @property
    def max_payoff(self) -> Fraction: return max(self.payoffs)


def verify(positions: Sequence[Position],
           state_filter: Callable[[State], bool] | None = None) -> PayoffReport:
    """state_filter restricts to states the contract rules allow (e.g. an MEE event's
    underlying cannot fall outside the listed buckets). Default: all atoms allowed."""
    states = [s for s in state_space([p.event for p in positions]) if not state_filter or state_filter(s)]
    if not states:
        raise ValueError("empty state space after filter")
    return PayoffReport(tuple(states), tuple(sum((p.payoff(s) for p in positions), Fraction(0))
                                             for s in states))
