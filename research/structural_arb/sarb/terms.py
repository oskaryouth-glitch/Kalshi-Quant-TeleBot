"""Registry of contract terms that have been VERIFIED by reading the official PDF.

A family of markets can only reach the RULE_DEFINED_LOCK label if its series' `contract_terms_url` is in
this registry AND the PDF fetched at snapshot time has the recorded SHA-256. If Kalshi edits
the terms, the hash changes and verification lapses automatically.

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


@dataclass(frozen=True)
class VerifiedTerms:
    url: str
    sha256: str
    between_inclusive: bool | None
    no_data: str
    citations: tuple[str, ...]
    common_determination: str = ""     # why all contracts of a family share one Expiration Value

    def __post_init__(self):
        if self.no_data not in SUPPORTED_NO_DATA:
            raise ValueError(f"{self.url}: no_data={self.no_data!r} is not supported by the payoff model")
        if not self.common_determination:
            raise ValueError(f"{self.url}: common-determination basis must be documented")


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

REGISTRY: dict[str, VerifiedTerms] = {t.url: t for t in (
    VerifiedTerms("https://assets.kalshi.com/contract_terms/BTC.pdf",
                  "e7d857369971e75e9db14c5e2d91c29b94eb9a06e83e2acd9777991c4f2a0e2f",
                  True, "ALL_NO", _CRYPTO_CITES, _CRYPTO_COMMON),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/ETH.pdf",
                  "ae079241099608c13c0c0ed31a6c91be174c6e61abe706dd76e8976ba682cc6d",
                  True, "ALL_NO", _CRYPTO_CITES, _CRYPTO_COMMON),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf",
                  "160281687cf9d3cd694c1c419522f3d53a8e1a6d4eddd40a7f5559c3a06211d0",
                  True, "DISCRETIONARY", (
                      "Operators: 'Above' >, 'below' <, 'at least' >=, 'between' inclusive (>= lower and <= upper)",
                      "'exactly' = equal when rounded to one decimal place (not supported by the scanner)",
                      "'If no data is available ... all strikes shall resolve to the last fair price as determined in the sole discretion of the Exchange.'",
                      "'Contract resolution is based on the full precision reported by the Source Agency.' (no integer rounding -> real-valued)",
                  ), "'Only the first official non-preliminary report published by the Source Agencies that includes "
                     "the relevant data will be used for resolution' -> one report fixes the value for every contract, "
                     "whatever each contract's expiration instant (Expiration time fixed at 10:00 AM ET)."),
)}


def lookup(url: str | None, fetched_sha256: str | None) -> tuple[VerifiedTerms | None, str]:
    """Returns (terms, reason). terms is None unless the URL is registered AND the hash matches."""
    if not url:
        return None, "TERMS_URL_MISSING"
    t = REGISTRY.get(url)
    if t is None:
        return None, "TERMS_UNVERIFIED"
    if fetched_sha256 is None:
        return None, "TERMS_HASH_NOT_CHECKED"
    if fetched_sha256 != t.sha256:
        return None, "TERMS_HASH_CHANGED"
    return t, "TERMS_VERIFIED"
