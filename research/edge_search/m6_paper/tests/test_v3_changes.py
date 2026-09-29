"""Reviewer items of 2026-09-29: 2 req/s, recorded collection gaps, fee provenance, validation quarantine."""
from decimal import Decimal as D

import pytest

from m6_paper import collector as C
from m6_paper import selection as SEL
from m6_paper import sim as SIM
from m6_paper import spec as S
from m6_paper import storage as ST
from test_collector_analysis import Fake, collector

NS = 10**9


def test_request_ceiling_is_two_per_second():
    assert S.MAX_REQUESTS_PER_S == 2.0 and C.Http(opener=Fake()).min_gap == 0.5


def test_epoch_records_its_collection_gap_and_queues_new_fee_fetches(tmp_path):
    c = collector(tmp_path, Fake(12))
    rec = c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    gaps = [r for r in ST.read(str(tmp_path), "ops") if r.get("kind") == "collection_gap"]
    assert gaps and gaps[0]["reason"] == "epoch" and gaps[0]["start_ns"] <= gaps[0]["end_ns"]
    assert rec["fee_provenance"]["series_fee_t_ns"] and len(c.pending_fee_markets) == 12
    assert c.poll_new_fees() == S.FEES_NEW_PER_LOOP and len(c.pending_fee_markets) == 12 - S.FEES_NEW_PER_LOOP


def test_validation_and_prospective_data_never_mix(tmp_path):
    C.check_dir(set(), True, "/srv/m6/validation_1")
    with pytest.raises(SystemExit):
        C.check_dir(set(), True, "/srv/m6/data")                 # validation outside a validation path
    with pytest.raises(SystemExit):
        C.check_dir({"validation"}, False, "/srv/m6/data")       # prospective run into validation data
    with pytest.raises(SystemExit):
        C.check_dir({"start"}, True, "/srv/m6/validation_1")
    root = str(tmp_path / "validation_x")
    ST.Writer(root).write("meta", {"t_ns": 1, "kind": "validation"})
    with pytest.raises(RuntimeError):
        SIM.Replay(root)


# ---------------------------------------------------------------- known vs applicable fee state
T = SEL.ts_ns("2026-10-02T00:00:00Z")


def world(series_obs=None, event_obs=None, changes=None, override=None):
    w = SIM.World()
    w.market["MA"] = {"event_ticker": "EV"}
    if event_obs is not None:
        w.on_feestate(event_obs, {"events": {"EV": {"t_ns": event_obs, "series_ticker": "S1", **(override or {})}}, "series": {}})
    if series_obs is not None:
        w.on_feestate(series_obs, {"events": {}, "series": {"S1": {"t_ns": series_obs, "fee_type": "quadratic", "fee_multiplier": 1}},
                                   "fee_changes": changes or [], "fee_changes_t_ns": series_obs})
    return w


def test_known_fee_uses_only_prior_observations_applicable_may_use_later_ones():
    w = world(series_obs=T + 3600 * NS, event_obs=T + 3600 * NS)
    ft, m, p = w.fee_state("MA", T)
    assert (ft, m) == S.UNKNOWN_FEE_STATE and p["basis"] == "known"
    ft, m, p = w.fee_state("MA", T, T + 86400 * NS)
    assert ft == "quadratic" and p["basis"] == "applicable" and p["status"] == "ok"


def test_scheduled_change_before_fill_is_applied_and_one_after_is_not():
    ch = [{"series_ticker": "S1", "scheduled_ts": "2026-10-01T12:00:00Z", "fee_type": "quadratic_with_maker_fees", "fee_multiplier": 2}]
    w = world(series_obs=T - 86400 * NS, event_obs=T - 86400 * NS, changes=ch)
    ft, m, p = w.fee_state("MA", T)
    assert (ft, m) == ("quadratic_with_maker_fees", D(2)) and p["changes_applied"] == ["2026-10-01T12:00:00Z"]
    ft, m, _ = w.fee_state("MA", SEL.ts_ns("2026-10-01T06:00:00Z"))
    assert ft == "quadratic"


def test_change_between_fill_and_later_only_observation_is_undetermined():
    ch = [{"series_ticker": "S1", "scheduled_ts": "2026-10-02T00:30:00Z", "fee_type": "quadratic", "fee_multiplier": 1}]
    w = world(series_obs=T + 3600 * NS, event_obs=T - 60 * NS, changes=ch)
    ft, m, p = w.fee_state("MA", T, T + 86400 * NS)
    assert (ft, m) == S.UNKNOWN_FEE_STATE and p["status"].startswith("undetermined")


def test_event_override_applies_to_fills():
    w = world(series_obs=T - 60 * NS, event_obs=T - 60 * NS,
              override={"fee_type_override": "quadratic_with_maker_fees", "fee_multiplier_override": "0.5"})
    ft, m, p = w.fee_state("MA", T)
    assert (ft, m) == ("quadratic_with_maker_fees", D("0.5")) and p["event_override"]


def test_selection_uses_only_the_epoch_series_state():
    from test_sim import BOOK, EPOCH, MARKET, PROGRAM
    ep = {"t_ns": EPOCH + 30 * NS, "epoch_ns": EPOCH, "programs": [PROGRAM], "markets": {"MA": MARKET}, "books": {"MA": BOOK},
          "series_fee": {"S-MA": {"fee_type": "quadratic", "fee_multiplier": 1}}, "event_series": {"EV-MA": "S-MA"},
          "fee_provenance": {"series_fee_t_ns": EPOCH + 20 * NS}}
    c = SEL.candidates(ep)[0]
    assert c.fee_type == "quadratic" and c.fee_provenance["basis"] == "selection_series_level"
    assert c.fee_provenance["series_fee_t_ns"] == EPOCH + 20 * NS and c.fee_provenance["known"]
    ep["event_series"] = {}
    c2 = SEL.candidates(ep)[0]
    assert (c2.fee_type, c2.fee_mult) == S.UNKNOWN_FEE_STATE and not c2.fee_provenance["known"]


def test_full_fee_refresh_is_incremental_and_records_change_history(tmp_path):
    c = collector(tmp_path, Fake(7))
    c.epoch(SEL.ts_ns("2026-10-01T06:00:00Z"))
    while c.poll_new_fees():
        pass
    c.schedule_full_fees()
    assert len(c.pending_fee_markets) == 7 and all(s == "full" for _, s in c.pending_fee_markets)
    n = 0
    while True:
        k = c.poll_new_fees()
        assert k <= S.FEES_NEW_PER_LOOP
        if not k:
            break
        n += k
    recs = list(ST.read(str(tmp_path), "feestate"))
    assert n == 7 and any(r["scope"] == "fee_changes" and "fee_changes" in r for r in recs)
    assert all(v["t_ns"] for r in recs for v in r["events"].values())      # every fee object carries its receive time


def test_gaps_longer_than_60s_earn_no_reward_time():
    assert SIM.covered(59 * NS) == 59 * NS and SIM.covered(60 * NS) == 60 * NS
    assert SIM.covered(61 * NS) == 0 and SIM.covered(104 * NS) == 0
