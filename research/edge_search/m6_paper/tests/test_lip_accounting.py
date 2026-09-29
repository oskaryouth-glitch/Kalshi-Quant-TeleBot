"""Reward scoring equals the PT1-frozen algorithm; fees, netting and valuation."""
import random
from decimal import Decimal as D

import m6_rewards as PT1                      # PT1-frozen functions (price_test_1/m6_rewards.py)
import pt1_common as P1
from m6_paper import accounting as A
from m6_paper import lip


def rand_book(rng):
    def side():
        return [[f"{p / 100:.4f}", f"{rng.choice([0, 5, 50, 200, 800, 3000])}.00"] for p in sorted(rng.sample(range(1, 99), rng.randint(0, 8)))]
    return {"yes_dollars": side(), "no_dollars": side()}


def test_configure_and_share_equal_pt1_on_random_books():
    rng = random.Random(7)
    ranges = [{"start": "0.0000", "end": "1.0000", "step": "0.0100"}]
    for _ in range(400):
        book = rand_book(rng)
        py, pn, mode, yb, nb, _ = PT1.configure(book, {"price_ranges": ranges})
        assert lip.configure(book, ranges) == (py, pn, mode)
        T, d, x = D(rng.choice([100, 1000, 2500])), D("0.5"), D(rng.randint(1, 300))
        assert lip.side_share(yb, [(py, x)], T, d, ranges) == PT1.side_share(yb, py, x, T, d, ranges)
        assert lip.side_share(nb, [(pn, x)], T, d, ranges) == PT1.side_share(nb, pn, x, T, d, ranges)


def test_two_own_orders_at_one_price_score_like_one():
    others = [(D("0.40"), D("900")), (D("0.39"), D("500"))]
    a = lip.side_share(others, [(D("0.40"), D("3")), (D("0.40"), D("7"))], D(1000), D("0.5"), None)
    assert a == lip.side_share(others, [(D("0.40"), D("10"))], D(1000), D("0.5"), None)


def test_excluded_snapshot_scores_zero():
    book = {"yes_dollars": [["0.40", "10"]], "no_dollars": [["0.55", "5000"]]}
    assert lip.snapshot_score(book, [(D("0.40"), D(5))], [(D("0.55"), D(5))], D(1000), D("0.5"), None) == 0


def test_fee_matches_pt1_and_rounds_up():
    for p in ("0.01", "0.37", "0.50", "0.99"):
        for n in ("1", "7", "123.45"):
            assert A.fee(D(p), D(n), D(1), A.S.MAKER_COEF) == P1.fee(D(p), D(n), D(1), P1.MAKER_COEF)[0]
            assert A.fee(D(p), D(n), D(1), A.S.MAKER_COEF, A.S.NONDIRECT_G) == P1.fee(D(p), D(n), D(1), P1.MAKER_COEF)[1]
    assert A.maker_fee("quadratic", D(1), D("0.5"), D(100)) == 0
    assert A.maker_fee("quadratic_with_maker_fees", D(1), D("0.5"), D(100)) == D("0.4375")


def fill(side, p, n, fee="0"):
    return A.Fill(0, side, D(p), D(n), D(fee), D(fee), "e", "queue")


def test_netting_pairs_release_capital_and_keep_q():
    pos = A.Position()
    pos.apply(fill("yes", "0.40", 10))
    assert pos.q == 10 and pos.inventory_cost == D("4.00")
    pos.apply(fill("no", "0.55", 4))
    assert pos.q == 6 and pos.pairs_redeemed == 4 and pos.inventory_cost == D("2.40")


def test_valuation_totals_equal_pairs_plus_marked_net():
    pos = A.Position()
    fs = [fill("yes", "0.40", 10), fill("no", "0.55", 4)]
    for f in fs:
        pos.apply(f)
    vy, vn, how = A.contract_values(None, D("0.30"), D("0.60"), pos.q, D(1))
    m = D("0.30") - A.fee(D("0.30"), D(1), D(1), A.S.TAKER_COEF)
    assert how == "liquidation" and vy == m
    total = sum(A.fill_pnl(f, vy, vn) for f in fs)
    assert total == (4 * D(1) + 6 * m) - (D("4.00") + D("2.20"))
    vy, vn, how = A.contract_values(D(1), None, None, pos.q, D(1))
    assert sum(A.fill_pnl(f, vy, vn) for f in fs) == 10 * D(1) - D("6.20")
    assert A.contract_values(None, None, None, D(3), D(1))[0] == 0          # no bid -> worthless
