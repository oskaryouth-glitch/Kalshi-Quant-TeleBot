"""Amendment-aware terms verification (sarb/filings.py, sarb/terms.py, sarb/terms_retro.py).

Fixtures use the REAL bucket objects for the three registered templates as listed on 2026-09-29
(edge_search/evidence/terms_audit/outputs/terms_audit.json). No network access.
"""
import dataclasses
import hashlib

import pytest

from sarb import config, filings as FL, terms as T, terms_retro as TR

F = FL.Filing
NOW = FL.iso_to_ns("2026-09-29T04:00:00Z")
GT_URL = "https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf"
BTC_URL = "https://assets.kalshi.com/contract_terms/BTC.pdf"
GT_AMENDMENTS = (F("regulatory/notices/GLOBALTEMPERATURE Amendment (for posting).pdf", "2026-08-18T17:55:55.000Z", 308464),
                 F("regulatory/notices/GLOBALTEMPERATURE Amendment 2 (for posting).pdf", "2026-09-02T12:00:55.000Z", 249342))
NEIGHBOURS = (F("regulatory/notices/BTCMINMAX Amendment for posting.pdf", "2024-11-12T07:34:12.000Z", 255989),
              F("regulatory/product-certifications/GLOBALTEMPERATURESUSTAINED.pdf", "2025-12-12T18:08:00.000Z", 1),
              F("contract_terms/KXBTC.pdf", "2025-01-01T00:00:00.000Z", 1))
BUCKET_2026_09_29 = (T.REGISTRY[BTC_URL].known_filings + T.REGISTRY["https://assets.kalshi.com/contract_terms/ETH.pdf"].known_filings
                     + T.REGISTRY[GT_URL].known_filings + GT_AMENDMENTS + NEIGHBOURS)


def listing(t, objs=BUCKET_2026_09_29, sha="ctrl", at=NOW - 60 * 10**9):
    return FL.Listing(t.template, at, None if objs is None else tuple(o for o in objs if FL.belongs(t.template, o.key)),
                      t.controlling_filing_sha256 if sha == "ctrl" else sha)


# ---------------------------------------------------------------- the live registry, as of 2026-09-29
def test_globaltemperature_is_superseded_by_its_amendments():
    t = T.REGISTRY[GT_URL]
    assert FL.status(t, listing(t), NOW) == "TERMS_SUPERSEDED"
    assert T.lookup(GT_URL, t.sha256, FL.status(t, listing(t), NOW)) == (None, "TERMS_SUPERSEDED")


@pytest.mark.parametrize("url", [BTC_URL, "https://assets.kalshi.com/contract_terms/ETH.pdf"])
def test_crypto_entries_keyed_to_amendment_2_verify(url):
    t = T.REGISTRY[url]
    assert t.controlling_filing.endswith("Amendment 2 for posting.pdf")
    assert FL.status(t, listing(t), NOW) == FL.OK
    assert T.lookup(url, t.sha256, FL.OK)[1] == "TERMS_VERIFIED"


# ---------------------------------------------------------------- every non-OK outcome
BTC = T.REGISTRY[BTC_URL]


@pytest.mark.parametrize("lst,expected", [
    (None, "TERMS_FILINGS_NOT_CHECKED"),
    (listing(BTC, objs=None), "TERMS_FILINGS_UNAVAILABLE"),
    (listing(BTC, at=NOW - int(config.MAX_FILINGS_LISTING_AGE_S * 1e9) - 1), "TERMS_FILINGS_STALE"),
    (listing(BTC, at=NOW + 10**9), "TERMS_FILINGS_STALE"),                        # listing from the future
    (listing(BTC, objs=BUCKET_2026_09_29 + (F("regulatory/notices/BTC Amendment 3 for posting.pdf", "2026-09-28T00:00:00.000Z", 9),)),
     "TERMS_SUPERSEDED"),
    (listing(BTC, objs=BUCKET_2026_09_29 + (F("regulatory/notices/processed-BTC modification (3).pdf", "2026-09-28T00:00:00.000Z", 9),)),
     "TERMS_SUPERSEDED"),                                                           # name not starting with the template
    (listing(BTC, objs=BUCKET_2026_09_29 + (F("regulatory/notices/btc amendment 3.pdf", "2026-09-28T00:00:00.000Z", 9),)),
     "TERMS_SUPERSEDED"),                                                           # case-insensitive
    (listing(BTC, objs=BUCKET_2026_09_29 + (F("contract_terms/BTC (1).pdf", "2026-09-28T00:00:00.000Z", 9),)),
     "TERMS_FILINGS_UNRECOGNISED"),
    (listing(BTC, objs=tuple(o for o in BUCKET_2026_09_29 if o.key != "regulatory/notices/BTC Amendment for posting.pdf")),
     "TERMS_FILINGS_INCOMPLETE"),
    (listing(BTC, objs=tuple(dataclasses.replace(o, last_modified="2026-09-28T00:00:00.000Z") if o.key == BTC.controlling_filing
                             else o for o in BUCKET_2026_09_29)), "TERMS_FILING_CHANGED"),
    (listing(BTC, sha=None), "TERMS_CONTROLLING_FILING_UNCONFIRMED"),
    (listing(BTC, sha="0" * 64), "TERMS_CONTROLLING_FILING_UNCONFIRMED"),
])
def test_status_fails_closed(lst, expected):
    assert FL.status(BTC, lst, NOW) == expected
    assert T.lookup(BTC_URL, BTC.sha256, FL.status(BTC, lst, NOW))[0] is None


def test_neighbouring_templates_do_not_count():
    assert not FL.belongs("BTC", "regulatory/notices/BTCMINMAX Amendment for posting.pdf")
    assert not FL.belongs("BTC", "contract_terms/KXBTC.pdf")
    assert not FL.belongs("GLOBALTEMPERATURE", "regulatory/product-certifications/GLOBALTEMPERATURESUSTAINED.pdf")
    assert FL.belongs("BTC", "regulatory/notices/BTC-amendment.pdf")
    assert not FL.belongs("BTC", "some/other/prefix/BTC.pdf")


def test_recent_controlling_filing_is_pending():
    t = dataclasses.replace(BTC)
    posted = FL.iso_to_ns("2025-04-28T14:27:29.000Z")
    assert FL.status(t, listing(t, at=posted + 3 * 86400 * 10**9), posted + 3 * 86400 * 10**9 + 1) == "TERMS_AMENDMENT_PENDING"
    after = posted + int(config.AMENDMENT_PENDING_S * 1e9) + 10**9
    assert FL.status(t, listing(t, at=after - 10**9), after) == FL.OK


def test_lookup_never_verifies_without_ok_filing_status():
    for fs in (None, "", "ok", "TERMS_VERIFIED", *FL.NON_OK_STATUSES):
        assert T.lookup(BTC_URL, BTC.sha256, fs)[1] != "TERMS_VERIFIED"
    assert T.lookup(BTC_URL, "0" * 64, FL.OK)[1] == "TERMS_HASH_CHANGED"


# ---------------------------------------------------------------- registry guards
def test_registry_entries_must_name_their_filing_basis():
    base = dict(url="u", sha256="s", between_inclusive=True, no_data="ALL_NO", citations=("c",), common_determination="c")
    with pytest.raises(ValueError):
        T.VerifiedTerms(**base)                                            # no filing basis at all
    ok = dict(base, template="BTC", controlling_filing=BTC.controlling_filing,
              controlling_filing_sha256=BTC.controlling_filing_sha256, known_filings=BTC.known_filings, reviewed="r")
    T.VerifiedTerms(**ok)
    with pytest.raises(ValueError):                                         # controlling filing not listed
        T.VerifiedTerms(**dict(ok, known_filings=BTC.known_filings[:2]))
    with pytest.raises(ValueError):                                         # reviewed an older filing than the newest
        T.VerifiedTerms(**dict(ok, controlling_filing="regulatory/notices/BTC Amendment for posting.pdf"))
    with pytest.raises(ValueError):                                         # another template's object
        T.VerifiedTerms(**dict(ok, known_filings=BTC.known_filings + NEIGHBOURS[:1]))


def test_rules_markers():
    assert T.rules_conflicts(BTC, {"rules_primary": "CF Benchmarks' Bitcoin Real-Time Index (BRTI)"}) == []
    gt = T.REGISTRY[GT_URL]
    live = {"rules_primary": "is between 71-72° fahrenheit according to The Weather Company"}
    assert T.rules_conflicts(gt, live) == ["MISSING:National Weather Service"]


# ---------------------------------------------------------------- refresh (I/O wrapper)
def test_refresh_fails_closed_and_skips_network_for_empty_registry():
    def boom(prefix):
        raise ConnectionError()
    out = FL.refresh({BTC_URL: BTC}, boom, lambda k: b"", now_ns=lambda: NOW)
    assert out[BTC_URL].objects is None and FL.status(BTC, out[BTC_URL], NOW) == "TERMS_FILINGS_UNAVAILABLE"
    assert FL.refresh({}, boom, boom) == {}
    ok = FL.refresh({BTC_URL: BTC}, lambda p: [o for o in BUCKET_2026_09_29 if o.key.startswith(p)],
                    lambda k: (_ for _ in ()).throw(TimeoutError()), now_ns=lambda: NOW)
    assert FL.status(BTC, ok[BTC_URL], NOW) == "TERMS_CONTROLLING_FILING_UNCONFIRMED"


class _R:
    def __init__(self, status, content):
        self.status_code, self.content = status, content


def _page(keys, truncated, token=None):
    body = "".join(f"<Contents><Key>{k}</Key><LastModified>2020-01-01T00:00:00.000Z</LastModified><Size>1</Size></Contents>"
                   for k in keys)
    t = f"<NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    return ('<?xml version="1.0"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f"{body}<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>{t}</ListBucketResult>").encode()


def test_http_list_paginates_and_refuses_partial_listings():
    pages = iter([_R(200, _page(["a"], True, "tok")), _R(200, _page(["b"], False))])
    assert [f.key for f in FL.http_list("p/", get=lambda url: next(pages))] == ["a", "b"]
    with pytest.raises(RuntimeError):
        FL.http_list("p/", get=lambda url: _R(403, b""))
    with pytest.raises(RuntimeError):
        FL.http_list("p/", get=lambda url: _R(200, _page(["a"], True, None)))


# ---------------------------------------------------------------- retroactive, demote-only relabel
SERIES = {"KXHIGHLAX": GT_URL, "KXBTCD": BTC_URL, "KXATTYGENMN": None}


def rec(status, events, utc="2026-09-27T18:00:00Z", legs=None):
    return {"status": status, "event_tickers": events, "logged_utc_ns": FL.iso_to_ns(utc),
            "extra": {"provenance": {"legs": legs}} if legs else {}}


def test_legacy_weather_record_is_demoted_as_superseded():
    r = rec("GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", ["KXHIGHLAX-26SEP28"])
    assert TR.retro_status(r, list(BUCKET_2026_09_29), SERIES) == ("CANDIDATE_TERMS_UNVERIFIED", "TERMS_SUPERSEDED_AT_SNAPSHOT")
    before = rec("GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", ["KXHIGHLAX-26AUG01"], utc="2026-08-01T00:00:00Z")
    assert TR.retro_status(before, list(BUCKET_2026_09_29), SERIES)[1] == "TERMS_FILINGS_NOT_CHECKED_AT_SNAPSHOT"


def test_legacy_mecnet_exemption_record_is_demoted():
    r = rec("GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", ["KXATTYGENMN-26"])
    assert TR.retro_status(r, list(BUCKET_2026_09_29), SERIES) == ("CANDIDATE_TERMS_UNVERIFIED", "TERMS_NOT_VERIFIED_AT_SNAPSHOT")


def test_checked_record_stands_unless_a_filing_it_did_not_know_was_already_posted():
    legs = {"L": {"terms_url": BTC_URL, "terms_status": "TERMS_VERIFIED", "terms_filing_status": "OK",
                  "terms_known_filings": [[f.key, f.last_modified, f.size] for f in BTC.known_filings]}}
    r = rec("RULE_DEFINED_LOCK", ["KXBTCD-26SEP27"], legs=legs)
    assert TR.retro_status(r, list(BUCKET_2026_09_29), SERIES) == ("RULE_DEFINED_LOCK", None)
    late = F("regulatory/notices/BTC Amendment 3 for posting.pdf", "2026-09-27T12:00:00.000Z", 9)
    assert TR.retro_status(r, list(BUCKET_2026_09_29) + [late], SERIES)[1] == "TERMS_SUPERSEDED_AT_SNAPSHOT"
    later = dataclasses.replace(late, last_modified="2026-09-28T12:00:00.000Z")
    assert TR.retro_status(r, list(BUCKET_2026_09_29) + [later], SERIES) == ("RULE_DEFINED_LOCK", None)
    assert TR.retro_status(r, list(BUCKET_2026_09_29) + [later], SERIES, grace_s=2 * 86400)[1] == "TERMS_SUPERSEDED_AT_SNAPSHOT"


def test_retro_never_promotes():
    for s in ("CANDIDATE_TERMS_UNVERIFIED", "STATISTICAL", "REJECTED", "FEE_UNRESOLVED"):
        assert TR.retro_status(rec(s, ["KXBTCD-26SEP27"]), [], SERIES) == (s, None)
