"""Structural relationship templates R1-R5 (derivations in DESIGN.md §B).

Every template is a portfolio of TAKER BUYS (YES or NO) in distinct markets. A NO position is
YES on the complement, so the locked payoff L of any portfolio is
    L = min over allowed settlement states of #(positions that pay)
Two independent computations are made:
  (1) FAST template pass: bitmasks over the family's state list. YES pays on `sure`, NO pays on
      `~maybe`. Used to enumerate candidates cheaply, and independent of prices.
  (2) payoff.verify(): the brute-force checker on explicit State objects.
They must agree. Any disagreement is recorded as a BUG and the candidate is rejected.

Templates (nominal L assumes ideal, exact semantics; the actual L is whatever the checker says):
  R1_LONG            YES on every market of one event                       nominal 1
  R1_SHORT           NO  on every market of one event                       nominal n-1
  R1_EXCLUSIVE_PAIR  NO on two markets that can't both be YES               L = 1
                     (dominates R1_SHORT: each extra NO leg adds bid-1-fee < 0)
  R2_NESTED          YES_big + NO_small with E_small ⊆ E_big                L = 1
  R4_DUPLICATE       R2 holding in both directions (E_a = E_b)              L = 1
  R4_COVER_PAIR      YES_a + YES_b with E_a ∪ E_b = everything              L = 1
  R3_RANGE_A         YES on buckets S + NO_T with E_T ⊆ ∪S                  nominal 1
  R3_RANGE_B         YES_T + NO on buckets S with ∪S ⊆ E_T (S disjoint)     nominal |S|
  R5_COMBO_UPPER     component leg position + NO_combo  (P(A∧B) <= P(A))    L = 1
  R5_COMBO_LOWER     YES_combo + opposite of every leg  (Fréchet lower)     L = 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from typing import Sequence

from . import payoff as P
from .semantics import MarketSpec


@dataclass
class Structural:
    relationship: str
    relationship_class: str             # GUARANTEED (locks in all determinate states) | STATISTICAL
    positions: tuple[P.Position, ...]
    nominal_locked: Fraction
    locked: Fraction                    # checker min payoff over determinate states
    argmin_state: str
    one_leg_discretionary_worst: Fraction
    family_key: str
    events: tuple[str, ...]
    notes: list[str] = field(default_factory=list)
    terms_verified: bool = False        # every leg's series terms verified (sarb/terms.py)
    checked: bool = True                # independent checker has run (lazy mode defers it)
    states: tuple = field(default=(), repr=False, compare=False)


def check(st: "Structural") -> "Structural":
    """Run the independent brute-force checker on a lazily enumerated template (in place)."""
    if st.checked:
        return st
    fast = st.locked
    if isinstance(st.states, _LazyStates):
        st.states = st.states.get()
    rep = P.verify(st.positions, st.states)
    if rep.min_payoff != fast:
        st.notes.append(f"BUG_TEMPLATE_VS_CHECKER fast={fast} checker={rep.min_payoff}")
    st.locked, st.argmin_state = rep.min_payoff, rep.argmin
    st.one_leg_discretionary_worst = P.one_leg_discretionary_worst(st.positions, st.states)
    st.relationship_class = ("GUARANTEED" if (rep.min_payoff >= st.nominal_locked and rep.min_payoff > 0
                                              and not st.notes) else "STATISTICAL")
    st.checked = True
    return st


class Family:
    """Markets on ONE underlying X (same template, terms, secondary rules, expiry, sources).

    Masks are computed directly over the atoms (bit i = atom i; one extra bit for ALL_NO when
    included), using the same atom and state order as payoff.interval_states(). The explicit
    State objects for the independent checker are built lazily."""

    def __init__(self, specs: Sequence[MarketSpec]):
        self.specs = {s.ticker: s for s in specs}
        self.key = specs[0].family_key
        self.terms_verified = all(s.terms_status == "TERMS_VERIFIED" for s in specs)
        self.include_all_no = any(s.no_data_all_no for s in specs)
        bps: set = set()
        for sp in self.specs.values():
            bps |= sp.envelope.breakpoints()
        self.xs = P.atoms(bps)
        n = len(self.xs) + (1 if self.include_all_no else 0)
        self.full = (1 << n) - 1
        self.sure, self.maybe = {}, {}
        for t, sp in self.specs.items():
            e, su, mb = sp.envelope, 0, 0
            for i, x in enumerate(self.xs):
                if e.sure_yes(x):
                    su |= 1 << i
                if e.maybe_yes(x):
                    mb |= 1 << i
            self.sure[t], self.maybe[t] = su, mb      # ALL_NO bit stays 0: every market resolves No
        self._states = None

    @property
    def states(self) -> list[P.State]:
        if self._states is None:
            self._states = P.interval_states({t: s.envelope for t, s in self.specs.items()}, self.include_all_no)
        return self._states

    def pay_mask(self, ticker: str, side: str) -> int:
        return self.sure[ticker] if side == "yes" else (~self.maybe[ticker]) & self.full

    def locked_fast(self, positions: Sequence[P.Position]) -> Fraction:
        """min over states of #paying positions (unit quantities), via 'at least k' bitsets:
        ge[k] = set of states where at least k positions pay."""
        if any(p.qty != 1 for p in positions):
            raise ValueError("locked_fast supports unit quantities only")
        ge = [self.full] + [0] * len(positions)
        for p in positions:
            m = self.pay_mask(p.ticker, p.side)
            for k in range(len(positions), 0, -1):
                ge[k] |= ge[k - 1] & m
        return Fraction(max(k for k in range(len(ge)) if ge[k] == self.full))

    def pair_relationship(self, a: str, sa: str, b: str, sb: str) -> str | None:
        """Name of the structural relationship if the pair locks >= 1, else None."""
        ma, mb = self.pay_mask(a, sa), self.pay_mask(b, sb)
        if (ma | mb) != self.full:
            return None
        if sa != sb:
            big, small = (a, b) if sa == "yes" else (b, a)
            rev = (self.pay_mask(small, "yes") | self.pay_mask(big, "no")) == self.full
            return "R4_DUPLICATE" if rev else "R2_NESTED"
        return "R4_COVER_PAIR" if sa == "yes" else "R1_EXCLUSIVE_PAIR"

    def by_event(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for t, s in self.specs.items():
            out.setdefault(s.event_ticker, []).append(t)
        return out


_LAZY = False


class _LazyStates:
    """Defers Family.states until the checker actually needs them."""
    def __init__(self, fam: "Family"):
        self.fam = fam

    def get(self):
        return self.fam.states


def _finish(fam_key: str, rel: str, positions: Sequence[P.Position], nominal: Fraction,
            fast: Fraction, states, events: Sequence[str],
            terms_verified: bool = False) -> Structural:
    if _LAZY:
        klass = "GUARANTEED" if (fast >= nominal and fast > 0) else "STATISTICAL"
        return Structural(rel, klass, tuple(positions), nominal, fast, "UNCHECKED", Fraction(-1), fam_key,
                          tuple(sorted(set(events))), [], terms_verified, False, states)
    if isinstance(states, _LazyStates):
        states = states.get()
    rep = P.verify(positions, states)
    notes = []
    if rep.min_payoff != fast:
        notes.append(f"BUG_TEMPLATE_VS_CHECKER fast={fast} checker={rep.min_payoff}")
    klass = "GUARANTEED" if (rep.min_payoff >= nominal and rep.min_payoff > 0 and not notes) else "STATISTICAL"
    return Structural(rel, klass, tuple(positions), nominal, rep.min_payoff, rep.argmin,
                      P.one_leg_discretionary_worst(positions, states), fam_key,
                      tuple(sorted(set(events))), notes, terms_verified)


def numeric_family_templates(fam: Family, lazy: bool = False, include_pairs: bool = True) -> list[Structural]:
    global _LAZY
    _LAZY = lazy
    try:
        return _numeric_family_templates(fam, include_pairs)
    finally:
        _LAZY = False


def pair_struct(fam: Family, a: str, sa: str, b: str, sb: str, lazy: bool = True) -> Structural | None:
    rel = fam.pair_relationship(a, sa, b, sb)
    if rel is None:
        return None
    if rel == "R2_NESTED" or rel == "R4_DUPLICATE":
        big, small = (a, b) if sa == "yes" else (b, a)
        pos = [P.Position(big, "yes"), P.Position(small, "no")]
    else:
        pos = sorted([P.Position(a, sa), P.Position(b, sb)], key=lambda p: p.ticker)
    evs = [fam.specs[a].event_ticker, fam.specs[b].event_ticker]
    global _LAZY
    _LAZY = lazy
    try:
        return _finish(fam.key, rel, pos, Fraction(1), fam.locked_fast(pos), _LazyStates(fam), evs, fam.terms_verified)
    finally:
        _LAZY = False


def screen_pairs(fam: Family, ask) -> list[Structural]:
    """All structurally locking pairs whose summed asks are < 1, found WITHOUT enumerating every
    pair. ask(ticker, side) -> Decimal | None. For each first leg, the second legs are scanned in
    increasing ask order, and the scan stops once the sum reaches 1. Tests prove the result
    equals the full enumeration filtered by ask sum < 1."""
    from decimal import Decimal
    quotes = {side: sorted((a, t) for t in fam.specs for a in [ask(t, side)] if a is not None)
              for side in ("yes", "no")}
    out, seen = [], set()
    for sa in ("yes", "no"):
        for a_price, a in quotes[sa]:
            for sb in ("yes", "no"):
                for b_price, b in quotes[sb]:
                    if a_price + b_price >= Decimal(1):
                        break
                    if b == a:
                        continue
                    key = frozenset(((a, sa), (b, sb)))
                    if key in seen:
                        continue
                    seen.add(key)
                    st = pair_struct(fam, a, sa, b, sb)
                    if st is not None:
                        out.append(st)
    return out


def _numeric_family_templates(fam: Family, include_pairs: bool = True) -> list[Structural]:
    out: list[Structural] = []
    ev = fam.by_event()
    tickers = sorted(fam.specs)
    # ---- R1 on each event's market set within the family
    for e, ts in ev.items():
        if len(ts) < 2:
            continue
        long_ = [P.Position(t, "yes") for t in sorted(ts)]
        short = [P.Position(t, "no") for t in sorted(ts)]
        out.append(_finish(fam.key, "R1_LONG", long_, Fraction(1), fam.locked_fast(long_), _LazyStates(fam), [e], fam.terms_verified))
        out.append(_finish(fam.key, "R1_SHORT", short, Fraction(len(ts) - 1), fam.locked_fast(short), _LazyStates(fam), [e], fam.terms_verified))
    # ---- pairs: R1_EXCLUSIVE_PAIR / R2 / R4
    for a, b in (combinations(tickers, 2) if include_pairs else ()):
        evs = [fam.specs[a].event_ticker, fam.specs[b].event_ticker]
        ya, yb, na, nb = (fam.pay_mask(a, "yes"), fam.pay_mask(b, "yes"),
                          fam.pay_mask(a, "no"), fam.pay_mask(b, "no"))
        a_in_b = (ya | nb) == fam.full           # YES_a + NO_b locks 1  <=>  E_b ⊆ E_a (surely)
        b_in_a = (yb | na) == fam.full
        if a_in_b and b_in_a:
            for big, small in ((a, b), (b, a)):
                pos = [P.Position(big, "yes"), P.Position(small, "no")]
                out.append(_finish(fam.key, "R4_DUPLICATE", pos, Fraction(1), fam.locked_fast(pos), _LazyStates(fam), evs, fam.terms_verified))
        elif a_in_b or b_in_a:
            big, small = (a, b) if a_in_b else (b, a)
            pos = [P.Position(big, "yes"), P.Position(small, "no")]
            out.append(_finish(fam.key, "R2_NESTED", pos, Fraction(1), fam.locked_fast(pos), _LazyStates(fam), evs, fam.terms_verified))
        if (ya | yb) == fam.full:
            pos = [P.Position(a, "yes"), P.Position(b, "yes")]
            out.append(_finish(fam.key, "R4_COVER_PAIR", pos, Fraction(1), fam.locked_fast(pos), _LazyStates(fam), evs, fam.terms_verified))
        if (na | nb) == fam.full:
            pos = [P.Position(a, "no"), P.Position(b, "no")]
            out.append(_finish(fam.key, "R1_EXCLUSIVE_PAIR", pos, Fraction(1), fam.locked_fast(pos), _LazyStates(fam), evs, fam.terms_verified))
    # ---- R3: each half-line market T against each event's buckets that can overlap it
    for t in tickers:
        if fam.specs[t].direction not in ("up", "down"):
            continue
        for e, ts in ev.items():
            S = sorted(m for m in ts if m != t and (fam.maybe[m] & fam.maybe[t]))
            # S must be pairwise disjoint buckets (a partition piece). A ladder of nested
            # thresholds is not a bucket set; R2 already covers each of its pairs.
            if len(S) < 2 or any(fam.maybe[x] & fam.maybe[y] for x, y in combinations(S, 2)):
                continue
            a = [P.Position(m, "yes") for m in S] + [P.Position(t, "no")]
            out.append(_finish(fam.key, "R3_RANGE_A", a, Fraction(1), fam.locked_fast(a), _LazyStates(fam),
                               [e, fam.specs[t].event_ticker], fam.terms_verified))
            b = [P.Position(t, "yes")] + [P.Position(m, "no") for m in S]
            out.append(_finish(fam.key, "R3_RANGE_B", b, Fraction(len(S)), fam.locked_fast(b), _LazyStates(fam),
                               [e, fam.specs[t].event_ticker], fam.terms_verified))
    return out


def categorical_templates(event_ticker: str, tickers: Sequence[str], mutually_exclusive: bool) -> list[Structural]:
    """Non-numeric markets of one event. At most one YES is guaranteed ONLY by
    mutually_exclusive=True (collateral_return_type MECNET; API docs). Exhaustiveness is never
    provable, so a NONE state is always included."""
    if not mutually_exclusive or len(tickers) < 2:
        return []
    states = P.categorical_states(list(tickers))
    key = f"MECNET:{event_ticker}"
    out = []
    long_ = [P.Position(t, "yes") for t in sorted(tickers)]
    short = [P.Position(t, "no") for t in sorted(tickers)]
    fast_min = lambda pos: min(sum((p.payoff(s) for p in pos), Fraction(0)) for s in states)  # noqa: E731
    out.append(_finish(key, "R1_LONG", long_, Fraction(1), fast_min(long_), states, [event_ticker]))
    out.append(_finish(key, "R1_SHORT", short, Fraction(len(tickers) - 1), fast_min(short), states, [event_ticker]))
    for a, b in combinations(sorted(tickers), 2):
        pos = [P.Position(a, "no"), P.Position(b, "no")]
        out.append(_finish(key, "R1_EXCLUSIVE_PAIR", pos, Fraction(1), fast_min(pos), states, [event_ticker]))
    return out


def combo_templates(combo_ticker: str, legs: Sequence[dict]) -> list[Structural]:
    """legs: mve_selected_legs [{market_ticker, side}]. Combo YES pays the product of component
    payouts (FOOTBALLSTATS terms: 'product of the payouts for each <component> ... rounded
    down to the nearest cent'). In determinate states that is the AND of the legs' sides."""
    comps = [l["market_ticker"] for l in legs]
    if len(set(comps)) != len(comps) or combo_ticker in comps or len(comps) < 2:
        return []
    sides = {l["market_ticker"]: l["side"] for l in legs}
    derived = {combo_ticker: lambda env: all(env[c] == (sides[c] == "yes") for c in comps)}
    states = P.binary_product_states(comps, derived)
    key = f"COMBO:{combo_ticker}"
    fast_min = lambda pos: min(sum((p.payoff(s) for p in pos), Fraction(0)) for s in states)  # noqa: E731
    out = []
    for c in comps:
        pos = [P.Position(c, sides[c]), P.Position(combo_ticker, "no")]
        out.append(_finish(key, "R5_COMBO_UPPER", pos, Fraction(1), fast_min(pos), states, [combo_ticker]))
    opp = {"yes": "no", "no": "yes"}
    pos = [P.Position(combo_ticker, "yes")] + [P.Position(c, opp[sides[c]]) for c in comps]
    out.append(_finish(key, "R5_COMBO_LOWER", pos, Fraction(1), fast_min(pos), states, [combo_ticker]))
    return out
