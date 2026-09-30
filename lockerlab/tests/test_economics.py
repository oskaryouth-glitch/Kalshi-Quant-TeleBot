"""Financial-calculation tests. Expected values are computed by hand in the
comments so a reviewer can check the arithmetic independently of the code."""

import dataclasses
import itertools

import pytest

from lockerlab.economics import (
    CostPolicy,
    MarginRules,
    Scenario,
    acquisition_cost,
    constraint_failures,
    evaluate,
    increment_for,
    max_bid,
)

POLICY = CostPolicy(
    buyer_premium_rate=0.15,
    buyer_premium_min_cents=1000,
    sales_tax_rate=0.08,
    tax_applies_to_premium=True,
    cleaning_deposit_cents=10000,
    cleaning_deposit_forfeit_prob=0.05,
    selling_fee_rate=0.07,
    per_order_fee_cents=20,
    packing_cost_per_shipped_order_cents=300,
    shipped_order_share=0.25,
    returns_rate=0.03,
    risk_reserve_rate=0.05,
    labor_rate_cents_per_hour=2000,
)

BASE = Scenario(
    name="base", gross_proceeds_cents=100000, n_orders=10, transport_cost_cents=5000,
    disposal_cost_cents=3000, labor_hours=8.0, retained_cuft=50.0,
)
LOW = dataclasses.replace(BASE, name="low", gross_proceeds_cents=40000, n_orders=5, disposal_cost_cents=6000)
HIGH = dataclasses.replace(BASE, name="high", gross_proceeds_cents=180000, n_orders=14)
SCEN = {"low": LOW, "base": BASE, "high": HIGH}

RULES = MarginRules(
    min_expected_profit_cents=15000,
    target_roi=0.5,
    max_low_case_loss_cents=7500,
    min_profit_per_hour_before_labor_cents=2500,
    bankroll_cents=100000,
)


class TestAcquisition:
    def test_premium_and_tax_on_premium(self):
        # bid 200.00; premium 15% = 30.00; tax 8% of 230.00 = 18.40
        a = acquisition_cost(20000, POLICY)
        assert (a.premium_cents, a.tax_cents, a.total_cents) == (3000, 1840, 24840)

    def test_premium_minimum(self):
        # 15% of 50.00 = 7.50 < 10.00 minimum; tax 8% of 60.00 = 4.80
        a = acquisition_cost(5000, POLICY)
        assert (a.premium_cents, a.tax_cents) == (1000, 480)

    def test_zero_bid_costs_nothing(self):
        assert acquisition_cost(0, POLICY).total_cents == 0

    def test_tax_on_bid_only(self):
        p = dataclasses.replace(POLICY, tax_applies_to_premium=False)
        assert acquisition_cost(20000, p).tax_cents == 1600

    def test_resale_exempt(self):
        p = dataclasses.replace(POLICY, resale_exempt=True)
        assert acquisition_cost(20000, p).tax_cents == 0

    def test_costs_round_up(self):
        # 15% of 1.01 = 0.1515 -> min applies; use a policy with no minimum
        p = dataclasses.replace(POLICY, buyer_premium_min_cents=0, sales_tax_rate=0.0)
        assert acquisition_cost(101, p).premium_cents == 16  # 15.15 cents -> 16

    def test_negative_bid_rejected(self):
        with pytest.raises(ValueError):
            acquisition_cost(-1, POLICY)

    def test_policy_rejects_bad_rates(self):
        with pytest.raises(ValueError):
            dataclasses.replace(POLICY, buyer_premium_rate=15.0)  # percent, not fraction


class TestEvaluate:
    def test_full_breakdown(self):
        e = evaluate(20000, BASE, POLICY)
        assert e.acquisition.total_cents == 24840
        assert e.packing_cents == 750  # 10 orders * 25% shipped * $3
        assert e.deposit_expected_loss_cents == 500  # $100 * 5%
        assert e.selling_fees_cents == 7200  # 7% of $1000 + 10 * $0.20
        assert e.returns_cents == 3000
        assert e.risk_reserve_cents == 5000
        # out of pocket = 248.40 + 50 + 30 + 7.50 + 5 = 340.90
        assert e.out_of_pocket_cents == 34090
        assert e.selling_costs_cents == 15200
        # 1000 - 340.90 - 152 = 507.10
        assert e.profit_before_labor_cents == 50710
        assert e.labor_cost_cents == 16000
        assert e.net_profit_cents == 34710
        assert e.all_in_cost_cents == 100000 - 34710
        # invested = 248.40 + 50 + 30 + 7.50 = 335.90
        assert e.cash_invested_cents == 33590
        assert e.roi == pytest.approx(34710 / 33590)
        # required up front = 248.40 + 100 deposit + 50 + 30
        assert e.cash_required_cents == 42840
        assert e.profit_per_hour_before_labor_cents == pytest.approx(50710 / 8)
        assert e.net_profit_per_retained_cuft_cents == pytest.approx(34710 / 50)

    def test_net_profit_strictly_decreases_with_bid(self):
        prev = None
        for bid in range(0, 100001, 2500):
            n = evaluate(bid, BASE, POLICY).net_profit_cents
            if prev is not None:
                assert n < prev
            prev = n

    def test_zero_volume_and_zero_hours_do_not_divide(self):
        s = dataclasses.replace(BASE, retained_cuft=0.0, labor_hours=0.0)
        e = evaluate(0, s, POLICY)
        assert e.net_profit_per_retained_cuft_cents is None
        assert e.profit_per_hour_before_labor_cents is None


def brute_force_max_bid(scen, policy, rules, step=100, limit=300000):
    best = None
    for b in range(0, limit, step):
        if not constraint_failures(evaluate(b, scen["base"], policy), evaluate(b, scen["low"], policy), rules):
            best = b
    return best


class TestMaxBid:
    def test_matches_brute_force(self):
        r = max_bid(SCEN, POLICY, RULES)
        assert r.max_bid_cents == brute_force_max_bid(SCEN, POLICY, RULES)
        assert r.max_bid_cents is not None and r.max_bid_cents > 0

    def test_max_is_tight(self):
        r = max_bid(SCEN, POLICY, RULES)
        b = r.max_bid_cents
        assert not constraint_failures(evaluate(b, BASE, POLICY), evaluate(b, LOW, POLICY), RULES)
        assert constraint_failures(evaluate(b + 100, BASE, POLICY), evaluate(b + 100, LOW, POLICY), RULES)
        assert r.binding_constraints  # something stops a higher bid

    @pytest.mark.parametrize(
        "gross,disposal,premium",
        list(itertools.product([30000, 60000, 100000, 250000], [0, 25300, 60000], [0.09, 0.18])),
    )
    def test_matches_brute_force_grid(self, gross, disposal, premium):
        base = dataclasses.replace(BASE, gross_proceeds_cents=gross, disposal_cost_cents=disposal)
        low = dataclasses.replace(base, name="low", gross_proceeds_cents=gross // 3)
        high = dataclasses.replace(base, name="high", gross_proceeds_cents=gross * 2)
        scen = {"low": low, "base": base, "high": high}
        policy = dataclasses.replace(POLICY, buyer_premium_rate=premium)
        assert max_bid(scen, policy, RULES).max_bid_cents == brute_force_max_bid(scen, policy, RULES, limit=gross + 100)

    def test_no_feasible_bid(self):
        tiny = dataclasses.replace(BASE, gross_proceeds_cents=5000)
        scen = {"low": dataclasses.replace(tiny, name="low"), "base": tiny, "high": dataclasses.replace(tiny, name="high")}
        r = max_bid(scen, POLICY, RULES)
        assert r.max_bid_cents is None
        assert "min_expected_profit" in r.binding_constraints

    def test_more_value_never_lowers_max_bid(self):
        prev = -1
        for gross in range(40000, 300001, 20000):
            base = dataclasses.replace(BASE, gross_proceeds_cents=gross)
            scen = {"low": LOW, "base": base, "high": dataclasses.replace(base, name="high")}
            m = max_bid(scen, POLICY, RULES).max_bid_cents or 0
            assert m >= prev
            prev = m

    def test_more_disposal_never_raises_max_bid(self):
        prev = 10**9
        for disp in range(0, 60001, 5000):
            base = dataclasses.replace(BASE, disposal_cost_cents=disp)
            low = dataclasses.replace(LOW, disposal_cost_cents=disp)
            scen = {"low": low, "base": base, "high": HIGH}
            m = max_bid(scen, POLICY, RULES).max_bid_cents or 0
            assert m <= prev
            prev = m

    def test_max_bid_below_breakeven(self):
        """Margin of safety: the max bid must leave the required profit, so it
        is strictly below the bid at which base-case net profit is zero."""
        r = max_bid(SCEN, POLICY, RULES)
        assert evaluate(r.max_bid_cents, BASE, POLICY).net_profit_cents >= RULES.min_expected_profit_cents

    def test_low_case_loss_binds(self):
        rules = dataclasses.replace(RULES, max_low_case_loss_cents=0, target_roi=0.0,
                                    min_expected_profit_cents=0, min_profit_per_hour_before_labor_cents=0)
        r = max_bid(SCEN, POLICY, rules)
        assert r.binding_constraints == ["max_low_case_loss"]
        assert r.low_at_max.profit_before_labor_cents >= 0

    def test_bankroll_binds(self):
        rules = dataclasses.replace(RULES, bankroll_cents=30000)
        r = max_bid(SCEN, POLICY, rules)
        assert r.base_at_max.cash_required_cents <= 30000
        assert "bankroll" in r.binding_constraints


class TestIncrements:
    SCHED = [[10000, 500], [50000, 1000], [None, 5000]]

    def test_schedule(self):
        assert increment_for(0, self.SCHED) == 500
        assert increment_for(9999, self.SCHED) == 500
        assert increment_for(10000, self.SCHED) == 1000
        assert increment_for(10**7, self.SCHED) == 5000

    def test_schedule_must_be_open_ended(self):
        with pytest.raises(ValueError):
            increment_for(10**7, [[10000, 500]])
