"""Independent brute-force payoff checker over explicit settlement states.

A settlement STATE assigns each market a worst-case truth:
    sure_yes  -- YES certainly pays $1
    maybe_yes -- YES might pay (sure_yes implies maybe_yes)
A YES position pays qty iff sure_yes, and a NO position pays qty iff not maybe_yes. This is the
adversarial reading of any semantic uncertainty (see semantics.Envelope). Payoffs are exact
Fractions.

The three state generators below cover every outcome class that the determinate rules allow:
  * interval_states: one real-valued underlying X (atoms of all breakpoints: every breakpoint
    and every open gap between them), plus an ALL_NO state when the terms say "no data -> No"
    or the terms are unverified.
  * categorical_states: at most one market resolves YES (MECNET, per the API definition), plus
    a NONE state, because exhaustiveness is not provable.
  * binary_product_states: independent component outcomes (for combos).
Discretionary settlements (Rulebook 6.3(c)/7.1 "fair price", result='scalar') are NOT states
here. They are reported separately via one_leg_discretionary_worst() and the residual-risk
list.

A relationship's closed-form locked payoff is trusted only when it equals verify().min_payoff.
The randomized tests in tests/test_relationships.py check this.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterable, Mapping, Sequence


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

    def __repr__(self) -> str:
        l = "(-inf" if self.lo is None else ("[" if self.lo_closed else "(") + str(self.lo)
        h = "+inf)" if self.hi is None else str(self.hi) + ("]" if self.hi_closed else ")")
        return f"{l},{h}"


def gt(a) -> Interval: return Interval(F(a), False, None, False)
def ge(a) -> Interval: return Interval(F(a), True, None, False)
def lt(b) -> Interval: return Interval(None, False, F(b), False)
def le(b) -> Interval: return Interval(None, False, F(b), True)
def closed(a, b) -> Interval: return Interval(F(a), True, F(b), True)
def closed_open(a, b) -> Interval: return Interval(F(a), True, F(b), False)
def open_(a, b) -> Interval: return Interval(F(a), False, F(b), False)


def atoms(breaks: Iterable[Fraction]) -> list[Fraction]:
    """One representative point per distinguishable region: every breakpoint, every open gap
    between consecutive breakpoints, and both tails."""
    bs = sorted(set(breaks))
    if not bs:
        return [Fraction(0)]
    pts = [bs[0] - 1]
    for i, b in enumerate(bs):
        pts.append(b)
        pts.append((b + bs[i + 1]) / 2 if i + 1 < len(bs) else b + 1)
    return pts


@dataclass(frozen=True)
class Truth:
    sure_yes: bool
    maybe_yes: bool

    def __post_init__(self):
        if self.sure_yes and not self.maybe_yes:
            raise ValueError("sure_yes implies maybe_yes")


NO_T = Truth(False, False)
YES_T = Truth(True, True)


@dataclass(frozen=True)
class State:
    label: str
    truth: Mapping[str, Truth]


@dataclass(frozen=True)
class Position:
    ticker: str
    side: str              # 'yes' | 'no'
    qty: Fraction = Fraction(1)

    def payoff(self, s: State) -> Fraction:
        t = s.truth[self.ticker]
        if self.side == "yes":
            return self.qty if t.sure_yes else Fraction(0)
        if self.side == "no":
            return Fraction(0) if t.maybe_yes else self.qty
        raise ValueError(self.side)


@dataclass(frozen=True)
class PayoffReport:
    labels: tuple[str, ...]
    payoffs: tuple[Fraction, ...]

    @property
    def min_payoff(self) -> Fraction:
        return min(self.payoffs)

    @property
    def argmin(self) -> str:
        return self.labels[self.payoffs.index(self.min_payoff)]

    @property
    def max_payoff(self) -> Fraction:
        return max(self.payoffs)


def _check_portfolio(positions: Sequence[Position]) -> None:
    tickers = [p.ticker for p in positions]
    if len(set(tickers)) != len(tickers):
        # Holding both sides (or two lots) of one market nets on Kalshi; templates never do this.
        raise ValueError(f"market used more than once in a portfolio: {tickers}")


def verify(positions: Sequence[Position], states: Sequence[State]) -> PayoffReport:
    _check_portfolio(positions)
    if not states:
        raise ValueError("empty state space")
    return PayoffReport(tuple(s.label for s in states),
                        tuple(sum((p.payoff(s) for p in positions), Fraction(0)) for s in states))


def one_leg_discretionary_worst(positions: Sequence[Position], states: Sequence[State]) -> Fraction:
    """Worst payoff if any ONE leg is instead settled at an adversarial Exchange-determined value
    (Rulebook 6.3(c) 'fair price'), and every other leg settles determinately."""
    _check_portfolio(positions)
    worst = None
    for s in states:
        pay = [p.payoff(s) for p in positions]
        tot = sum(pay, Fraction(0))
        for x in pay:
            v = tot - x
            worst = v if worst is None or v < worst else worst
    return worst if worst is not None else Fraction(0)


# ------------------------------------------------------------------ state generators

def interval_states(envelopes: Mapping[str, "object"], include_all_no: bool) -> list[State]:
    """envelopes: ticker -> object with sure_yes(x), maybe_yes(x), breakpoints()."""
    bps: set[Fraction] = set()
    for e in envelopes.values():
        bps |= e.breakpoints()
    out = [State(f"X={x}", {t: Truth(e.sure_yes(x), e.maybe_yes(x)) for t, e in envelopes.items()})
           for x in atoms(bps)]
    if include_all_no:
        out.append(State("ALL_NO(no data)", {t: NO_T for t in envelopes}))
    return out


def categorical_states(tickers: Sequence[str]) -> list[State]:
    out = [State(f"WINNER={w}", {t: (YES_T if t == w else NO_T) for t in tickers}) for w in tickers]
    out.append(State("NONE(no listed winner / ALL_NO)", {t: NO_T for t in tickers}))
    return out


def binary_product_states(components: Sequence[str],
                          derived: Mapping[str, Callable[[Mapping[str, bool]], bool]]) -> list[State]:
    """Independent binary components, and derived markets whose outcome is a function of them."""
    out = []
    for bits in itertools.product((False, True), repeat=len(components)):
        env = dict(zip(components, bits))
        truth = {c: (YES_T if b else NO_T) for c, b in env.items()}
        for t, fn in derived.items():
            truth[t] = YES_T if fn(env) else NO_T
        out.append(State("COMP=" + "".join("1" if b else "0" for b in bits), truth))
    return out
