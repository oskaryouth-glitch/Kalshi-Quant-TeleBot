from decimal import Decimal as D
import pytest
from sarb.fees import FeeSchedule, UnsupportedFee, round_up
from sarb.orderbook import Level


def test_round_up():
    assert round_up(D("0.0175"), D("0.01")) == D("0.02")
    assert round_up(D("0.02"), D("0.01")) == D("0.02")
    assert round_up(D("0.00001"), D("0.01")) == D("0.01")
    assert round_up(D(0), D("0.01")) == 0
    assert round_up(D("0.017500"), D("0.0001")) == D("0.0175")


@pytest.mark.parametrize("p,c,expected", [
    ("0.50", 1, "0.02"),     # 0.07*.25 = .0175 -> .02
    ("0.50", 100, "1.75"),   # exact
    ("0.10", 1, "0.01"),     # .0063 -> .01
    ("0.99", 1, "0.01"),     # .000693 -> .01
    ("0.30", 10, "0.15"),    # .147 -> .15
])
def test_taker_fee_cent_rounding(p, c, expected):
    assert FeeSchedule().taker_fee([Level(D(p), D(c))]) == D(expected)


def test_multiplier_and_centicent():
    fs = FeeSchedule(multiplier=D("0.5"), rounding_unit=D("0.0001"))
    assert fs.taker_fee([Level(D("0.5"), D(1))]) == D("0.0088")   # .00875 -> .0088


def test_per_fill_rounding_is_conservative():
    fills = [Level(D("0.45"), D(7)), Level(D("0.50"), D(3))]
    per_fill = FeeSchedule(per_fill_rounding=True).taker_fee(fills)
    per_leg = FeeSchedule(per_fill_rounding=False).taker_fee(fills)
    assert per_fill >= per_leg
    assert per_leg == round_up(D("0.07") * (7 * D("0.45") * D("0.55") + 3 * D("0.25")), D("0.01"))


def test_fee_symmetric_in_yes_no_price():
    fs = FeeSchedule()
    for p in ("0.01", "0.2", "0.37", "0.5"):
        assert fs.taker_fee([Level(D(p), D(13))]) == fs.taker_fee([Level(1 - D(p), D(13))])


def test_from_series_and_unsupported():
    fs = FeeSchedule.from_series({"series": {"fee_type": "quadratic_with_maker_fees", "fee_multiplier": 1}})
    assert fs.fee_type == "quadratic_with_maker_fees" and fs.multiplier == 1
    with pytest.raises(UnsupportedFee):
        FeeSchedule.from_series({"series": {"ticker": "X"}})
    with pytest.raises(UnsupportedFee):
        FeeSchedule(fee_type="flat").taker_fee([Level(D("0.5"), D(1))])
