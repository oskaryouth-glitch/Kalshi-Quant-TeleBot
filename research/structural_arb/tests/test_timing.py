from sarb.timing import LegTiming, check

S = 1_000_000_000


def test_ok():
    v = check([LegTiming("A", 0, S // 10), LegTiming("B", S // 10, S // 5)], now_utc_ns=S, max_skew_ns=S, max_age_ns=5 * S)
    assert v.ok and v.skew_ns == S // 5 and v.age_ns == S - S // 10


def test_skew_and_stale():
    v = check([LegTiming("A", 0, 1), LegTiming("B", 3 * S, 3 * S + 1)], now_utc_ns=10 * S, max_skew_ns=2 * S, max_age_ns=5 * S)
    assert not v.ok and "SKEW" in v.reasons and "STALE" in v.reasons


def test_anomalies():
    v = check([LegTiming("A", 5, 1)], now_utc_ns=0)
    assert "CLOCK_ANOMALY:A" in v.reasons and "FUTURE_TIMESTAMP" in v.reasons
    assert check([], 0).reasons == ("NO_LEGS",)
