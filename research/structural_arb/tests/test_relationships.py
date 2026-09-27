"""Randomized attempts to FALSIFY every structural relationship.

Three independent computations must agree:
  (1) template bitmask pass (relationships.Family.locked_fast)
  (2) State-based brute-force checker (payoff.verify)            -> Structural.locked
  (3) direct dense sampling of X using raw interval membership (this file, no payoff.py code)
plus closed-form lock conditions from interval arithmetic (this file).
"""
import itertools
import random
from decimal import Decimal as D
from fractions import Fraction as Fr

import pytest

from sarb import payoff as P
from sarb import relationships as R
from sarb.semantics import Envelope, MarketSpec

# ---------------------------------------------------------------- helpers (independent of sarb.payoff logic)


def contains(iv, x):
    lo_ok = iv.lo is None or x > iv.lo or (x == iv.lo and iv.lo_closed)
    hi_ok = iv.hi is None or x < iv.hi or (x == iv.hi and iv.hi_closed)
    return lo_ok and hi_ok


def spec(t, inner, outer=None, event="E", direction=None, all_no=False, verified=True):
    s = MarketSpec(t, event, "S", "x")
    s.envelope = Envelope(tuple(inner), tuple(outer if outer is not None else inner))
    iv = inner[0] if inner else outer[0]
    s.direction = direction or ("up" if iv.hi is None else "down" if iv.lo is None else "range")
    s.family_key, s.no_data_all_no = "FAM", all_no
    s.terms_status = "TERMS_VERIFIED" if verified else "TERMS_UNVERIFIED"
    return s


def rand_interval(rng, lo=0, hi=12):
    kind = rng.choice(["gt", "ge", "lt", "le", "cc", "co", "oc", "oo"])
    a = Fr(rng.randint(lo, hi), rng.choice([1, 2]))
    if kind in ("gt", "ge"):
        return P.Interval(a, kind == "ge", None, False)
    if kind in ("lt", "le"):
        return P.Interval(None, False, a, kind == "le")
    b = a + Fr(rng.randint(0 if kind == "cc" else 1, 6), rng.choice([1, 2]))
    return P.Interval(a, kind[0] == "c", b, kind[1] == "c")


def sample_points(specs):
    bps = sorted({b for s in specs for iv in s.envelope.inner + s.envelope.outer for b in iv.breakpoints()} | {Fr(0)})
    pts = set()
    for b in bps:
        for d in (Fr(0), Fr(1, 10**6), -Fr(1, 10**6), Fr(1, 3), -Fr(1, 3)):
            pts.add(b + d)
    for k in range(-40, 120):
        pts.add(Fr(k, 7))
    pts |= {bps[0] - 1000, bps[-1] + 1000}
    return sorted(pts)


def direct_payoff(specs, positions, x, all_no=False):
    by = {s.ticker: s for s in specs}
    tot = Fr(0)
    for p in positions:
        e = by[p.ticker].envelope
        if all_no:
            tot += 0 if p.side == "yes" else 1
        elif p.side == "yes":
            tot += 1 if any(contains(iv, x) for iv in e.inner) else 0
        else:
            tot += 0 if any(contains(iv, x) for iv in e.outer) else 1
    return tot


def check_against_direct(specs, st, all_no):
    pts = sample_points(specs)
    vals = [direct_payoff(specs, st.positions, x) for x in pts]
    if all_no:
        vals.append(direct_payoff(specs, st.positions, None, all_no=True))
    # (a) nothing below the checker's min; (b) the checker's argmin is reproduced exactly
    assert min(vals) >= st.locked, (st.relationship, st.positions, st.locked, min(vals))
    if st.argmin_state.startswith("X="):
        x = Fr(st.argmin_state[2:])
        assert direct_payoff(specs, st.positions, x) == st.locked
    else:
        assert direct_payoff(specs, st.positions, None, all_no=True) == st.locked


def subset(a, b):
    """Closed-form: interval a ⊆ interval b (exact, single intervals)."""
    lo_ok = b.lo is None or (a.lo is not None and (a.lo > b.lo or (a.lo == b.lo and (b.lo_closed or not a.lo_closed))))
    hi_ok = b.hi is None or (a.hi is not None and (a.hi < b.hi or (a.hi == b.hi and (b.hi_closed or not a.hi_closed))))
    empty = a.lo is not None and a.hi is not None and (a.lo > a.hi or (a.lo == a.hi and not (a.lo_closed and a.hi_closed)))
    return empty or (lo_ok and hi_ok)


def disjoint(a, b):
    lo = max((a.lo, a.lo_closed), (b.lo, b.lo_closed), key=lambda t: (float("-inf") if t[0] is None else t[0], not t[1]))
    hi = min((a.hi, a.hi_closed), (b.hi, b.hi_closed), key=lambda t: (float("inf") if t[0] is None else t[0], t[1]))
    if lo[0] is None or hi[0] is None:
        return False
    return lo[0] > hi[0] or (lo[0] == hi[0] and not (lo[1] and hi[1]))


def covers_line(a, b):
    """a ∪ b = ℝ (closed form for two intervals)."""
    for x, y in ((a, b), (b, a)):
        if x.lo is None and y.hi is None:   # (-inf, x.hi?] ∪ [y.lo?, +inf)
            if x.hi is None or y.lo is None:
                return True
            if x.hi > y.lo or (x.hi == y.lo and (x.hi_closed or y.lo_closed)):
                return True
    return (a.lo is None and a.hi is None) or (b.lo is None and b.hi is None)


# ---------------------------------------------------------------- randomized ideal families


@pytest.mark.parametrize("seed", range(120))
def test_random_ideal_families_all_templates(seed):
    rng = random.Random(seed)
    all_no = rng.random() < 0.4
    n = rng.randint(2, 6)
    specs = [spec(f"M{i}", [rand_interval(rng)], event=rng.choice(["E1", "E2"]), all_no=all_no) for i in range(n)]
    fam = R.Family(specs)
    out = R.numeric_family_templates(fam)
    for st in out:
        assert not st.notes, st.notes                                   # template == checker, never exceeds nominal
        check_against_direct(specs, st, all_no)
        assert st.relationship_class == ("GUARANTEED" if st.locked >= st.nominal_locked and st.locked > 0 else "STATISTICAL")
    # closed-form lock conditions vs emitted pair templates
    iv = {s.ticker: s.envelope.inner[0] for s in specs}
    emitted = {(st.relationship, tuple((p.ticker, p.side) for p in st.positions)) for st in out}
    for a, b in itertools.combinations(sorted(iv), 2):
        a_in_b, b_in_a = subset(iv[b], iv[a]), subset(iv[a], iv[b])   # E_b ⊆ E_a  <=> YES_a+NO_b locks
        if a_in_b and b_in_a:
            assert ("R4_DUPLICATE", ((a, "yes"), (b, "no"))) in emitted
        elif a_in_b:
            assert ("R2_NESTED", ((a, "yes"), (b, "no"))) in emitted
        elif b_in_a:
            assert ("R2_NESTED", ((b, "yes"), (a, "no"))) in emitted
        else:
            assert not any(r in ("R2_NESTED", "R4_DUPLICATE") and {t for t, _ in pos} == {a, b} for r, pos in emitted)
        assert (("R1_EXCLUSIVE_PAIR", ((a, "no"), (b, "no"))) in emitted) == disjoint(iv[a], iv[b])
        assert (("R4_COVER_PAIR", ((a, "yes"), (b, "yes"))) in emitted) == (covers_line(iv[a], iv[b]) and not all_no)


def partition(rng, k):
    """Exact partition of ℝ: (-inf,b1) [b1,b2) ... [bk,+inf)."""
    bs = sorted(rng.sample(range(0, 40), k))
    ivs = [P.Interval(None, False, Fr(bs[0]), False)]
    ivs += [P.Interval(Fr(bs[i]), True, Fr(bs[i + 1]), False) for i in range(k - 1)]
    ivs += [P.Interval(Fr(bs[-1]), True, None, False)]
    return bs, ivs


@pytest.mark.parametrize("seed", range(60))
def test_r1_on_exact_partitions(seed):
    rng = random.Random(seed)
    bs, ivs = partition(rng, rng.randint(2, 7))
    for all_no in (False, True):
        specs = [spec(f"B{i}", [iv], event="E", all_no=all_no) for i, iv in enumerate(ivs)]
        out = {s.relationship: s for s in R.numeric_family_templates(R.Family(specs)) if s.relationship.startswith("R1_") and s.relationship != "R1_EXCLUSIVE_PAIR"}
        n = len(ivs)
        assert out["R1_SHORT"].locked == (n - 1) and out["R1_SHORT"].relationship_class == "GUARANTEED"
        if all_no:   # "no data -> all No" (crypto terms) kills the YES basket
            assert out["R1_LONG"].locked == 0 and out["R1_LONG"].argmin_state.startswith("ALL_NO")
            assert out["R1_LONG"].relationship_class == "STATISTICAL"
        else:
            assert out["R1_LONG"].locked == 1 and out["R1_LONG"].relationship_class == "GUARANTEED"
        for st in out.values():
            check_against_direct(specs, st, all_no)


@pytest.mark.parametrize("seed", range(40))
def test_r1_long_with_real_gaps_is_not_locked(seed):
    """Kalshi-style buckets [a, a+w-0.01] leave real gaps (e.g. (72499.99, 72500))."""
    rng = random.Random(seed)
    w, k, a0 = Fr(rng.choice([1, 5, 25])), rng.randint(2, 6), Fr(rng.randint(0, 50))
    ivs = [P.Interval(None, False, a0, False)]
    ivs += [P.Interval(a0 + i * w, True, a0 + (i + 1) * w - Fr(1, 100), True) for i in range(k)]
    ivs += [P.Interval(a0 + k * w - Fr(1, 100), False, None, False)]
    specs = [spec(f"B{i}", [iv], event="E") for i, iv in enumerate(ivs)]
    out = {s.relationship: s for s in R.numeric_family_templates(R.Family(specs))}
    lg = out["R1_LONG"]
    assert lg.locked == 0 and lg.relationship_class == "STATISTICAL"
    gap_x = Fr(lg.argmin_state[2:])
    assert not any(contains(iv, gap_x) for iv in ivs)          # it really is a gap
    assert out["R1_SHORT"].locked == len(ivs) - 1


@pytest.mark.parametrize("seed", range(40))
def test_r3_threshold_vs_buckets(seed):
    rng = random.Random(seed)
    bs, ivs = partition(rng, rng.randint(3, 7))
    j = rng.randint(1, len(bs) - 2)            # at least two buckets inside T (generator needs |S| >= 2)
    T = P.Interval(Fr(bs[j]), True, None, False)                          # T = union of buckets above bs[j]
    specs = [spec(f"B{i}", [iv], event="EB") for i, iv in enumerate(ivs)] + [spec("T", [T], event="ET")]
    out = [s for s in R.numeric_family_templates(R.Family(specs)) if s.relationship.startswith("R3")]
    a = next(s for s in out if s.relationship == "R3_RANGE_A")
    b = next(s for s in out if s.relationship == "R3_RANGE_B")
    S = [p.ticker for p in a.positions if p.side == "yes"]
    assert S == [f"B{i}" for i in range(j + 1, len(ivs))]                 # exactly the buckets inside T
    assert a.locked == 1 and b.locked == len(S) == b.nominal_locked
    # misaligned threshold (starts mid-bucket): B is no longer locked at |S|, A still is
    T2 = P.Interval(Fr(bs[j]) + Fr(1, 2), True, None, False)
    specs2 = specs[:-1] + [spec("T", [T2], event="ET")]
    out2 = {s.relationship: s for s in R.numeric_family_templates(R.Family(specs2)) if s.relationship.startswith("R3")}
    assert out2["R3_RANGE_A"].locked == 1
    assert out2["R3_RANGE_B"].locked < out2["R3_RANGE_B"].nominal_locked
    assert out2["R3_RANGE_B"].relationship_class == "STATISTICAL"
    for st in out + list(out2.values()):
        check_against_direct(specs2 if st in out2.values() else specs, st, False)


# ---------------------------------------------------------------- envelope conservativeness


def concrete_variants(iv):
    """Plausible concrete readings of an uncertain interval: endpoint inclusivity and ±0.0001 offsets."""
    out = set()
    for lc in ((True, False) if iv.lo is not None else (False,)):
        for hc in ((True, False) if iv.hi is not None else (False,)):
            for dlo in ((Fr(0), Fr(1, 10**4)) if iv.lo is not None else (Fr(0),)):
                out.add(P.Interval(None if iv.lo is None else iv.lo + dlo, lc, iv.hi, hc))
    return sorted(out, key=repr)


@pytest.mark.parametrize("seed", range(40))
def test_envelope_is_never_more_optimistic_than_any_concrete_reading(seed):
    rng = random.Random(seed)
    base = [rand_interval(rng) for _ in range(3)]
    variants = [concrete_variants(iv)[:3] for iv in base]
    envs = []
    for i, vs in enumerate(variants):
        from sarb.semantics import intersect
        inner = intersect(list(vs))
        envs.append(spec(f"M{i}", [inner] if inner else [], vs))
    for sides in itertools.product(("yes", "no"), repeat=3):
        pos = [P.Position(f"M{i}", s) for i, s in enumerate(sides)]
        L_env = P.verify(pos, P.interval_states({s.ticker: s.envelope for s in envs}, False)).min_payoff
        for choice in itertools.product(*variants):
            concrete = {f"M{i}": spec(f"M{i}", [iv]).envelope for i, iv in enumerate(choice)}
            L_c = P.verify(pos, P.interval_states(concrete, False)).min_payoff
            assert L_env <= L_c


def test_identical_markets_with_encoding_uncertainty_are_not_a_lock():
    """INXU-style: fields >= 7550 vs text > 7549.9999. Even an exact duplicate pair can't be
    certified, because (7549.9999, 7550) is a state where neither leg surely pays."""
    inner = [P.Interval(Fr(7550), True, None, False)]
    outer = [P.Interval(Fr(7550), True, None, False), P.Interval(Fr("7549.9999"), False, None, False)]
    specs = [spec("A", inner, outer, event="E1"), spec("B", inner, outer, event="E2")]
    out = R.numeric_family_templates(R.Family(specs))
    assert not any(s.relationship in ("R4_DUPLICATE", "R2_NESTED") for s in out)


# ---------------------------------------------------------------- categorical (MECNET) and combos


@pytest.mark.parametrize("n", [2, 3, 5, 8])
def test_categorical_mecnet(n):
    ts = [f"C{i}" for i in range(n)]
    out = R.categorical_templates("EV", ts, True)
    by = {}
    for s in out:
        by.setdefault(s.relationship, []).append(s)
    assert by["R1_LONG"][0].locked == 0 and by["R1_LONG"][0].relationship_class == "STATISTICAL"   # no-winner state
    assert by["R1_SHORT"][0].locked == n - 1 and by["R1_SHORT"][0].relationship_class == "GUARANTEED"
    assert len(by["R1_EXCLUSIVE_PAIR"]) == n * (n - 1) // 2 and all(s.locked == 1 for s in by["R1_EXCLUSIVE_PAIR"])
    assert R.categorical_templates("EV", ts, False) == []                                       # no MECNET, no claim


@pytest.mark.parametrize("sides", list(itertools.product(("yes", "no"), repeat=3)))
def test_combo_bounds_determinate(sides):
    legs = [{"market_ticker": f"L{i}", "side": s} for i, s in enumerate(sides)]
    out = R.combo_templates("COMBO", legs)
    assert {s.relationship for s in out} == {"R5_COMBO_UPPER", "R5_COMBO_LOWER"}
    assert all(s.locked == 1 and s.relationship_class == "GUARANTEED" for s in out)


def _floor_cent(x: Fr) -> Fr:
    return Fr(int(x * 100), 100)


@pytest.mark.parametrize("seed", range(30))
def test_combo_bounds_under_scalar_component_settlement(seed):
    """Components settled at arbitrary fair values v in [0,1] (Rulebook 6.3(c)). Combo YES pays
    floor_cent(prod of component payouts) (FOOTBALLSTATS terms). Upper stays >= 1; the lower
    bound can lose at most the one-cent floor."""
    rng = random.Random(seed)
    k = rng.randint(2, 4)
    sides = [rng.choice(("yes", "no")) for _ in range(k)]
    for _ in range(200):
        v = [Fr(rng.randint(0, 1000), 1000) if rng.random() < 0.8 else Fr(rng.randint(0, 1)) for _ in range(k)]
        comp = [vi if s == "yes" else 1 - vi for vi, s in zip(v, sides)]   # component payout for the leg's side
        prod = Fr(1)
        for c in comp:
            prod *= c
        combo_yes = _floor_cent(prod)
        for j in range(k):
            assert comp[j] + (1 - combo_yes) >= 1                                # UPPER
        lower = combo_yes + sum((1 - c) for c in comp)
        assert lower >= 1 - Fr(1, 100)                                           # LOWER (cent floor)


def test_combo_rejects_degenerate_leg_lists():
    assert R.combo_templates("C", [{"market_ticker": "A", "side": "yes"}]) == []
    assert R.combo_templates("C", [{"market_ticker": "A", "side": "yes"}, {"market_ticker": "A", "side": "no"}]) == []
    assert R.combo_templates("C", [{"market_ticker": "C", "side": "yes"}, {"market_ticker": "A", "side": "no"}]) == []


def test_r3_skips_threshold_ladders_as_bucket_sets():
    ladder = [spec(f"L{i}", [P.gt(10 + i)], event="LAD") for i in range(4)]
    T = spec("T", [P.ge(11)], event="ET")
    out = R.numeric_family_templates(R.Family(ladder + [T]))
    assert not any(s.relationship.startswith("R3") for s in out)


@pytest.mark.parametrize("seed", range(30))
def test_lazy_templates_check_to_same_result_as_eager(seed):
    rng = random.Random(seed)
    specs = [spec(f"M{i}", [rand_interval(rng)], event=rng.choice(["E1", "E2"]), all_no=rng.random() < 0.4)
             for i in range(rng.randint(2, 6))]
    eager = R.numeric_family_templates(R.Family(specs))
    lazy = R.numeric_family_templates(R.Family(specs), lazy=True)
    assert len(eager) == len(lazy) and not any(s.checked for s in lazy)
    for e, l in zip(eager, lazy):
        R.check(l)
        assert (e.relationship, e.positions, e.locked, e.relationship_class, e.argmin_state,
                e.one_leg_discretionary_worst, e.notes) == \
               (l.relationship, l.positions, l.locked, l.relationship_class, l.argmin_state,
                l.one_leg_discretionary_worst, l.notes)


@pytest.mark.parametrize("seed", range(80))
def test_screen_pairs_equals_full_enumeration_filtered_by_price(seed):
    rng = random.Random(seed)
    specs = [spec(f"M{i}", [rand_interval(rng)], event=rng.choice(["E1", "E2"]), all_no=rng.random() < 0.4)
             for i in range(rng.randint(2, 9))]
    fam = R.Family(specs)
    quotes = {(s.ticker, side): (None if rng.random() < 0.15 else D(rng.randint(1, 99)) / 100)
              for s in specs for side in ("yes", "no")}
    ask = lambda t, side: quotes[(t, side)]  # noqa: E731
    pair_rels = {"R2_NESTED", "R4_DUPLICATE", "R4_COVER_PAIR", "R1_EXCLUSIVE_PAIR"}
    full = {(s.relationship, s.positions) for s in R.numeric_family_templates(fam)
            if s.relationship in pair_rels
            and all(ask(p.ticker, p.side) is not None for p in s.positions)
            and sum(ask(p.ticker, p.side) for p in s.positions) < 1}
    got = R.screen_pairs(fam, ask)
    assert {(s.relationship, s.positions) for s in got} == full
    for s in got:
        R.check(s)
        assert s.checked and not s.notes and s.locked >= 1
