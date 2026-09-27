"""Strike-to-interval mapping on REAL rules texts captured from the live API on 2026-09-27."""
from fractions import Fraction as Fr

import pytest

from sarb import semantics as S
from sarb.payoff import Interval


def mk(text, st, floor=None, cap=None, series_terms=None, sha=None, **kw):
    ev = {"event_ticker": kw.pop("event", "E"), "series_ticker": kw.pop("series", "S"), "settlement_sources": []}
    m = {"ticker": kw.pop("ticker", "T"), "strike_type": st, "floor_strike": floor, "cap_strike": cap,
         "rules_primary": text, "rules_secondary": kw.pop("secondary", ""), "market_type": "binary",
         "notional_value_dollars": "1.0000", "latest_expiration_time": kw.pop("exp", "2026-10-02T21:00:00Z"),
         "custom_strike": kw.pop("custom", None)}
    series = {"contract_terms_url": series_terms} if series_terms else {}
    return S.build_market_spec(ev, m, series, {series_terms: sha} if series_terms else {})


BTC = "https://assets.kalshi.com/contract_terms/BTC.pdf"
BTC_SHA = "e7d857369971e75e9db14c5e2d91c29b94eb9a06e83e2acd9777991c4f2a0e2f"
BTC_B = ("If the simple average of the sixty seconds of CF Benchmarks' Bitcoin Real-Time Index (BRTI) before 5 PM EDT "
         "is between 72000-72499.99 at 5 PM EDT on Oct 2, 2026, then the market resolves to Yes.")
BTC_T = ("If the simple average of the sixty seconds of CF Benchmarks' Bitcoin Real-Time Index (BRTI) before 5 PM EDT "
         "is above 71999.99 at 5 PM EDT on Oct 2, 2026, then the market resolves to Yes.")


def test_between_unverified_terms_is_adversarial():
    sp = mk(BTC_B, "between", 72000, 72499.99)
    assert sp.reject is None and sp.terms is None and sp.terms_status != "TERMS_VERIFIED" and sp.no_data_all_no
    assert sp.envelope.inner == (Interval(Fr(72000), False, Fr("72499.99"), False),)
    assert Interval(Fr(72000), True, Fr("72499.99"), True) in sp.envelope.outer


def test_between_verified_terms_inclusive_and_all_no():
    sp = mk(BTC_B, "between", 72000, 72499.99, series_terms=BTC, sha=BTC_SHA)
    assert sp.terms_status == "TERMS_VERIFIED" and sp.no_data_all_no
    assert sp.envelope.inner == (Interval(Fr(72000), True, Fr("72499.99"), True),)


def test_terms_hash_change_lapses_verification():
    sp = mk(BTC_B, "between", 72000, 72499.99, series_terms=BTC, sha="0" * 64)
    assert sp.terms_status == "TERMS_HASH_CHANGED" and sp.terms is None


def test_btc_and_btcd_share_a_family_template():
    a = mk(BTC_B, "between", 72000, 72499.99, series="KXBTC", event="KXBTC-26OCT0217")
    b = mk(BTC_T, "greater", 71999.99, series="KXBTCD", event="KXBTCD-26OCT0217")
    assert a.family_key == b.family_key and "<cond>" in a.template


def test_inxu_encoding_offset_envelope():
    sp = mk("If the S&P 500 index value on Sep 28, 2026 at 4pm EDT is above 7549.9999, then the market resolves to Yes.",
            "greater_or_equal", 7550)
    assert sp.envelope.inner == (Interval(Fr(7550), True, None, False),)
    assert Interval(Fr("7549.9999"), False, None, False) in sp.envelope.outer


def test_plus_notation_and_half_offset():
    sp = mk("If Sam Darnold records 1+ passing interceptions in the Seattle vs Washington Pro Football game "
            "originally scheduled for Sep 27, 2026, then the market resolves to Yes.", "greater", 0.5)
    assert sp.reject is None and sp.envelope.inner == (Interval(Fr(1), True, None, False),)


def test_scaled_units_k_and_billion():
    a = mk("If Tough Love by Nessa Barrett has above 12K Pure Album Sales during the week, then the market resolves to Yes.",
           "greater", 12000)
    assert a.reject is None
    b = mk("If Total Construction Spending: Manufacturing in the United States for December 2026 is above $170 billion, "
           "then the market resolves to Yes.", "greater", 170)
    assert b.reject is None and b.envelope.inner == (Interval(Fr(170), False, None, False),)


def test_vote_share_range_encodes_halfline():
    sp = mk("If the certified percentage of the popular vote received by Rachel Peace in the 2026 NJ-04 House "
            "election is 44% to 100%, inclusive of both endpoints, then the market resolves to Yes.",
            "greater_or_equal", 44)
    assert sp.reject is None and sp.direction == "up"
    assert sp.envelope.inner == (Interval(Fr(44), True, Fr(100), True),)


@pytest.mark.parametrize("text,st,floor,cap,code", [
    ("If the NOAA's National Hurricane Center records more than 7 hurricanes of hurricane category 1 or above "
     "between January 1, 2026 and December 01, 2026, then the market resolves to Yes.", "greater", 7, None,
     "AMBIGUOUS_COMPARATOR"),
    ("If a member of the Democratic Party wins the popular vote in 2028 by a margin of between 8.00-8.99%, "
     "then the market resolves to Yes.", "between", -8.99, -8, "TEXT_FIELD_VALUE_CONFLICT"),
    ("If the number of MLB regular season games played is exactly 0 games in the 2027 MLB regular season, "
     "then the market resolves to Yes.", "less", None, 1, "UNSUPPORTED_COMPARATOR"),
    ("If the total vote count is above 1010000, then the market resolves to Yes.", "less", None, 1010000,
     "TEXT_FIELD_DIRECTION_CONFLICT"),
    ("Some text with no strike at all.", "greater", 5, None, "NO_COMPARATOR"),
    ("If X is above 5, then the market resolves to Yes.", "greater", None, 5, "FIELD_SHAPE"),
])
def test_rejections(text, st, floor, cap, code):
    assert mk(text, st, floor, cap).reject == code


def test_path_dependent_directions_split_families():
    up = mk("If the 30Y yield is ever above 5.50% on any business day between Sep 9, 2026 and Sep 30, 2026, "
            "then the market resolves to Yes.", "greater", 5.5)
    dn = mk("If the 30Y yield is ever below 5.08% on any business day between Sep 9, 2026 and Sep 30, 2026, "
            "then the market resolves to Yes.", "less", None, 5.08)
    assert up.path_dependent and dn.path_dependent
    # same template, but max-based and min-based statistics must NOT share an underlying
    assert up.template == dn.template and up.family_key != dn.family_key


def test_path_dependent_between_rejected():
    sp = mk("If the price is ever between 5-6 at any time before Dec 31, then the market resolves to Yes.",
            "between", 5, 6)
    assert sp.reject == "PATH_DEPENDENT_RANGE"


def test_family_key_separates_custom_strike_and_expiry():
    t = "If Team wins by more than 3.5 points in the game, then the market resolves to Yes."
    a = mk(t, "greater", 3.5, custom={"team": "A"})
    b = mk(t, "greater", 3.5, custom={"team": "B"})
    c = mk(t, "greater", 3.5, custom={"team": "A"}, exp="2027-01-01T00:00:00Z")
    assert len({a.family_key, b.family_key, c.family_key}) == 3


def test_non_binary_or_non_unit_notional_rejected():
    sp = mk(BTC_T, "greater", 71999.99)
    assert sp.reject is None
    ev = {"event_ticker": "E", "series_ticker": "S"}
    m = {"ticker": "T", "strike_type": "greater", "floor_strike": 1, "rules_primary": "above 1",
         "market_type": "scalar", "notional_value_dollars": "1.0000"}
    assert S.build_market_spec(ev, m, {}, {}).reject == "NOT_BINARY"
