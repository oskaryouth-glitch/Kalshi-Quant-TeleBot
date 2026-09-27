"""Mechanics of the independent verifier only. Relationship templates (R1-R5) are tested
against this verifier after the checkpoint review."""
from fractions import Fraction as Fr
import pytest
from sarb.payoff import (Position, verify, on, gt, ge, lt, le, closed_open, closed, And, Not, atoms, state_space, Interval)


def test_interval_endpoints():
    assert ge(50).contains(Fr(50)) and not gt(50).contains(Fr(50))
    assert le(50).contains(Fr(50)) and not lt(50).contains(Fr(50))
    iv = closed_open(1, 2)
    assert iv.contains(Fr(1)) and not iv.contains(Fr(2)) and iv.contains(Fr(3, 2))
    assert closed(1, 2).contains(Fr(2))
    assert Interval().contains(Fr(-10 ** 9))


def test_atoms_cover_points_and_gaps():
    assert atoms({Fr(1), Fr(3)}) == [Fr(0), Fr(1), Fr(2), Fr(3), Fr(4)]
    assert atoms(set()) == [Fr(0)]


def test_yes_plus_no_same_event_is_one_everywhere():
    e = on("X", ge(50))
    r = verify([Position(e, "yes"), Position(e, "no")])
    assert set(r.payoffs) == {1}


def test_gt_vs_ge_distinguished_at_boundary():
    # YES(X>=50) + NO(X>50): pays 2 only when X == 50 exactly
    r = verify([Position(on("X", ge(50)), "yes"), Position(on("X", gt(50)), "no")])
    two = [s["X"] for s, p in zip(r.states, r.payoffs) if p == 2]
    assert two == [Fr(50)] and r.min_payoff == 1


def test_qty_and_multi_underlying_product_space():
    a, b = on("A", ge(0)), on("B", ge(0))
    r = verify([Position(And((a, b)), "yes", Fr(3))])
    assert len(r.states) == 9 and r.max_payoff == 3 and r.min_payoff == 0
    assert sum(1 for p in r.payoffs if p == 3) == 4   # A>=0 in 2 atoms x B>=0 in 2 atoms


def test_not_and_filter():
    e = on("X", closed_open(0, 10))
    r = verify([Position(Not(e), "yes")], state_filter=lambda s: 0 <= s["X"] < 10)
    assert set(r.payoffs) == {0}
    with pytest.raises(ValueError):
        verify([Position(e, "yes")], state_filter=lambda s: False)


def test_bad_side():
    with pytest.raises(ValueError):
        verify([Position(on("X", ge(1)), "maybe")])
