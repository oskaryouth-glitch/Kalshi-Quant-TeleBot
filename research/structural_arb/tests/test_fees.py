"""Fee math vs official sources, plus randomized attempts to break the proven bounds."""
import random
from decimal import Decimal as D

import pytest

from sarb import fees as F
from sarb.orderbook import Level

PDF_TABLE = {  # Fee Schedule PDF pp.4-5: price -> (fee for 1 contract, fee for 100 contracts)
    "0.01": ("0.01", "0.07"), "0.05": ("0.01", "0.34"), "0.10": ("0.01", "0.63"), "0.15": ("0.01", "0.90"),
    "0.20": ("0.02", "1.12"), "0.25": ("0.02", "1.32"), "0.30": ("0.02", "1.47"), "0.35": ("0.02", "1.60"),
    "0.40": ("0.02", "1.68"), "0.45": ("0.02", "1.74"), "0.50": ("0.02", "1.75"), "0.55": ("0.02", "1.74"),
    "0.60": ("0.02", "1.68"), "0.65": ("0.02", "1.60"), "0.70": ("0.02", "1.47"), "0.75": ("0.02", "1.32"),
    "0.80": ("0.02", "1.12"), "0.85": ("0.01", "0.90"), "0.90": ("0.01", "0.63"), "0.95": ("0.01", "0.34"),
    "0.99": ("0.01", "0.07"),
}


def test_docs_worked_example_fcm_fill():
    # docs Fee Rounding: revenue -$0.055, model fee $0.00363825 -> trade fee 0.003639,
    # aligned -0.06, rounding 0.001361, net 0.005
    assert F.model_fee(D("0.055"), D(1), D(1)) == D("0.00363825")
    r = F.order_fee_exact([Level(D("0.055"), D(1))], D(1), F.NON_DIRECT_PRECISION)
    assert r.trade_fees == D("0.003639")
    assert r.rounding == D("0.001361")
    assert r.net_fee == D("0.005") and r.cash_out == D("0.06") and r.rebates == 0


@pytest.mark.parametrize("p", sorted(PDF_TABLE))
def test_pdf_table_equals_single_fill_at_cent_precision(p):
    one, hundred = PDF_TABLE[p]
    for c, want in ((1, one), (100, hundred)):
        r = F.order_fee_exact([Level(D(p), D(c))], D(1), F.NON_DIRECT_PRECISION)
        assert r.net_fee == D(want), (p, c, r)


def test_direct_precision_is_centicent():
    r = F.order_fee_exact([Level(D("0.50"), D(1))], D(1), F.DIRECT_PRECISION)
    assert r.net_fee == D("0.0175")          # PDF: 'rounded to a centicent'
    r = F.order_fee_exact([Level(D("0.55"), D(3))], D(1), F.DIRECT_PRECISION)
    assert r.net_fee == F.ceil_to(D("0.07") * 3 * D("0.55") * D("0.45"), D("0.0001"))


def test_zero_multiplier_zero_fee():
    for g in (F.DIRECT_PRECISION, F.NON_DIRECT_PRECISION):
        assert F.order_fee_exact([Level(D("0.37"), D(5))], D(0), g).net_fee == 0


def test_accumulator_rebates_across_fills():
    # 100 one-contract fills at 0.50 for a non-direct member: each fill alone would pay 0.02,
    # but rebates bring the total within one cent of the single-fill fee (1.75).
    fills = [Level(D("0.50"), D(1))] * 100
    r = F.order_fee_exact(fills, D(1), F.NON_DIRECT_PRECISION)
    assert D("1.75") <= r.net_fee < D("1.76")
    assert r.rebates > 0


def _random_price(rng):
    grid = rng.choice([D("0.01"), D("0.001"), D("0.0001"), D("0.005"), D("0.002")])
    k = rng.randint(1, int(D(1) / grid) - 1)
    return k * grid


def _split(qty: D, unit: D, rng):
    """Random split of qty into fills that are multiples of `unit`."""
    parts, left = [], qty
    while left > 0:
        n_units = int(left / unit)
        take = unit * rng.randint(1, max(1, min(n_units, rng.choice([1, 2, 3, 7, n_units]))))
        take = min(take, left)
        parts.append(take)
        left -= take
    return parts


@pytest.mark.parametrize("seed", range(40))
def test_bounds_hold_under_random_fragmentation(seed):
    rng = random.Random(seed)
    for _ in range(60):
        integer = rng.random() < 0.6
        unit = D(1) if integer else D("0.01")
        levels = []
        for _ in range(rng.randint(1, 4)):
            q = D(rng.randint(1, 40)) if integer else D(rng.randint(1, 4000)) / 100
            levels.append(Level(_random_price(rng), q))
        m = rng.choice([D(1), D("0.5"), D(0), D("0.25"), D(2)])
        fills = [Level(l.price, q) for l in levels for q in _split(l.qty, unit, rng)]
        rng.shuffle(fills)
        for g in (F.DIRECT_PRECISION, F.NON_DIRECT_PRECISION):
            exact = F.order_fee_exact(fills, m, g)
            b = F.order_fee_bound(levels, m, g)
            assert b.lower <= exact.net_fee < b.upper, (levels, m, g, exact, b)
            assert exact.net_fee >= 0
            # the per-order debit is always on the member's precision grid
            assert (exact.principal + exact.net_fee) % g == 0


def test_on_grid_bound_is_tight_and_independent_of_fill_count():
    lv = [Level(D("0.42"), D(50))]
    b = F.order_fee_bound(lv, D(1), F.NON_DIRECT_PRECISION)
    assert b.on_grid and b.upper - b.lower < D("0.0101")
    worst = F.order_fee_exact([Level(D("0.42"), D(1))] * 50, D(1), F.NON_DIRECT_PRECISION)
    assert b.lower <= worst.net_fee < b.upper


def test_off_grid_nondirect_bound_is_wide():
    # sub-cent price for a non-direct member: each 1-contract fill can round up by < 1 cent
    lv = [Level(D("0.953"), D(10))]
    b = F.order_fee_bound(lv, D(1), F.NON_DIRECT_PRECISION)
    assert not b.on_grid and b.n_fills_max == 10
    worst = F.order_fee_exact([Level(D("0.953"), D(1))] * 10, D(1), F.NON_DIRECT_PRECISION)
    assert b.lower <= worst.net_fee < b.upper
    assert worst.net_fee > F.order_fee_exact(lv, D(1), F.NON_DIRECT_PRECISION).net_fee


def test_fractional_levels_force_fine_fill_unit():
    b = F.order_fee_bound([Level(D("0.40"), D("2.5"))], D(1), F.DIRECT_PRECISION)
    assert b.min_fill_unit == D("0.01") and b.n_fills_max == 250


def test_fee_symmetric_yes_no():
    for p in ("0.013", "0.2", "0.37", "0.5", "0.9001"):
        a = F.order_fee_exact([Level(D(p), D(13))], D(1), F.DIRECT_PRECISION).trade_fees
        b = F.order_fee_exact([Level(1 - D(p), D(13))], D(1), F.DIRECT_PRECISION).trade_fees
        assert a == b


SERIES_CH = [
    {"series_ticker": "KXA", "fee_type": "quadratic", "fee_multiplier": 1, "scheduled_ts": "2026-01-01T00:00:00Z", "id": "s1"},
    {"series_ticker": "KXA", "fee_type": "quadratic", "fee_multiplier": 0.5, "scheduled_ts": "2026-08-07T00:00:00Z", "id": "s2"},
    {"series_ticker": "KXF", "fee_type": "flat", "fee_multiplier": 1, "scheduled_ts": "2026-01-01T00:00:00Z", "id": "s3"},
    {"series_ticker": "KXL", "fee_type": "quadratic", "fee_multiplier": 1, "scheduled_ts": "2026-12-01T00:00:00Z", "id": "s4"},
]
EVENT_CH = [
    {"event_ticker": "KXA-E1", "series_ticker": "KXA", "fee_type_override": "quadratic", "fee_multiplier_override": 1,
     "scheduled_ts": "2026-09-27T19:10:00Z", "id": "e1"},
    {"event_ticker": "KXA-E2", "series_ticker": "KXA", "fee_type_override": "quadratic", "fee_multiplier_override": 2,
     "scheduled_ts": "2026-09-01T00:00:00Z", "id": "e2"},
    {"event_ticker": "KXA-E2", "series_ticker": "KXA", "fee_type_override": None, "fee_multiplier_override": None,
     "scheduled_ts": "2026-09-10T00:00:00Z", "id": "e3"},
]


def test_resolve_fee_precedence_and_time():
    r = F.resolve_fee("KXA", "KXA-E1", "2026-09-27T19:00:00Z", None, SERIES_CH, EVENT_CH)
    assert r.multiplier == D("0.5") and r.source.startswith("series_change:s2")
    r = F.resolve_fee("KXA", "KXA-E1", "2026-09-27T19:10:00Z", None, SERIES_CH, EVENT_CH)
    assert r.multiplier == 1 and r.source.startswith("event_override:e1")     # in-game override
    r = F.resolve_fee("KXA", "KXA-E2", "2026-09-05T00:00:00Z", None, SERIES_CH, EVENT_CH)
    assert r.multiplier == 2
    r = F.resolve_fee("KXA", "KXA-E2", "2026-09-11T00:00:00Z", None, SERIES_CH, EVENT_CH)
    assert r.multiplier == D("0.5")                                            # override cleared
    r = F.resolve_fee("KXA", "X", "2026-03-01T00:00:00Z", None, SERIES_CH, EVENT_CH)
    assert r.multiplier == 1


def test_resolve_fee_rejects_unknown_and_unsupported():
    with pytest.raises(F.UnsupportedFee):
        F.resolve_fee("KXF", "e", "2026-09-01T00:00:00Z", None, SERIES_CH, [])
    with pytest.raises(F.UnsupportedFee):   # only a FUTURE change is known -> value now unknown
        F.resolve_fee("KXL", "e", "2026-09-01T00:00:00Z", {"series": {"fee_type": "quadratic", "fee_multiplier": 1}},
                      SERIES_CH, [])
    with pytest.raises(F.UnsupportedFee):
        F.resolve_fee("KXZ", "e", "2026-09-01T00:00:00Z", {"series": {}}, SERIES_CH, [])
    with pytest.raises(F.UnsupportedFee):
        F.resolve_fee("KXZ", "e", "2026-09-01T00:00:00Z",
                      {"series": {"fee_type": "margin_market_maker_program_fees", "fee_multiplier": 0}}, SERIES_CH, [])
    r = F.resolve_fee("KXZ", "e", "2026-09-01T00:00:00Z",
                      {"series": {"fee_type": "quadratic_with_combo_maker_fees", "fee_multiplier": 1}}, SERIES_CH, [])
    assert r.source == "series_current"


def test_conservative_multiplier():
    assert F.conservative_multiplier("KXMLBGAME", D("0.5")) == 1         # PDF taker 1 > API 0.5
    assert F.conservative_multiplier("KXBTCY", D("0.5")) == D("0.5")     # PDF 0 < API
    assert F.conservative_multiplier("KXMVECROSSCATEGORY", D("0.5")) == 1
    assert F.conservative_multiplier("KXUNLISTED", D("0.5")) == D("0.5")


def test_leg_cash_out_scenarios_ordering():
    lv = [Level(D("0.953"), D(10)), Level(D("0.96"), D(5))]
    rf = F.ResolvedFee("quadratic", D("0.5"), "t")
    exp = F.leg_cash_out(lv, "KXMLBGAME", rf, F.DIRECT_EXPECTED)
    bnd = F.leg_cash_out(lv, "KXMLBGAME", rf, F.DIRECT_BOUND)
    con = F.leg_cash_out(lv, "KXMLBGAME", rf, F.NONDIRECT_CONSERVATIVE)
    assert exp < bnd < con
