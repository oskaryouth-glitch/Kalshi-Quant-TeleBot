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


class Family:
    """Markets on ONE underlying X (same template, terms, secondary rules, expiry, sources)."""

    def __init__(self, specs: Sequence[MarketSpec]):
        self.specs = {s.ticker: s for s in specs}
        self.key = specs[0].family_key
        self.terms_verified = all(s.terms_status == "TERMS_VERIFIED" for s in specs)
        self.include_all_no = any(s.no_data_all_no for s in specs)
        self.states = P.interval_states({t: s.envelope for t, s in self.specs.items()}, self.include_all_no)
        self.full = (1 << len(self.states)) - 1
        self.sure = {t: 0 for t in self.specs}
        self.maybe = {t: 0 for t in self.specs}
        for i, st in enumerate(self.states):
            for t, tr in st.truth.items():
                if tr.sure_yes:
                    self.sure[t] |= 1 << i
                if tr.maybe_yes:
                    self.maybe[t] |= 1 << i

    def pay_mask(self, ticker: str, side: str) -> int:
        return self.sure[ticker] if side == "yes" else (~self.maybe[ticker]) & self.full

    def locked_fast(self, positions: Sequence[P.Position]) -> Fraction:
        best = None
        for i in range(len(self.states)):
            v = sum((p.qty for p in positions if self.pay_mask(p.ticker, p.side) >> i & 1), Fraction(0))
            best = v if best is None or v < best else best
        return best

    def by_event(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for t, s in self.specs.items():
            out.setdefault(s.event_ticker, []).append(t)
        return out


def _finish(fam_key: str, rel: str, positions: Sequence[P.Position], nominal: Fraction,
            fast: Fraction, states: Sequence[P.State], events: Sequence[str],
            terms_verified: bool = False) -> Structural:
    rep = P.verify(positions, states)
    notes = []
    if rep.min_payoff != fast:
        notes.append(f"BUG_TEMPLATE_VS_CHECKER fast={fast} checker={rep.min_payoff}")
    klass = "GUARANTEED" if (rep.min_payoff >= nominal and rep.min_payoff > 0 and not notes) else "STATISTICAL"
    return Structural(rel, klass, tuple(positions), nominal, rep.min_payoff, rep.argmin,
                      P.one_leg_discretionary_worst(positions, states), fam_key,
                      tuple(sorted(set(events))), notes, terms_verified)


def numeric_family_templates(fam: Family) -> list[Structural]:
    out: list[Structural] = []
    ev = fam.by_event()
    tickers = sorted(fam.specs)
    # ---- R1 on each event's market set within the family
    for e, ts in ev.items():
        if len(ts) < 2:
            continue
        long_ = [P.Position(t, "yes") for t in sorted(ts)]
        short = [P.Position(t, "no") for t in sorted(ts)]
        out.append(_finish(fam.key, "R1_LONG", long_, Fraction(1), fam.locked_fast(long_), fam.states, [e], fam.terms_verified))
        out.append(_finish(fam.key, "R1_SHORT", short, Fraction(len(ts) - 1), fam.locked_fast(short), fam.states, [e], fam.terms_verified))
    # ---- pairs: R1_EXCLUSIVE_PAIR / R2 / R4
    for a, b in combinations(tickers, 2):
        evs = [fam.specs[a].event_ticker, fam.specs[b].event_ticker]
        ya, yb, na, nb = (fam.pay_mask(a, "yes"), fam.pay_mask(b, "yes"),
                          fam.pay_mask(a, "no"), fam.pay_mask(b, "no"))
        a_in_b = (ya | nb) == fam.full           # YES_a + NO_b locks 1  <=>  E_b ⊆ E_a (surely)
        b_in_a = (yb | na) == fam.full
        if a_in_b and b_in_a:
            for big, small in ((a, b), (b, a)):
                pos = [P.Position(big, "yes"), P.Position(small, "no")]
                out.append(_finish(fam.key, "R4_DUPLICATE", pos, Fraction(1), fam.locked_fast(pos), fam.states, evs, fam.terms_verified))
        elif a_in_b or b_in_a:
            big, small = (a, b) if a_in_b else (b, a)
            pos = [P.Position(big, "yes"), P.Position(small, "no")]
            out.append(_finish(fam.key, "R2_NESTED", pos, Fraction(1), fam.locked_fast(pos), fam.states, evs, fam.terms_verified))
        if (ya | yb) == fam.full:
            pos = [P.Position(a, "yes"), P.Position(b, "yes")]
            out.append(_finish(fam.key, "R4_COVER_PAIR", pos, Fraction(1), fam.locked_fast(pos), fam.states, evs, fam.terms_verified))
        if (na | nb) == fam.full:
            pos = [P.Position(a, "no"), P.Position(b, "no")]
            out.append(_finish(fam.key, "R1_EXCLUSIVE_PAIR", pos, Fraction(1), fam.locked_fast(pos), fam.states, evs, fam.terms_verified))
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
            out.append(_finish(fam.key, "R3_RANGE_A", a, Fraction(1), fam.locked_fast(a), fam.states,
                               [e, fam.specs[t].event_ticker], fam.terms_verified))
            b = [P.Position(t, "yes")] + [P.Position(m, "no") for m in S]
            out.append(_finish(fam.key, "R3_RANGE_B", b, Fraction(len(S)), fam.locked_fast(b), fam.states,
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
