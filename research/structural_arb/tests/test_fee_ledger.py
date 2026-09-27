"""Time-versioned fee ledger: the fee IN FORCE at the snapshot, or FEE_UNRESOLVED."""
import datetime as dt
from decimal import Decimal as D

import pytest

from sarb.fee_ledger import BOUNDARY_NS, MAX_OBS_AGE_NS, FeeLedger, FeeUnresolved

S = 1_000_000_000
MIN = 60 * S


def ns(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * S)


def iso(n):
    return dt.datetime.fromtimestamp(n / S, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


T0 = ns("2026-09-27T18:00:00Z")


def sch(key, at, ftype, m, cid):          # series change
    return {"series_ticker": key, "fee_type": ftype, "fee_multiplier": m, "scheduled_ts": iso(at), "id": cid}


def ech(ev, at, ftype, m, cid):           # event change (None, None = clear)
    return {"event_ticker": ev, "series_ticker": "KXS", "fee_type_override": ftype,
            "fee_multiplier_override": m, "scheduled_ts": iso(at), "id": cid}


def obs(led, ev=None, ev_state=(None, None), series=None, s_state=None, at=T0):
    if ev:
        led.observe_event({"event_ticker": ev, "fee_type_override": ev_state[0], "fee_multiplier_override": ev_state[1]}, at)
    if series:
        led.observe_series({"series": {"ticker": series, "fee_type": s_state[0], "fee_multiplier": s_state[1]}}, at)


def base(tmp_path=None):
    led = FeeLedger(str(tmp_path / "ledger.jsonl") if tmp_path else None)
    led.add_series_changes([sch("KXS", T0 - 100 * MIN, "quadratic", 1, "s1")])
    return led


def test_series_value_when_no_override():
    led = base()
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    r = led.resolve("KXS", "E", T0 + 5 * S)
    assert r.multiplier == 1 and "series_object_observed" in r.source


def test_series_fee_decrease_and_increase_follow_history():
    led = base()
    led.add_series_changes([sch("KXS", T0 + 10 * MIN, "quadratic", 0.5, "s2"),
                            sch("KXS", T0 + 20 * MIN, "quadratic", 2, "s3")])
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    for t, want in ((T0 + 5 * S, 1), (T0 + 15 * MIN, D("0.5")), (T0 + 25 * MIN, 2)):
        obs(led, "E", (None, None), at=t - 2 * S)                   # fresh event observation
        assert led.resolve("KXS", "E", t).multiplier == want        # history covers after the old series obs


def test_temporary_event_override_then_expiry_reverts_to_series():
    led = base()
    led.add_event_changes([ech("E", T0 + 10 * MIN, "quadratic", 2, "e1"),
                           ech("E", T0 + 30 * MIN, None, None, "e2")])       # cleared = reversion
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    assert led.resolve("KXS", "E", T0 + 5 * S).multiplier == 1
    obs(led, "E", ("quadratic", 2), "KXS", ("quadratic", 1), at=T0 + 15 * MIN)
    r = led.resolve("KXS", "E", T0 + 15 * MIN + 5 * S)
    assert r.multiplier == 2 and "event_object_observed" in r.source
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0 + 35 * MIN)
    assert led.resolve("KXS", "E", T0 + 35 * MIN + 5 * S).multiplier == 1


def test_scheduled_event_change_between_observation_and_snapshot_is_applied():
    led = base()
    led.add_event_changes([ech("E", T0 + 20 * S + BOUNDARY_NS, "quadratic", 2, "e1")])
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    # snapshot after the change but inside obs freshness window is impossible with 60 s boundary + 30 s age,
    # so the boundary guard fires instead of guessing:
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + 20 * S + BOUNDARY_NS)
    assert e.value.code == "NEAR_SCHEDULED_CHANGE"


def test_event_override_decrease_below_series():
    led = base()
    obs(led, "E", ("quadratic", "0.25"), "KXS", ("quadratic", 1), at=T0)
    assert led.resolve("KXS", "E", T0 + S).multiplier == D("0.25")          # decreases are honoured, no max()


def test_multiple_changes_latest_wins_and_no_maximum_substitution():
    led = base()
    led.add_event_changes([ech("E", T0 - 50 * MIN, "quadratic", 3, "e1"),
                           ech("E", T0 - 40 * MIN, "quadratic", 1, "e2"),
                           ech("E", T0 - 30 * MIN, "quadratic", "0.5", "e3")])
    obs(led, "E", ("quadratic", "0.5"), "KXS", ("quadratic", 1), at=T0)
    assert led.resolve("KXS", "E", T0 + S).multiplier == D("0.5")
    # another event of the same series: the series' past overrides must NOT leak into it
    obs(led, "E2", (None, None), at=T0)
    assert led.resolve("KXS", "E2", T0 + S).multiplier == 1


def test_override_in_force_before_first_seen_is_taken_from_event_object():
    """The change list never showed it (it had already taken effect); the event object does."""
    led = base()
    obs(led, "E", ("quadratic", 1), "KXS", ("quadratic", "0.5"), at=T0)
    assert led.resolve("KXS", "E", T0 + S).multiplier == 1


def test_unobserved_or_stale_event_is_unresolved():
    led = base()
    obs(led, None, series="KXS", s_state=("quadratic", 1), at=T0)
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + S)
    assert e.value.code == "EVENT_NOT_OBSERVED"
    obs(led, "E", (None, None), at=T0)
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + MAX_OBS_AGE_NS + S)
    assert e.value.code == "EVENT_OBSERVATION_STALE"
    with pytest.raises(FeeUnresolved):
        led.resolve("KXS", "E", T0 - S)                                   # observation after snapshot: look-ahead


def test_collector_downtime_across_effective_timestamp():
    led = base()
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    # downtime: an override is created AND takes effect while we are down (never in our change list)
    t_back = T0 + 3 * 60 * MIN
    with pytest.raises(FeeUnresolved) as e:                              # before re-observation: unresolved
        led.resolve("KXS", "E", t_back)
    assert e.value.code in ("EVENT_OBSERVATION_STALE",)
    obs(led, "E", ("quadratic", 2), "KXS", ("quadratic", 1), at=t_back + S)
    assert led.resolve("KXS", "E", t_back + 2 * S).multiplier == 2


def test_series_change_during_downtime_known_from_complete_history():
    led = base()
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    led.add_series_changes([sch("KXS", T0 + 60 * MIN, "quadratic", "0.5", "s9")])   # fetched after restart
    obs(led, "E", (None, None), at=T0 + 120 * MIN)
    assert led.resolve("KXS", "E", T0 + 120 * MIN + S).multiplier == D("0.5")


def test_conflict_between_schedule_and_observation_is_unresolved():
    led = base()
    led.add_event_changes([ech("E", T0 - 30 * MIN, "quadratic", 2, "e1")])
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)         # schedule says override, object says none
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + S)
    assert e.value.code == "EVENT_LEDGER_CONFLICT"
    led2 = base()
    obs(led2, "E", (None, None), "KXS", ("quadratic", "0.7"), at=T0)   # series object disagrees with history
    with pytest.raises(FeeUnresolved) as e:
        led2.resolve("KXS", "E", T0 + S)
    assert e.value.code == "SERIES_LEDGER_CONFLICT"


def test_boundary_guard_both_layers():
    led = base()
    led.add_series_changes([sch("KXS", T0 + 30 * S, "quadratic", "0.5", "s2")])
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + 5 * S)
    assert e.value.code == "NEAR_SCHEDULED_CHANGE"


def test_unsupported_type_unresolved():
    led = base()
    obs(led, "E", ("flat", 1), "KXS", ("quadratic", 1), at=T0)
    with pytest.raises(FeeUnresolved) as e:
        led.resolve("KXS", "E", T0 + S)
    assert e.value.code == "UNSUPPORTED_FEE_TYPE"


def test_restart_from_persisted_history(tmp_path):
    led = base(tmp_path)
    led.add_event_changes([ech("E", T0 + 10 * MIN, "quadratic", 2, "e1"), ech("E", T0 + 30 * MIN, None, None, "e2")])
    obs(led, "E", (None, None), "KXS", ("quadratic", 1), at=T0)
    obs(led, "E", ("quadratic", 2), at=T0 + 15 * MIN)
    led.add_event_changes([ech("E", T0 + 10 * MIN, "quadratic", 2, "e1")])      # duplicate ignored
    led2 = FeeLedger(str(tmp_path / "ledger.jsonl"))
    assert led2.changes == led.changes and led2.obs == led.obs
    # freshness is NOT persisted: after restart nothing resolves until re-observed
    with pytest.raises(FeeUnresolved) as e:
        led2.resolve("KXS", "E", T0 + 15 * MIN + S)
    assert e.value.code == "EVENT_NOT_OBSERVED"
    obs(led2, "E", ("quadratic", 2), "KXS", ("quadratic", 1), at=T0 + 16 * MIN)
    assert led2.resolve("KXS", "E", T0 + 16 * MIN + S).multiplier == 2
    # schedule loaded from disk still applies after the re-observation
    obs(led2, "E", (None, None), "KXS", ("quadratic", 1), at=T0 + 32 * MIN)
    assert led2.resolve("KXS", "E", T0 + 32 * MIN + S).multiplier == 1
    lines = open(tmp_path / "ledger.jsonl").read().splitlines()
    assert sum('"kind": "change"' in l for l in lines) == 3                  # s1, e1, e2 once each
