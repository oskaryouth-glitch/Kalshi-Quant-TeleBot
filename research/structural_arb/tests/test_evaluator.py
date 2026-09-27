"""End-to-end gate behaviour of the evaluator on synthetic, fully controlled snapshots."""
from decimal import Decimal as D
from fractions import Fraction as Fr

import pytest

from sarb import fees as FEES
from sarb import payoff as P
from sarb import relationships as R
from sarb.evaluator import BookObs, MarketMeta, evaluate
from sarb.orderbook import parse_orderbook
from sarb.semantics import Envelope, MarketSpec

S = 1_000_000_000
NOW_UTC = 1_790_000_000 * S


def spec(t, iv, verified=True, event="E", all_no=False):
    s = MarketSpec(t, event, "KXTEST", "x")
    s.envelope = Envelope((iv,), (iv,))
    s.direction = "up" if iv.hi is None else "down" if iv.lo is None else "range"
    s.family_key, s.no_data_all_no = "FAM", all_no
    s.terms_status = "TERMS_VERIFIED" if verified else "TERMS_UNVERIFIED"
    return s


def book(t, yes, no, sent=0, recv=S // 10, code=200, x_cache=None):
    ob = parse_orderbook(t, {"orderbook_fp": {"yes_dollars": yes, "no_dollars": no}})
    return BookObs(ob, code, sent, recv, NOW_UTC - S + sent, NOW_UTC - S + recv, x_cache)


def meta(t, last="0.40", status="active"):
    return MarketMeta(t, "KXTEST", "E", status, NOW_UTC + 3600 * S, D(last) if last else None, NOW_UTC + 86400 * S, 0)


FEE = {t: FEES.ResolvedFee("quadratic", D(1), "test") for t in ("A", "B", "C", "D", "E0", "E1", "E2")}


def structural(rel, specs, sides=None):
    out = R.numeric_family_templates(R.Family(specs))
    cands = [s for s in out if s.relationship == rel]
    if sides:
        cands = [s for s in cands if tuple((p.ticker, p.side) for p in s.positions) == sides]
    assert cands, (rel, [s.relationship for s in out])
    return cands[0]


def r2_setup(verified=True):
    # A: X > 10 (big)   B: X > 12 (small)   => YES_A + NO_B locks $1
    st = structural("R2_NESTED", [spec("A", P.gt(10), verified), spec("B", P.gt(12), verified)])
    books = {
        "A": book("A", [["0.30", "50"]], [["0.60", "5"], ["0.40", "100"]]),     # YES ask A: 5@0.40, 100@0.60
        "B": book("B", [["0.47", "50"]], [["0.40", "50"]], sent=S // 10, recv=S // 5),  # NO ask B: 50@0.53
    }
    metas = {"A": meta("A", "0.40"), "B": meta("B", "0.47")}
    return st, books, metas


def run(st, books, metas, fees=FEE, persist=True, now_mono=S, active=True, ex_fetched=0, consistent=True):
    cons = {t: consistent for t in books} if isinstance(consistent, bool) else consistent
    return evaluate(st, books, metas, fees, active, now_mono, NOW_UTC, persist,
                    exchange_fetched_mono_ns=ex_fetched, metadata_consistent=cons)


def test_true_lock_all_gates_pass_is_rule_defined_lock():
    st, books, metas = r2_setup()
    out, rec = run(st, books, metas)
    assert out == "LOGGED" and rec.status == "RULE_DEFINED_LOCK", rec.reasons
    assert D(rec.raw_inconsistency) == D("0.47") - D("0.40")      # closed form: yes_bid_small - yes_ask_big
    assert rec.max_executable_size == "5"                          # depth at 0.40 is 5; next level kills edge
    edges = rec.extra["edges_by_size"]["1"]
    assert D(edges["direct_expected"]) > D(edges["direct_bound"]) > D(edges["nondirect_conservative"]) > 0
    assert rec.extra["edges_by_size"]["100"] == "INSUFFICIENT_DEPTH"          # B shows only 50
    assert all(D(v) < 0 for v in rec.extra["edges_by_size"]["10"].values())  # walks into A's 0.60 level
    assert "RULEBOOK_6.3c" in rec.extra["residual_risks"][0]


def test_persistence_not_confirmed_blocks_label():
    st, books, metas = r2_setup()
    _, rec = run(st, books, metas, persist=None)
    assert rec.status == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE" and "FAIL:persistence_confirmed" in rec.reasons


def test_asynchronous_legs_rejected():
    """The two books were observed 3 s apart: the displayed 'lock' may never have coexisted."""
    st, books, metas = r2_setup()
    books["B"] = book("B", [["0.47", "50"]], [["0.40", "50"]], sent=3 * S, recv=3 * S + S // 10)
    _, rec = run(st, books, metas, now_mono=3 * S + S // 5)
    assert rec.status == "REJECTED" and "FAIL:skew_ok" in rec.reasons


def test_stale_snapshot_rejected():
    st, books, metas = r2_setup()
    _, rec = run(st, books, metas, now_mono=30 * S)
    assert rec.status == "REJECTED" and "FAIL:age_ok" in rec.reasons


@pytest.mark.parametrize("mutate,reason", [
    (lambda b, m: b.__setitem__("A", book("A", [["0.30", "5"]], [["0.60", "5"]], x_cache="Hit from cloudfront")), "CDN_CACHE_HIT:A"),
    (lambda b, m: b.__setitem__("A", book("A", [["0.45", "5"]], [["0.60", "5"]])), "BOOK_CROSSED_OR_LOCKED:A"),
    (lambda b, m: b.__setitem__("A", book("A", [["0.40", "5"]], [["0.60", "5"]])), "BOOK_CROSSED_OR_LOCKED:A"),
    (lambda b, m: b.__setitem__("A", book("A", [], [], code=429)), "BOOK_UNAVAILABLE:A"),
])
def test_book_integrity_rejections(mutate, reason):
    st, books, metas = r2_setup()
    mutate(books, metas)
    out, rec = run(st, books, metas)
    assert out == "LOGGED" and rec.status == "REJECTED" and reason in rec.reasons


def test_inactive_market_and_exchange_halt_rejected():
    st, books, metas = r2_setup()
    metas["B"] = meta("B", "0.47", status="inactive")
    assert run(st, books, metas)[1].status == "REJECTED"
    st, books, metas = r2_setup()
    _, rec = run(st, books, metas, active=False)
    assert rec.status == "REJECTED" and "FAIL:exchange_trading_active" in rec.reasons


def test_unresolved_fee_rejected():
    st, books, metas = r2_setup()
    fees = dict(FEE)
    fees["B"] = FEES.UnsupportedFee("flat")
    _, rec = run(st, books, metas, fees=fees)
    assert rec.status == "FEE_UNRESOLVED" and "FAIL:fees_resolved" in rec.reasons
    assert "B" in rec.extra["fee_unresolved"]


def test_unverified_terms_capped():
    st, books, metas = r2_setup(verified=False)
    _, rec = run(st, books, metas)
    assert rec.status == "CANDIDATE_TERMS_UNVERIFIED"


def test_rule_5_11_far_from_last_price():
    st, books, metas = r2_setup()
    metas["A"] = meta("A", "0.75")                 # executing YES at 0.40 when last traded 0.75
    _, rec = run(st, books, metas)
    assert rec.status == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"
    assert "FAIL:rule_5_11_within_no_cancel_range" in rec.reasons


def test_missing_last_price_fails_rule_5_11_gate():
    st, books, metas = r2_setup()
    metas["A"] = meta("A", None)
    _, rec = run(st, books, metas)
    assert "FAIL:rule_5_11_within_no_cancel_range" in rec.reasons


def test_consistent_prices_not_logged_and_missing_ask_counted():
    st, books, metas = r2_setup()
    books["B"] = book("B", [["0.39", "50"]], [["0.40", "50"]], sent=S // 10, recv=S // 5)   # bid_small < ask_big
    assert run(st, books, metas) == ("CONSISTENT", None)
    books["B"] = book("B", [], [["0.40", "50"]], sent=S // 10, recv=S // 5)                 # no YES bid -> no NO ask
    assert run(st, books, metas) == ("NO_ASK", None)


def test_direct_positive_but_broker_rounding_negative():
    """NO_A + NO_B on disjoint sets locks $1. Sub-cent price 0.475 is off the cent grid, so the
    conservative non-direct bound (+1 cent per fill) flips the sign."""
    st = structural("R1_EXCLUSIVE_PAIR", [spec("A", P.lt(10)), spec("B", P.gt(20))])
    books = {"A": book("A", [["0.52", "10"]], [["0.30", "10"]]),
             "B": book("B", [["0.525", "10"]], [["0.30", "10"]], sent=S // 10, recv=S // 5)}
    metas = {"A": meta("A", "0.52"), "B": meta("B", "0.52")}
    _, rec = run(st, books, metas)
    e = rec.extra["edges_by_size"]["1"]
    assert D(e["direct_expected"]) > 0 and D(e["direct_bound"]) > 0 and D(e["nondirect_conservative"]) < 0
    assert rec.status == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"
    assert "FAIL:edge_positive_all_scenarios_some_size" in rec.reasons


def test_r1_long_gap_is_statistical_even_if_asks_sum_below_one():
    ivs = [P.lt(100), P.closed(100, P.F("199.99")), P.closed(200, P.F("299.99")), P.gt(P.F("299.99"))]
    specs = [spec(f"E{i}", iv, event="EV") for i, iv in enumerate(ivs)]
    st = structural("R1_LONG", specs)
    books = {f"E{i}": book(f"E{i}", [["0.10", "10"]], [["0.78", "10"]], sent=i * S // 20, recv=i * S // 20 + S // 20)
             for i in range(3)}
    books["E3"] = book("E3", [["0.05", "10"]], [["0.80", "10"]], sent=S // 5, recv=S // 4)
    metas = {t: meta(t, "0.22") for t in books}
    fees = {t: FEES.ResolvedFee("quadratic", D(1), "t") for t in books}
    out, rec = run(st, books, metas, fees=fees)
    # asks: 0.22*3 + 0.20 = 0.86 < 1, but (199.99, 200) is an uncovered real state
    assert out == "LOGGED" and rec.status == "STATISTICAL"
    assert any(r.startswith("NOT_LOCKED:min_payoff=0@X=") for r in rec.reasons)


def test_rule_5_11_rejections_are_flagged_for_separate_logging():
    st, books, metas = r2_setup()
    metas["A"] = meta("A", "0.75")
    _, rec = run(st, books, metas, persist=None)
    assert rec.status == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"                  # still a hard gate
    assert rec.extra["rule_5_11"] == {"blocked_by_rule_5_11": True, "only_rule_5_11_and_or_persistence_failed": True}
    # still re-fetched for persistence (to measure what the gate removes) but can never be a lock
    assert rec.extra["persistence_eligible"] is True
    _, rec2 = run(st, books, metas, persist=True)
    assert rec2.status == "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"


def test_persistence_eligibility_and_unwind():
    st, books, metas = r2_setup()
    _, rec = run(st, books, metas, persist=None)
    assert rec.extra["persistence_eligible"] is True
    u = rec.extra["unwind"]["1"]
    assert u["complete"] and set(u["per_leg"]) == {"A", "B"}
    # buy YES A at 0.40 then sell back at YES bid 0.30 -> loss >= 0.10 + fees
    assert D(u["per_leg"]["A"]["loss"]) > D("0.10")
    losses = sorted(D(v["loss"]) for v in u["per_leg"].values())
    assert D(u["worst_partial_fill_unwind_loss"]) == losses[1]


def test_unwind_with_no_bids_values_leg_at_zero():
    st, books, metas = r2_setup()
    books["A"] = book("A", [], [["0.60", "5"], ["0.40", "100"]])
    _, rec = run(st, books, metas, persist=None)
    leg = rec.extra["unwind"]["1"]["per_leg"]["A"]
    assert D(leg["unwind_proceeds"]) == 0 and D(leg["loss"]) == D(leg["cash_out"])


def test_unchecked_template_is_rejected():
    fam = R.Family([spec("A", P.gt(10)), spec("B", P.gt(12))])
    st = R.pair_struct(fam, "A", "yes", "B", "no", lazy=True)
    assert not st.checked
    _, books, metas = r2_setup()
    _, rec = run(st, books, metas)
    assert rec.status == "REJECTED" and "FAIL:no_checker_bug" in rec.reasons
    R.check(st)
    assert run(st, books, metas)[1].status == "RULE_DEFINED_LOCK"


# ------------------------------------------------------------------ fall-through matrix (methodology audit)
import itertools as _it


def _perturbations():
    """Each returns (name, mutate(ctx)) where ctx = dict(st, books, metas, fees, kw)."""
    def unverified(c): c["st"].terms_verified = False
    def fee_unresolved(c): c["fees"] = {**c["fees"], "B": FEES.UnsupportedFee("FEE_UNRESOLVED:EVENT_OBSERVATION_STALE")}
    def rate_limited(c): c["books"]["A"] = book("A", [], [], code=429)
    def missing_book(c): c["books"].pop("B")
    def crossed(c): c["books"]["A"] = book("A", [["0.45", "5"]], [["0.60", "5"]])
    def cdn_hit(c): c["books"]["A"] = book("A", [["0.30", "50"]], [["0.40", "100"], ["0.60", "5"]], x_cache="Hit from cloudfront")
    def checker_bug(c): c["st"].notes.append("BUG_TEMPLATE_VS_CHECKER fast=1 checker=0")
    def unchecked(c): c["st"].checked = False
    def statistical(c): c["st"].relationship_class = "STATISTICAL"
    def not_locked(c): c["st"].locked = Fr(0)
    def metadata_changed(c): c["kw"]["metadata_consistent"] = {"A": True, "B": False}
    def metadata_absent(c): c["kw"]["metadata_consistent"] = None
    def exchange_stale(c): c["kw"]["exchange_fetched_mono_ns"] = None
    def exchange_halted(c): c["kw"]["active"] = False
    def market_inactive(c): c["metas"]["B"] = meta("B", "0.47", status="inactive")
    def skew(c): c["books"]["B"] = book("B", [["0.47", "50"]], [["0.40", "50"]], sent=3 * S, recv=3 * S + 1); c["kw"]["now_mono"] = 3 * S + 2
    def stale(c): c["kw"]["now_mono"] = 60 * S
    def no_persistence(c): c["kw"]["persist"] = None
    def rule_5_11(c): c["metas"]["A"] = meta("A", "0.75")
    def no_last_price(c): c["metas"]["A"] = meta("A", None)
    def no_edge(c): c["books"]["B"] = book("B", [["0.39", "50"]], [["0.40", "50"]], sent=S // 10, recv=S // 5)
    def thin_edge(c): c["books"]["B"] = book("B", [["0.415", "50"]], [["0.40", "50"]], sent=S // 10, recv=S // 5)
    def fee_high(c): c["fees"] = {t: FEES.ResolvedFee("quadratic", D(3), "t") for t in c["fees"]}
    return [(f.__name__, f) for f in (unverified, fee_unresolved, rate_limited, missing_book, crossed, cdn_hit,
                                      checker_bug, unchecked, statistical, not_locked, metadata_changed, metadata_absent,
                                      exchange_stale, exchange_halted, market_inactive, skew, stale, no_persistence,
                                      rule_5_11, no_last_price, no_edge, thin_edge, fee_high)]


def _ctx():
    st, books, metas = r2_setup()
    return {"st": st, "books": books, "metas": metas, "fees": dict(FEE),
            "kw": {"persist": True, "now_mono": S, "active": True, "ex_fetched": 0,
                   "exchange_fetched_mono_ns": 0, "metadata_consistent": {"A": True, "B": True}}}


def _eval(c):
    kw = c["kw"]
    return evaluate(c["st"], c["books"], c["metas"], c["fees"], kw["active"], kw["now_mono"], NOW_UTC, kw["persist"],
                    exchange_fetched_mono_ns=kw["exchange_fetched_mono_ns"], metadata_consistent=kw["metadata_consistent"])


def test_baseline_is_lock():
    out, rec = _eval(_ctx())
    assert rec.status == "RULE_DEFINED_LOCK"


@pytest.mark.parametrize("combo", [c for k in (1, 2) for c in _it.combinations(range(len(_perturbations())), k)])
def test_no_disqualifier_falls_through_to_lock(combo):
    c = _ctx()
    P_ = _perturbations()
    for i in combo:
        P_[i][1](c)
    try:
        out, rec = _eval(c)
    except KeyError:          # a missing leg can never be evaluated at all
        return
    assert rec is None or rec.status != "RULE_DEFINED_LOCK", [P_[i][0] for i in combo]


def test_rule_5_11_applies_at_the_executed_size_not_only_top_of_book():
    """Top of book sits exactly on the ±$0.20 band edge, the next level is $0.001 beyond it, and the
    edge is positive only at sizes that must walk into that deeper level."""
    st, books, metas = r2_setup()
    books["A"] = book("A", [["0.30", "50"]], [["0.599", "100"], ["0.60", "1"]])   # YES asks 1@0.40, 100@0.401
    books["B"] = book("B", [["0.45", "50"]], [["0.40", "50"]], sent=S // 10, recv=S // 5)  # NO asks 50@0.55
    metas["A"] = meta("A", "0.20")                                                   # fair YES A = 0.20
    metas["B"] = meta("B", "0.45")
    _, rec = run(st, books, metas)
    assert D(rec.extra["rule_5_11_distance"]["A"]) == D("0.20")                     # top of book is inside
    assert rec.max_executable_size is not None and int(rec.max_executable_size) > 1   # economics positive only deeper
    assert rec.extra["max_size_positive_and_rule_5_11"] is None
    assert rec.status != "RULE_DEFINED_LOCK" and "FAIL:rule_5_11_within_no_cancel_range" in rec.reasons
