"""Amendment-aware terms verification: the filing record for each registered template.

Why this exists (TERMS_AUDIT.md, 2026-09-29): the registry used to pin only the bytes of the PDF
served at `contract_terms_url`. Kalshi amended GLOBALTEMPERATURE twice under CFTC Reg. 40.6
(2026-08-17, 2026-09-02) without replacing that PDF, so every weather series stayed
TERMS_VERIFIED against superseded terms. A served-PDF hash cannot detect an amendment.

This module checks the FILING RECORD instead. Kalshi posts every product certification and
amendment to the public regulatory bucket. For each registered template the registry records
the complete set of objects that existed for that template when a human reviewed it
(`VerifiedTerms.known_filings`) and which filing's Appendix A was reviewed
(`controlling_filing`). A fresh, complete listing must reproduce that set exactly, and the
controlling filing must still hash to the reviewed value. Every other outcome is a non-OK
status, and nothing here can turn a non-OK status into OK.

FAIL-CLOSED RULES
  * a listing that errored, was truncated or could not be parsed  -> TERMS_FILINGS_UNAVAILABLE
  * a listing older than config.MAX_FILINGS_LISTING_AGE_S          -> TERMS_FILINGS_STALE
  * a new regulatory object for the template                       -> TERMS_SUPERSEDED
  * any other new object for the template                          -> TERMS_FILINGS_UNRECOGNISED
  * a reviewed object missing from the listing                     -> TERMS_FILINGS_INCOMPLETE
  * a reviewed object whose LastModified or size changed           -> TERMS_FILING_CHANGED
  * the controlling filing not fetched, or its sha256 differs      -> TERMS_CONTROLLING_FILING_UNCONFIRMED
  * controlling filing posted < config.AMENDMENT_PENDING_S ago     -> TERMS_AMENDMENT_PENDING
    (Reg. 40.6(a): a self-certified change may take effect 10 business days after filing, so
     the previous version may still be in force; 16 calendar days bounds 10 business days
     with up to two holidays)

A key belongs to template T if T occurs anywhere in its file name as a whole token (case-insensitive,
not adjacent to a letter or digit). So "BTCMINMAX.pdf" and "KXBTC.pdf" are not BTC's, but
"BTC Amendment 3.pdf", "BTC_v2.pdf" and "processed-BTC modification (3).pdf" all are. The bucket has
names of that last shape, so the whole of each prefix is listed rather than a name-prefix query.
An ambiguous name therefore counts against verification, never for it.

Residual risk (not removable here): a filing that is never posted to the bucket, or posted
late, is invisible. The CFTC portal is authoritative. See TERMS_AUDIT.md §6.4.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from . import config

BUCKET_URL = "https://kalshi-public-docs.s3.amazonaws.com/"
PREFIXES = ("regulatory/product-certifications/", "regulatory/notices/", "contract_terms/")
_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

OK = "OK"
NON_OK_STATUSES = ("TERMS_FILINGS_NOT_CHECKED", "TERMS_FILINGS_UNAVAILABLE", "TERMS_FILINGS_STALE",
                   "TERMS_SUPERSEDED", "TERMS_FILINGS_UNRECOGNISED", "TERMS_FILINGS_INCOMPLETE",
                   "TERMS_FILING_CHANGED", "TERMS_CONTROLLING_FILING_UNCONFIRMED", "TERMS_AMENDMENT_PENDING")


@dataclass(frozen=True)
class Filing:
    key: str             # object key in the public regulatory bucket
    last_modified: str   # S3 LastModified (ISO 8601, as listed)
    size: int


@dataclass(frozen=True)
class Listing:
    """One complete listing of a template's objects, made at `listed_utc_ns`. `objects` is None if
    the listing failed; `controlling_sha256` is the sha256 of the controlling filing fetched in the
    same refresh (None if it was not fetched or the fetch failed)."""
    template: str
    listed_utc_ns: int
    objects: tuple[Filing, ...] | None
    controlling_sha256: str | None = None
    error: str = ""


def belongs(template: str, key: str) -> bool:
    for pre in PREFIXES:
        if key.startswith(pre):
            return re.search(rf"(?<![A-Za-z0-9]){re.escape(template)}(?![A-Za-z0-9])", key[len(pre):], re.I) is not None
    return False


def iso_to_ns(s: str) -> int:
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1e9)


def status(terms, listing: Listing | None, now_utc_ns: int) -> str:
    """terms: a VerifiedTerms. Pure function; returns OK or one of NON_OK_STATUSES."""
    if listing is None:
        return "TERMS_FILINGS_NOT_CHECKED"
    if listing.objects is None:
        return "TERMS_FILINGS_UNAVAILABLE"
    if now_utc_ns - listing.listed_utc_ns > config.MAX_FILINGS_LISTING_AGE_S * 1e9 or now_utc_ns < listing.listed_utc_ns:
        return "TERMS_FILINGS_STALE"
    known = {f.key: f for f in terms.known_filings}
    now = {f.key: f for f in listing.objects if belongs(terms.template, f.key)}
    new = [k for k in now if k not in known]
    if any(k.startswith("regulatory/") for k in new):
        return "TERMS_SUPERSEDED"
    if new:
        return "TERMS_FILINGS_UNRECOGNISED"
    if any(k not in now for k in known):
        return "TERMS_FILINGS_INCOMPLETE"
    if any(now[k] != known[k] for k in known):
        return "TERMS_FILING_CHANGED"
    if listing.controlling_sha256 is None or listing.controlling_sha256 != terms.controlling_filing_sha256:
        return "TERMS_CONTROLLING_FILING_UNCONFIRMED"
    if now_utc_ns - iso_to_ns(known[terms.controlling_filing].last_modified) < config.AMENDMENT_PENDING_S * 1e9:
        return "TERMS_AMENDMENT_PENDING"
    return OK


# ---------------------------------------------------------------------------------------------- I/O
def http_list(prefix: str, get=None) -> list[Filing]:
    """Every object under `prefix` (paginated to completion). Raises on any HTTP or parse error, so a
    partial listing can never be mistaken for a complete one."""
    import requests
    get = get or (lambda url: requests.get(url, timeout=30))
    out, token = [], None
    for _ in range(1000):
        q = {"list-type": "2", "prefix": prefix, **({"continuation-token": token} if token else {})}
        r = get(BUCKET_URL + "?" + urllib.parse.urlencode(q))
        if r.status_code != 200:
            raise RuntimeError(f"bucket listing HTTP {r.status_code}")
        root = ET.fromstring(r.content)
        for c in root.findall("s3:Contents", _NS):
            out.append(Filing(c.findtext("s3:Key", namespaces=_NS), c.findtext("s3:LastModified", namespaces=_NS),
                              int(c.findtext("s3:Size", namespaces=_NS))))
        if root.findtext("s3:IsTruncated", namespaces=_NS) != "true":
            return out
        token = root.findtext("s3:NextContinuationToken", namespaces=_NS)
        if not token:
            raise RuntimeError("truncated listing without a continuation token")
    raise RuntimeError("bucket listing did not terminate")


def http_fetch(key: str) -> bytes:
    import requests
    r = requests.get(BUCKET_URL + urllib.parse.quote(key), timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"filing fetch HTTP {r.status_code}")
    return r.content


def refresh(registry, lister=http_list, fetcher=http_fetch, now_ns=time.time_ns) -> dict[str, Listing]:
    """One complete listing of every prefix, split per registered template, plus a fresh hash of each
    template's controlling filing. Returns {registry url: Listing}. A listing error makes every
    template's Listing objects=None (-> TERMS_FILINGS_UNAVAILABLE); a fetch error leaves that
    template's controlling_sha256 None (-> TERMS_CONTROLLING_FILING_UNCONFIRMED)."""
    t0 = now_ns()
    if not registry:
        return {}
    try:
        everything = [f for pre in PREFIXES for f in lister(pre)]
    except Exception as e:                                       # noqa: BLE001  (fail closed on anything)
        return {url: Listing(t.template, t0, None, None, repr(e)[:200]) for url, t in registry.items()}
    out = {}
    for url, t in registry.items():
        objs = tuple(f for f in everything if belongs(t.template, f.key))
        try:
            sha = hashlib.sha256(fetcher(t.controlling_filing)).hexdigest()
            out[url] = Listing(t.template, t0, objs, sha)
        except Exception as e:                                   # noqa: BLE001
            out[url] = Listing(t.template, t0, objs, None, repr(e)[:200])
    return out
