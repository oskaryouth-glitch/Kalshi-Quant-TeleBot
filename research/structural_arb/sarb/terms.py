"""Registry of contract terms that have been VERIFIED by reading the official PDF.

A family of markets can only reach the ARBITRAGE label if its series' `contract_terms_url` is in
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


_CRYPTO_CITES = (
    "Payout Criterion: 'between' -> '>= lower ... and <= greater value' (inclusive)",
    "Payout Criterion: 'If no data is available on the Expiration Date at the Expiration Time, then the market resolves to No.'",
    "Underlying: simple average of the RTI for the 60 seconds prior to <time> (no rounding stated -> real-valued)",
    "Contingencies: Market Outcome Review Process, Rule 6.3(c)",
)

REGISTRY: dict[str, VerifiedTerms] = {t.url: t for t in (
    VerifiedTerms("https://assets.kalshi.com/contract_terms/BTC.pdf",
                  "e7d857369971e75e9db14c5e2d91c29b94eb9a06e83e2acd9777991c4f2a0e2f",
                  True, "ALL_NO", _CRYPTO_CITES),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/ETH.pdf",
                  "ae079241099608c13c0c0ed31a6c91be174c6e61abe706dd76e8976ba682cc6d",
                  True, "ALL_NO", _CRYPTO_CITES),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/INX.pdf",
                  "9f79e958a612e605d37ec091cbbdc8d1748f4d2831ff338a808814eb75ea9d38",
                  True, "LAST_VALUE", (
                      "Payout Criterion: 'between' inclusive of both values",
                      "Payout Criterion: 'If no data is available ... the Expiration Value will be the value most recently available prior to that <time>.'",
                      "<on/before>: 'before' variants are path-dependent (hit) contracts",
                      "Contingencies: Market Outcome Review Process, Rule 6.3(c)",
                  )),
    VerifiedTerms("https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf",
                  "160281687cf9d3cd694c1c419522f3d53a8e1a6d4eddd40a7f5559c3a06211d0",
                  True, "DISCRETIONARY", (
                      "Operators: 'Above' >, 'below' <, 'at least' >=, 'between' inclusive (>= lower and <= upper)",
                      "'exactly' = equal when rounded to one decimal place (not supported by the scanner)",
                      "'If no data is available ... all strikes shall resolve to the last fair price as determined in the sole discretion of the Exchange.'",
                      "'Contract resolution is based on the full precision reported by the Source Agency.' (no integer rounding -> real-valued)",
                  )),
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
