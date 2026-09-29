# Proposed patch: amendment-aware, fail-closed terms verification for `structural_arb`

- **Status:** **PROPOSED, NOT APPLIED.** `research/structural_arb` is unchanged in this repository. The patch is `structural_terms_v2.patch` (sha256 `24da471a…`).
- **Base:** commit `49a6aa9`.
- **Why:** `../TERMS_AUDIT.md`. The registry pinned only the bytes of the served terms PDF, so the 61 GLOBALTEMPERATURE series stayed `TERMS_VERIFIED` after two filed amendments.
- H038/H039 are not touched.

## How it was validated (all outside the repository tree)

1. The patch was written in a scratch copy of `research/structural_arb`.
   - Its full suite passes: **945 passed** (the 905 existing tests plus 40 new).
   - Re-applied with `patch -p1` to a fresh copy: 945 passed again.
   - `git apply --check` succeeds against this repository's tree.
2. **Live check** of the patched filing code against the public regulatory bucket (2026-09-29 04:2x UTC):

   | template | status |
   |---|---|
   | BTC | OK |
   | ETH | OK |
   | GLOBALTEMPERATURE | **TERMS_SUPERSEDED** |

   All controlling-filing hashes match.
3. **Retroactive, demote-only relabel** (`scripts/terms_retro_report.py`) over the recorded 2026-09-27 validation data. The data is only read. Full output: `structural_terms_v2_retro_report.json`.

   | records | relabel | reason |
   |---|---|---|
   | 47 weather `R1_SHORT` | `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE → CANDIDATE_TERMS_UNVERIFIED` | `TERMS_SUPERSEDED_AT_SNAPSHOT` |
   | 362 pre-audit MECNET `R1_EXCLUSIVE_PAIR` | `→ CANDIDATE_TERMS_UNVERIFIED` | `TERMS_NOT_VERIFIED_AT_SNAPSHOT` (the removed MECNET exemption) |

   Nothing else was lock-like, and nothing is promoted.

To apply after review: `git apply research/edge_search/proposals/structural_terms_v2.patch`, then `cd research/structural_arb && python -m pytest -q`.

## What the patch changes (13 files, +638/−38 lines)

| file | change |
|---|---|
| `sarb/filings.py` (new) | Filing record per template. `refresh()` lists the three bucket prefixes **in full** (paginated; any HTTP, parse or truncation error aborts) and hashes each template's controlling filing. `status()` is a pure function returning `OK` or one of 9 non-OK codes (below). Template matching is a case-insensitive whole-token match anywhere in the file name. The bucket holds names like `processed-DCEIL modification (3).pdf`, so a name-prefix query would miss amendments. |
| `sarb/terms.py` | `VerifiedTerms` gains `template`, `controlling_filing`, `controlling_filing_sha256`, `known_filings` (every bucket object for the template at review), `rules_required`, `rules_forbidden` and `reviewed`. Construction fails if the filing basis is missing or inconsistent (for example, a known regulatory filing newer than the controlling one). `lookup(url, served_sha, filing_status)` returns `TERMS_VERIFIED` only with an `OK` filing status: *not checked → not verified*. New `rules_conflicts()`. |
| registry | **BTC, ETH:** re-keyed to their controlling "Amendment 2 for posting" filings (2025-04-28), with the full 4-object filing sets. Required live-rules phrases: `CF Benchmarks` plus `BRTI`/`ERTI`. Facts and citations unchanged. Marked *PROPOSED, requires independent sign-off*. **GLOBALTEMPERATURE:** stays pinned to what was actually reviewed (served PDF = 2025-12-12 certification; filing set = those two objects; required phrase `National Weather Service`). The new code therefore reports `TERMS_SUPERSEDED`, and live rules fail `rules_required` because they name The Weather Company. |
| `sarb/semantics.py`, `sarb/universe.py` | Per-URL filing status threaded into `build_market_spec` and the spec cache fingerprint. Live `rules_primary`/`rules_secondary` are checked against the entry, giving `TERMS_RULES_CONFLICT`. New `MarketSpec` fields: `terms_filing_status` and `terms_rules_conflicts`. |
| `sarb/collector.py` | Hourly filing refresh (with the served-PDF hash refresh). Filing status is computed per cycle for the build and recorded in the universe stream. At the **P3 re-check** the filing status is re-evaluated, so a listing that aged out or changed blocks the lock (`TERMS_FILINGS_NOT_OK:<status>`). Provenance records the controlling filing, its sha, the known filing set, the listing time and any rules conflicts. The lister and fetcher are injectable for tests. |
| `sarb/reconstruct.py` | Filing status is taken as recorded, like the P3 re-hash. Records without one cannot re-verify. |
| `sarb/terms_retro.py` (new), `scripts/terms_retro_report.py` (new) | Demote-only re-evaluation of recorded lock-like candidates. Report only; never rewrites data. |
| `sarb/config.py` | `MAX_FILINGS_LISTING_AGE_S = 7200`; `AMENDMENT_PENDING_S = 16 days`, which bounds Reg. 40.6(a)'s 10 business days including up to two holidays. `CONFIG_VERSION` bumped. |
| `DESIGN.md` | A7/A9, the status table, I.1 and I.4 updated. Also fixes the stale "(or MECNET …)" wording. |
| tests | New `tests/test_filings.py` (26 cases, including the live-registry fixtures as of 2026-09-29). 7 new collector integration tests (amendment posted, served PDF unchanged → demoted; listing failure; controlling-fetch failure; stale listing; filing change between build and P3; provenance). 7 new semantics cases. Fixtures updated for the richer `VerifiedTerms`. |

**Fail-closed status codes** (`filings.status`). Every code below is non-OK and caps the family at `CANDIDATE_TERMS_UNVERIFIED`:

| code | cause |
|---|---|
| `TERMS_FILINGS_NOT_CHECKED` | no listing |
| `TERMS_FILINGS_UNAVAILABLE` | listing error or truncation |
| `TERMS_FILINGS_STALE` | listing older than 2 h, or from the future |
| `TERMS_SUPERSEDED` | a new regulatory object for the template |
| `TERMS_FILINGS_UNRECOGNISED` | any other new object |
| `TERMS_FILINGS_INCOMPLETE` | a reviewed object is missing |
| `TERMS_FILING_CHANGED` | LastModified or size differs |
| `TERMS_CONTROLLING_FILING_UNCONFIRMED` | fetch failed, or sha differs |
| `TERMS_AMENDMENT_PENDING` | controlling filing posted under 16 days ago |

On top of these, `TERMS_HASH_CHANGED` (served PDF) and `TERMS_RULES_CONFLICT` (live rules) apply.

## Decisions for the reviewer

1. **Sign off or reject** the BTC/ETH re-keying. Evidence: every sentence of the served PDFs occurs in the Amendment 2 Appendix A; the only extra lines are letterhead (`../evidence/terms_audit/outputs/terms_audit.txt`).
2. **GLOBALTEMPERATURE re-review** (not part of this patch). Amendment 2 lets the Exchange delay expiration after a material error "until publication of revised data". Contracts of one family can expire at different instants (Rule 7.2 early expiration), so one contract could settle on the initial report and another on a revision. Either:
   - re-register with a revised `common_determination` that treats this as a discretionary residual state; or
   - de-register as with INX.
3. **Parameters:** `MAX_FILINGS_LISTING_AGE_S` (2 h) and `AMENDMENT_PENDING_S` (16 days) are proposals.
4. **Residual risks the patch cannot remove** (TERMS_AUDIT.md §6.4):
   - filings never posted to the bucket, or posted late (the CFTC portal is authoritative but unreachable here);
   - rulebook-wide amendments that do not name a template;
   - discretion inside the controlling text;
   - `rules_required` catches only the phrases someone listed.
