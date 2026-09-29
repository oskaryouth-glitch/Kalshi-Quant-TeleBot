"""Queue/fill model (DESIGN §6)."""
from decimal import Decimal as D

import pytest

from m6_paper import fills as F


def order(side="yes", price="0.40", size=10, q=5, placed=0, t_eff=1, oid=1):
    return F.Order(oid, side, D(price), D(size), D(q), placed, t_eff, "e")


def tr(taker, yes_price, count, tid="t"):
    return {"taker_side": taker, "yes_price_dollars": f"{D(yes_price):.4f}", "no_price_dollars": f"{1 - D(yes_price):.4f}",
            "count_fp": str(count), "trade_id": tid}


def test_queue_ahead_then_fill_then_direct():
    o = order(q=5)
    assert F.match_trade([o], tr("no", "0.40", 3), 10) == [] and o.q_real == 2
    res = F.match_trade([o], tr("no", "0.40", 4), 11)
    assert [(r[1], r[2]) for r in res] == [(D(2), "queue")] and o.size == 8 and o.q_real == 0
    F.match_trade([o], tr("no", "0.40", 100), 12)
    assert o.size == 0


def test_taker_side_mapping_and_other_side_untouched():
    y, n = order("yes", "0.40", q=0, oid=1), order("no", "0.55", q=0, oid=2)
    F.match_trade([y, n], tr("yes", "0.45", 3), 10)             # taker bought YES at 0.45 = sold NO at 0.55
    assert y.size == 10 and n.size == 7
    F.match_trade([y, n], tr("no", "0.40", 4), 11)
    assert y.size == 6


def test_trade_through_fills_better_priced_orders():
    o = order(q=500)
    res = F.match_trade([o], tr("no", "0.38", 6), 10)            # print below our 0.40 bid
    assert res[0][1] == 6 and res[0][2] == "through" and o.size == 4 and o.q_real == 0


def test_better_priced_trade_does_not_touch_us():
    o = order(q=0)
    assert F.match_trade([o], tr("no", "0.42", 50), 10) == [] and o.size == 10


def test_not_live_before_latency():
    o = order(q=0, t_eff=100)
    assert F.match_trade([o], tr("no", "0.40", 50), 99) == [] and o.size == 10


def test_own_earlier_order_is_ahead_and_real_consumption_is_exact():
    old = order(size=3, q=0, placed=0, oid=1)
    new = order(size=10, q=5, placed=5, oid=2)                  # queue: [old(3), real(5), new]
    res = F.match_trade([new, old], tr("no", "0.40", 4), 10)
    assert [(r[0].oid, r[1]) for r in res] == [(1, D(3))]
    assert new.q_real == 4 and new.size == 10                   # 1 real contract consumed


@pytest.mark.parametrize("variant,expected", [("V_T", D(60)), ("V_P", D(30)), ("V_C", D(10))])
def test_cancellation_credit_variants(variant, expected):
    o = order(q=60)
    prev = {"yes": {D("0.40"): D(100)}}
    now = {"yes": {D("0.40"): D(40)}}                          # 60 fewer; 10 traded -> 50 cancelled
    F.queue_update([o], prev, now, {("yes", D("0.40")): D(10)}, variant)
    assert o.q_real == expected


def test_level_vanished_puts_us_in_front_in_every_variant():
    for v in ("V_T", "V_P", "V_C"):
        o = order(q=60)
        F.queue_update([o], {"yes": {D("0.40"): D(100)}}, {"yes": {}}, {}, v)
        assert o.q_real == 0
