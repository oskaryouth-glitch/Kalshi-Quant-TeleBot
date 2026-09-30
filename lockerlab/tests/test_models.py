"""Transport, disposal, unit-size and money-parsing tests."""

import pytest

from lockerlab import disposal, transport
from lockerlab.money import cost_cents, parse_dollars, proceeds_cents
from lockerlab.units import parse_size, size_bucket, unit_volume_cuft

SEDAN = transport.Vehicle("sedan", usable_cuft=25, max_item_length_in=40, fixed_cents=2000, per_mile_cents=20)
SUV = transport.Vehicle("suv", usable_cuft=60, max_item_length_in=70, fixed_cents=2500, per_mile_cents=25)
VAN = transport.Vehicle(
    "van", usable_cuft=240, max_item_length_in=120, fixed_cents=1900, per_mile_cents=15,
    per_hour_cents=2000, included_hours=1.25, insurance_cents=1500,
)


class TestTransport:
    def test_trip_counts_and_cost(self):
        load = transport.Load(retained_cuft=60, donate_cuft=20, trash_cuft=20, longest_item_in=30)
        opts = {o.vehicle: o for o in transport.plan(load, [SEDAN, SUV, VAN], 10, 20, 1.0, 0.65)}
        # sedan: 100 / (25*.65=16.25) -> 7 trips > 4
        assert opts["sedan"].trips == 7 and not opts["sedan"].feasible
        # suv: 100 / 39 -> 3 trips; trash 20/39 -> 1 dump trip; miles 3*20 + 20 = 80
        s = opts["suv"]
        assert (s.trips, s.dump_trips, s.miles) == (3, 1, 80)
        assert s.cost_cents == 2500 + 80 * 25
        # van: 1 trip, 1 dump trip, 40 miles, 1h (inside 1.25 included)
        v = opts["van"]
        assert (v.trips, v.miles) == (1, 40)
        assert v.cost_cents == 1900 + 1500 + 40 * 15

    def test_cheapest_feasible_first(self):
        load = transport.Load(60, 20, 20, 30)
        opts = transport.plan(load, [SEDAN, SUV, VAN], 10, 20, 1.0, 0.65)
        assert transport.best(opts).vehicle == "van"  # $40 < suv $45
        assert opts[-1].vehicle == "sedan"

    def test_long_item_excludes_small_vehicles(self):
        load = transport.Load(10, 0, 0, longest_item_in=84)  # a sofa
        opts = {o.vehicle: o for o in transport.plan(load, [SEDAN, SUV, VAN], 5, 20, 1.0)}
        assert not opts["sedan"].feasible and not opts["suv"].feasible
        assert opts["van"].feasible

    def test_unavailable_vehicle(self):
        v = transport.Vehicle("x", 500, 200, 0, 0, available=False)
        assert not transport.plan(transport.Load(10, 0, 0), [v], 5, 20, 1.0)[0].feasible

    def test_empty_load_is_free(self):
        o = transport.plan(transport.Load(0, 0, 0), [SUV], 10, 20, 1.0)[0]
        assert (o.trips, o.cost_cents) == (0, 0)

    def test_extra_hours_billed(self):
        load = transport.Load(600, 0, 0)  # 600 / 156 -> 4 trips, 4h, 2.75h billable
        o = transport.plan(load, [VAN], 10, 20, 1.0, 0.65)[0]
        assert o.trips == 4
        assert o.cost_cents == 1900 + 1500 + 80 * 15 + 2.75 * 2000


RATES = disposal.DisposalRates(
    per_ton_cents=12650, minimum_charge_cents=25300, mattress_each_cents=8625,
    appliance_each_cents=700, ewaste_each_cents=0, lbs_per_cuft=9.0,
)


class TestDisposal:
    def test_minimum_dominates_small_load(self):
        e = disposal.estimate(disposal.DisposalInput(trash_cuft=20), RATES, dump_visits=1)
        assert e.load_fees_cents == 25300  # 180 lb would be $11.39 by weight

    def test_minimum_per_visit(self):
        e = disposal.estimate(disposal.DisposalInput(trash_cuft=20), RATES, dump_visits=2)
        assert e.load_fees_cents == 2 * 25300

    def test_weight_rate_above_minimum(self):
        # 600 cuft * 9 = 5400 lb = 2.7 t * 126.50 = 341.55
        e = disposal.estimate(disposal.DisposalInput(trash_cuft=600), RATES, dump_visits=1)
        assert e.load_fees_cents == 34155

    def test_item_fees(self):
        e = disposal.estimate(disposal.DisposalInput(0, mattresses=2, appliances=1, ewaste_items=3), RATES, 1)
        assert e.item_fees_cents == 2 * 8625 + 700
        assert e.visits == 1  # mattresses alone still need a dump visit
        assert e.total_cents == 25300 + 2 * 8625 + 700

    def test_nothing_to_dump(self):
        e = disposal.estimate(disposal.DisposalInput(0), RATES, dump_visits=0)
        assert (e.visits, e.total_cents, e.burden_level) == (0, 0, "LOW")

    def test_burden_levels(self):
        assert disposal.estimate(disposal.DisposalInput(300, mattresses=2), RATES, 1).burden_level == "HIGH"


class TestUnits:
    @pytest.mark.parametrize("text,expected", [
        ("10x10", (10, 10, None)),
        ("5' x 10'", (5, 10, None)),
        ("10 X 15 x 8", (10, 15, 8)),
        ("15x10", (10, 15, None)),
        ("7.5 by 10", (7.5, 10, None)),
        ("10ft x 20ft", (10, 20, None)),
    ])
    def test_parse(self, text, expected):
        assert parse_size(text) == expected

    @pytest.mark.parametrize("bad", ["", "10", "large", "0x10", "10x10x0"])
    def test_parse_rejects(self, bad):
        with pytest.raises(ValueError):
            parse_size(bad)

    @pytest.mark.parametrize("w,l,bucket", [
        (5, 5, "5x5"), (5, 10, "5x10"), (5, 15, "10x10"), (10, 10, "10x10"),
        (10, 15, "10x15"), (10, 20, "10x20+"), (10, 30, "10x20+"),
    ])
    def test_buckets(self, w, l, bucket):
        assert size_bucket(w, l) == bucket

    def test_volume_default_height(self):
        assert unit_volume_cuft(5, 10, None) == 400


class TestMoney:
    @pytest.mark.parametrize("text,cents", [
        ("145", 14500), ("$145", 14500), ("$1,234.50", 123450), ("0.5", 50), (" $ 12.34 ", 1234),
    ])
    def test_parse(self, text, cents):
        assert parse_dollars(text) == cents

    @pytest.mark.parametrize("bad", ["", "abc", "12.345", "$1.2.3", "1e5"])
    def test_parse_rejects(self, bad):
        with pytest.raises(ValueError):
            parse_dollars(bad)

    def test_rounding_is_conservative(self):
        assert cost_cents(10.01) == 11
        assert proceeds_cents(10.99) == 10
        assert cost_cents(10.0000000001) == 10  # float noise is not a cent
