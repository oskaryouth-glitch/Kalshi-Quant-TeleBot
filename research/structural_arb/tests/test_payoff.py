from fractions import Fraction as Fr

import pytest

from sarb import payoff as P


class Env:
    """Minimal exact envelope for tests (inner == outer unless given)."""
    def __init__(self, inner, outer=None):
        self.inner, self.outer = tuple(inner), tuple(outer if outer is not None else inner)
    def sure_yes(self, x): return any(i.contains(x) for i in self.inner)
    def maybe_yes(self, x): return any(i.contains(x) for i in self.outer)
    def breakpoints(self): return {b for i in self.inner + self.outer for b in i.breakpoints()}


def test_interval_endpoints_and_repr():
    assert P.ge(50).contains(Fr(50)) and not P.gt(50).contains(Fr(50))
    assert P.le(50).contains(Fr(50)) and not P.lt(50).contains(Fr(50))
    assert P.closed(1, 2).contains(Fr(2)) and not P.closed_open(1, 2).contains(Fr(2))
    assert repr(P.closed_open(1, 2)) == "[1,2)" and repr(P.gt(3)) == "(3,+inf)"


def test_atoms_cover_points_gaps_and_tails():
    assert P.atoms({Fr(1), Fr(3)}) == [Fr(0), Fr(1), Fr(2), Fr(3), Fr(4)]
    assert P.atoms([]) == [Fr(0)]


def test_truth_invariant():
    with pytest.raises(ValueError):
        P.Truth(True, False)


def test_yes_plus_no_same_event_requires_distinct_markets():
    with pytest.raises(ValueError):
        P.verify([P.Position("A", "yes"), P.Position("A", "no")], [P.State("s", {"A": P.YES_T})])


def test_gt_vs_ge_boundary_state_exists():
    states = P.interval_states({"A": Env([P.ge(50)]), "B": Env([P.gt(50)])}, include_all_no=False)
    r = P.verify([P.Position("A", "yes"), P.Position("B", "no")], states)
    assert r.min_payoff == 1
    assert sorted(l for l, v in zip(r.labels, r.payoffs) if v == 2) == ["X=50"]


def test_all_no_state_breaks_yes_cover():
    envs = {"LO": Env([P.lt(10)]), "HI": Env([P.ge(10)])}
    pos = [P.Position("LO", "yes"), P.Position("HI", "yes")]
    assert P.verify(pos, P.interval_states(envs, False)).min_payoff == 1
    r = P.verify(pos, P.interval_states(envs, True))
    assert r.min_payoff == 0 and r.argmin.startswith("ALL_NO")


def test_uncertain_envelope_is_adversarial():
    # inner (5,6) outer [5,6]: YES credited only strictly inside, NO only strictly outside
    envs = {"A": Env([P.open_(5, 6)], [P.closed(5, 6)])}
    st = P.interval_states(envs, False)
    y = P.verify([P.Position("A", "yes")], st)
    n = P.verify([P.Position("A", "no")], st)
    at5 = y.labels.index("X=5")
    assert y.payoffs[at5] == 0 and n.payoffs[at5] == 0


def test_categorical_states_at_most_one_winner_plus_none():
    st = P.categorical_states(["A", "B", "C"])
    assert len(st) == 4
    assert all(sum(t.sure_yes for t in s.truth.values()) <= 1 for s in st)


def test_binary_product_states_and_derived():
    st = P.binary_product_states(["A", "B"], {"C": lambda e: e["A"] and not e["B"]})
    assert len(st) == 4
    assert [s.truth["C"].sure_yes for s in st] == [False, False, True, False]


def test_one_leg_discretionary_worst():
    envs = {"LO": Env([P.lt(10)]), "HI": Env([P.ge(10)])}
    st = P.interval_states(envs, False)
    pos = [P.Position("LO", "no"), P.Position("HI", "no")]          # disjoint -> locked 1
    assert P.verify(pos, st).min_payoff == 1
    assert P.one_leg_discretionary_worst(pos, st) == 0              # the paying leg goes 'scalar' at 0
