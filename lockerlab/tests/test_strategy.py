"""manual_v1 strategy and breakeven analysis (with the repo's config)."""

import dataclasses

import pytest

from lockerlab import analysis
from lockerlab.strategies import OperatorEstimate, UnderwritingError, manual_v1

EST = OperatorEstimate(
    gross_low_cents=60000, gross_base_cents=200000, gross_high_cents=400000, confidence=0.6,
    fill_fraction=0.5, keep_fraction=0.3, trash_fraction=0.4, n_listings=20, n_orders=15,
    longest_item_in=48,
)


def uw_for(cfg, w, l, est=EST, market="colorado_springs"):
    snap = analysis.synthetic_snapshot(w, l, market)
    return manual_v1(snap, est, cfg.market(market), cfg.underwriting)


def test_vehicle_choice_minimises_transport_plus_disposal(cfg):
    # 10x15 half full: 240 cuft trash. A cargo van needs 2 dump visits (2 x $253
    # minimum); a 10ft truck needs 1. The truck must win despite higher rental cost.
    uw = uw_for(cfg, 10, 15)
    opts = {o["vehicle"]: o for o in uw.outputs["transport"]["options"]}
    assert opts["uhaul_10ft_truck"]["dump_trips"] == 1
    assert opts["homedepot_cargo_van"]["dump_trips"] == 2
    assert uw.outputs["transport"]["choice"]["vehicle"] == "uhaul_10ft_truck"


def test_disposal_label_reflects_cost(cfg):
    uw = uw_for(cfg, 5, 5, dataclasses.replace(EST, gross_low_cents=10000, gross_base_cents=50000,
                                                gross_high_cents=100000))
    # $253 minimum vs ~$425 gross: cost share alone makes it HIGH
    assert uw.outputs["disposal"]["burden_level"] == "HIGH"


def test_unit_size_required(cfg):
    snap = dataclasses.replace(analysis.synthetic_snapshot(5, 5, "colorado_springs"), width_ft=None)
    with pytest.raises(UnderwritingError, match="unit size"):
        manual_v1(snap, EST, cfg.market("colorado_springs"), cfg.underwriting)


def test_sofa_rules_out_cars(cfg):
    uw = uw_for(cfg, 5, 10, dataclasses.replace(EST, longest_item_in=84))
    assert uw.outputs["transport"]["choice"]["vehicle"] not in ("friend_sedan", "friend_suv")


def test_low_confidence_is_watch_not_bid(cfg):
    uw = uw_for(cfg, 5, 10, dataclasses.replace(EST, confidence=0.2))
    assert uw.max_bid_cents is not None and uw.decision == "WATCH" and uw.paper_bid_cents is None


def test_estimate_validation():
    with pytest.raises(UnderwritingError):
        dataclasses.replace(EST, gross_low_cents=300000)  # low > base
    with pytest.raises(UnderwritingError):
        dataclasses.replace(EST, keep_fraction=0.7, trash_fraction=0.4)


def test_breakeven_hurdle_rises_with_bid(cfg):
    snap = analysis.synthetic_snapshot(5, 10, "colorado_springs")
    p = analysis.Profile(avg_sale_cents=10000)
    m, uw = cfg.market("colorado_springs"), cfg.underwriting
    hurdles = [analysis.required_gross(snap, b, p, m, uw) for b in (0, 5000, 10000, 20000)]
    assert all(h is not None for h in hurdles)
    assert hurdles == sorted(hurdles) and hurdles[0] < hurdles[-1]
    # the hurdle really is the boundary
    assert analysis.max_bid_for(snap, hurdles[1], p, m, uw) >= 5000
    assert (analysis.max_bid_for(snap, hurdles[1] - 1000, p, m, uw) or -1) < 5000
