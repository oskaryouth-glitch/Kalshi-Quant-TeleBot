"""Registry of contract terms that have been VERIFIED by reading the CONTROLLING FILED terms.

A family of markets can only reach the RULE_DEFINED_LOCK label if its series' `contract_terms_url` is in
this registry AND all of the following hold at snapshot time (`lookup`):
  * the PDF served at that URL has the recorded SHA-256 (a change means someone must re-review);
  * the filing record is unchanged (sarb/filings.py): a fresh, complete listing of the public
    regulatory bucket shows exactly the objects that existed for the template when it was
    reviewed, the controlling filing still hashes to the reviewed value, and it is not inside
    the Reg. 40.6 waiting period. A new amendment therefore lapses verification automatically,
    even if the served PDF is never replaced (the GLOBALTEMPERATURE failure; TERMS_AUDIT.md);
  * the live market rules text contains every `rules_required` phrase and no `rules_forbidden`
    phrase (checked per market in semantics.build_market_spec -> TERMS_RULES_CONFLICT).
Code can only DEMOTE an entry. Promotion needs a human re-review that writes a new entry.

Each entry records the facts the payoff model depends on. Every fact cites its clause.
  between_inclusive : "between" includes both endpoints (True/False), or None if unstated.
  no_data           : what happens when no Expiration Value can be determined.
                      ALL_NO        -> an extra determinate state where every market resolves No
                      LAST_VALUE    -> the most recent value is used (stays inside the X-model)
                      DISCRETIONARY -> Exchange-determined "last fair price" (residual risk,
                                       not a determinate state)
  All terms also allow the Market Outcome Review Process (Rulebook 6.3(c)/7.1, discretionary),
  and Rulebook 7.2 contract modifications. Both are residual risks for every candidate.

VERIFICATION STANDARD (2026-09-27, after the AAA/SOL equivalence review). Every market is a
separate Contract, so terms qualify only if they force EVERY contract of a family onto the SAME
Expiration Value in every non-discretionary state (`common_determination`). A value fixed at an
Exchange-chosen or per-contract expiration instant, with post-expiration revisions ignored, does
NOT qualify.

SUPPORTED no_data values: ALL_NO, LAST_VALUE, DISCRETIONARY. Terms whose no-data rule acts
per contract or per strike (e.g. CRYPTO.pdf: "affected strikes resolve to No") need per-market
No-resolution states that the payoff model does not yet enumerate. They must NOT be registered
(the guard below enforces this) until the model supports them.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import filings as FL
from .filings import Filing


@dataclass(frozen=True)
class VerifiedTerms:
    url: str
    sha256: str                        # served PDF at `url`, as reviewed
    between_inclusive: bool | None
    no_data: str
    citations: tuple[str, ...]         # quote the CONTROLLING filing's Appendix A
    common_determination: str = ""     # why all contracts of a family share one Expiration Value
    template: str = ""                 # filing name ("Rulebook: <template>")
    controlling_filing: str = ""       # bucket key of the filing whose Appendix A was reviewed
    controlling_filing_sha256: str = ""
    known_filings: tuple[Filing, ...] = ()   # EVERY bucket object for the template at review time
    rules_required: tuple[str, ...] = ()     # phrases every live market's rules text must contain
    rules_forbidden: tuple[str, ...] = ()    # phrases no live market's rules text may contain
    reviewed: str = ""                 # who reviewed, when, against what

    def __post_init__(self):
        if self.no_data not in SUPPORTED_NO_DATA:
            raise ValueError(f"{self.url}: no_data={self.no_data!r} is not supported by the payoff model")
        if not self.common_determination:
            raise ValueError(f"{self.url}: common-determination basis must be documented")
        if not (self.template and self.controlling_filing.startswith("regulatory/")
                and len(self.controlling_filing_sha256) == 64 and self.reviewed):
            raise ValueError(f"{self.url}: controlling filing, its sha256 and the review record are required")
        keys = [f.key for f in self.known_filings]
        if self.controlling_filing not in keys or len(set(keys)) != len(keys):
            raise ValueError(f"{self.url}: known_filings must list the controlling filing once")
        if not all(FL.belongs(self.template, k) for k in keys):
            raise ValueError(f"{self.url}: known_filings contains an object that is not {self.template}'s")
        ctrl = next(f for f in self.known_filings if f.key == self.controlling_filing)
        if any(f.key.startswith("regulatory/") and f.last_modified > ctrl.last_modified for f in self.known_filings):
            raise ValueError(f"{self.url}: a known filing is newer than the controlling filing (review the newest)")


SUPPORTED_NO_DATA = frozenset({"ALL_NO", "LAST_VALUE", "DISCRETIONARY"})
UNSUPPORTED_NO_DATA_SEMANTICS = ("PER_MARKET_NO", "PER_STRIKE_NO")      # documented, never registrable yet


_CRYPTO_CITES = (
    "Payout Criterion: 'between' -> '>= lower ... and <= greater value' (inclusive)",
    "Payout Criterion: 'If no data is available on the Expiration Date at the Expiration Time, then the market resolves to No.'",
    "Underlying: simple average of the RTI for the 60 seconds prior to <time> (no rounding stated -> real-valued)",
    "Contingencies: Market Outcome Review Process, Rule 6.3(c)",
)

_CRYPTO_COMMON = ("Expiration Date/time = 'the first minute after <time> that data is available' (else one week "
                  "after <date>): fixed by data availability, identical for every contract with the same <time>/<date>; "
                  "'no data' -> 'the market resolves to No' at that same common instant, hence one ALL_NO state.")

# REMOVED 2026-09-27 (methodology audit): contract_terms/INX.pdf (sha 9f79e958...). Its Expiration time
# is 'the sooner of the first 10:00 AM ET following the occurrence of an event encompassed by the Payout
# Criterion or AT LEAST ONE MINUTE AFTER <time>', and the Source Agency is Kalshi, with revisions after
# expiration ignored. That does not force a common determination instant across contracts (the same
# divergence channel that made the AAA gas family TERMS_EQUIVALENCE_UNRESOLVED). INX families are
# therefore capped at CANDIDATE_TERMS_UNVERIFIED.
REMOVED = {"https://assets.kalshi.com/contract_terms/INX.pdf": "no common determination instant (see comment)"}

_BTC_FILINGS = (
    Filing("regulatory/product-certifications/BTC.pdf", "2024-03-14T21:20:02.000Z", 158894),
    Filing("regulatory/notices/BTC Amendment for posting.pdf", "2024-11-12T07:33:48.000Z", 256777),
    Filing("contract_terms/BTC.pdf", "2025-03-17T08:34:12.000Z", 24445),
    Filing("regulatory/notices/BTC Amendment 2 for posting.pdf", "2025-04-28T14:27:29.000Z", 274431),
)
_ETH_FILINGS = (
    Filing("regulatory/product-certifications/ETH.pdf", "2024-03-14T21:20:03.000Z", 158589),
    Filing("regulatory/notices/ETH Amendment for posting.pdf", "2024-11-12T07:33:59.000Z", 255887),
    Filing("contract_terms/ETH.pdf", "2025-03-17T08:33:33.000Z", 24347),
    Filing("regulatory/notices/ETH Amendment 2 for posting.pdf", "2025-04-28T14:27:37.000Z", 273544),
)
_CRYPTO_REVIEW = ("PROPOSED 2026-09-29 (edge_search/TERMS_AUDIT.md): every sentence of the served PDF (sha as "
                  "registered 2026-09-27) occurs in the Amendment 2 Appendix A; the only extra lines are filing "
                  "letterhead. Facts and citations unchanged. REQUIRES independent reviewer sign-off.")

# GLOBALTEMPERATURE: SUPERSEDED. The entry stays pinned to what was actually reviewed on 2026-09-27: the
# served PDF, whose Appendix A equals the 2025-12-12 product certification. Amendments filed 2026-08-17
# (The Weather Company becomes first Source Agency) and 2026-09-02 (Exchange-specified reports; material-
# error expiration delay) are NOT in known_filings, so filings.status() returns TERMS_SUPERSEDED and the
# `rules_required` check fails on live rules that name The Weather Company. Re-registration needs a human
# re-review against Amendment 2, including whether the material-error delay breaks the common
# determination (the INX question; TERMS_AUDIT.md §4). Until then every weather family is capped at
# CANDIDATE_TERMS_UNVERIFIED.
_GLOBALTEMPERATURE_FILINGS = (
    Filing("regulatory/product-certifications/GLOBALTEMPERATURE.pdf", "2025-12-12T18:08:25.000Z", 267225),
    Filing("contract_terms/GLOBALTEMPERATURE.pdf", "2025-12-12T18:08:27.000Z", 31861),
)

REGISTRY: dict[str, VerifiedTerms] = {t.url: t for t in (
    VerifiedTerms("https://assets.kalshi.com/contract_terms/BTC.pdf",
                  "e7d857369971e75e9db14c5e2d91c29b94eb9a06e83e2acd9777991c4f2a0e2f",
                  True, "ALL_NO", _CRYPTO_CITES, _CRYPTO_COMMON,
                  template="BTC", controlling_filing="regulatory/notices/BTC Amendment 2 for posting.pdf",
                  controlling_filing_sha256="efd80967164d20f1ebfe71e88e21a8d79083957b2d16d7af4e535fc2f9042dd8",
                  known_filings=_BTC_FILINGS, rules_required=("CF Benchmarks", "BRTI"), reviewed=_CRYPTO_REVIEW),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/ETH.pdf",
                  "ae079241099608c13c0c0ed31a6c91be174c6e61abe706dd76e8976ba682cc6d",
                  True, "ALL_NO", _CRYPTO_CITES, _CRYPTO_COMMON,
                  template="ETH", controlling_filing="regulatory/notices/ETH Amendment 2 for posting.pdf",
                  controlling_filing_sha256="1c62e7e6faf01b125078ef847e6c0592b89adf95b52950b73fc0c99e0c69a995",
                  known_filings=_ETH_FILINGS, rules_required=("CF Benchmarks", "ERTI"), reviewed=_CRYPTO_REVIEW),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf",
                  "160281687cf9d3cd694c1c419522f3d53a8e1a6d4eddd40a7f5559c3a06211d0",
                  True, "DISCRETIONARY", (
                      "Operators: 'Above' >, 'below' <, 'at least' >=, 'between' inclusive (>= lower and <= upper)",
                      "'exactly' = equal when rounded to one decimal place (not supported by the scanner)",
                      "'If no data is available ... all strikes shall resolve to the last fair price as determined in the sole discretion of the Exchange.'",
                      "'Contract resolution is based on the full precision reported by the Source Agency.' (no integer rounding -> real-valued)",
                      "Source Agency: 'in hierarchical order, National Weather Service, the national weather service for <area>'",
                  ), "'Only the first official non-preliminary report published by the Source Agencies that includes "
                     "the relevant data will be used for resolution' -> one report fixes the value for every contract, "
                     "whatever each contract's expiration instant (Expiration time fixed at 10:00 AM ET).",
                  template="GLOBALTEMPERATURE",
                  controlling_filing="regulatory/product-certifications/GLOBALTEMPERATURE.pdf",
                  controlling_filing_sha256="44fe7807bd884def6f2890813220a746802ac7bd3791d17c69607dbf66ba03fc",
                  known_filings=_GLOBALTEMPERATURE_FILINGS, rules_required=("National Weather Service",),
                  reviewed="2026-09-27 methodology audit, against the served PDF (= 2025-12-12 certification "
                           "Appendix A). SUPERSEDED by the 2026-08-17 and 2026-09-02 amendments; see comment above."),
)}


def lookup(url: str | None, fetched_sha256: str | None,
           filing_status: str | None = None) -> tuple[VerifiedTerms | None, str]:
    """Returns (terms, reason). terms is None unless the URL is registered, the served PDF hash matches
    AND `filing_status` (filings.status() for this URL, now) is OK. Not checked -> not verified."""
    if not url:
        return None, "TERMS_URL_MISSING"
    t = REGISTRY.get(url)
    if t is None:
        return None, "TERMS_UNVERIFIED"
    if fetched_sha256 is None:
        return None, "TERMS_HASH_NOT_CHECKED"
    if fetched_sha256 != t.sha256:
        return None, "TERMS_HASH_CHANGED"
    if filing_status is None:
        return None, "TERMS_FILINGS_NOT_CHECKED"
    if filing_status != FL.OK:
        return None, filing_status if filing_status in FL.NON_OK_STATUSES else "TERMS_FILINGS_NOT_CHECKED"
    return t, "TERMS_VERIFIED"


def rules_conflicts(t: VerifiedTerms, market: dict) -> list[str]:
    """Live market rules text vs the reviewed terms: required phrases missing, forbidden phrases present."""
    text = f"{market.get('rules_primary') or ''} {market.get('rules_secondary') or ''}".casefold()
    return ([f"MISSING:{p}" for p in t.rules_required if p.casefold() not in text]
            + [f"FORBIDDEN:{p}" for p in t.rules_forbidden if p.casefold() in text])
