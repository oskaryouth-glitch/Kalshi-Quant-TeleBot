# D1: BTC/ETH contract-terms change on 2026-09-29, rules-only evidence and protocol ruling

- **Status:** evidence only.
  - The verified terms registry (`research/structural_arb/sarb/terms.py`) is **unchanged**.
  - BTC/ETH remain fail-closed (`TERMS_FILING_CHANGED`).
  - structural_arb is not frozen and not started.
- **Inputs:** documents only; no price, book, opportunity or collection data was used.
  - Kalshi's public regulatory bucket (`kalshi-public-docs.s3.amazonaws.com`) and CDN (`assets.kalshi.com`);
  - the reviewed PDFs committed in `structural_arb/sources/contract_terms/`.
- **Tool:** `evidence/d1_btc_eth_terms/d1_compare.py`. Outputs are in `evidence/d1_btc_eth_terms/outputs/`, and the replaced PDFs are saved beside the script.
- **Not reachable from this environment:** cftc.gov (no response).
- H038/H039 were not touched.

## 1. What changed

| | BTC | ETH |
|---|---|---|
| reviewed served PDF (registry `sha256`) | `e7d85736…`, 24,445 B | `ae079241…`, 24,347 B |
| bucket `contract_terms/<T>.pdf` now | `7bba1b81…`, 38,090 B, LastModified 2026-09-29T20:38:36Z | `74bae3f5…`, 37,895 B, LastModified 2026-09-29T20:38:52Z |
| CDN `assets.kalshi.com/contract_terms/<T>.pdf` | still the reviewed PDF (CloudFront cache hit) | **both** versions served within the same hour: new PDF on one request (cache miss), reviewed PDF on a later one |
| controlling filing (registry) | `regulatory/notices/BTC Amendment 2 for posting.pdf`, sha `efd80967…`: **unchanged** | `…/ETH Amendment 2 for posting.pdf`, sha `1c62e7e6…`: **unchanged** |
| new BTC/ETH regulatory filing | **none** (only the four reviewed objects exist; the certification and both amendments are unchanged) | **none** |

**Context.**
- The two replacements are part of a bulk rewrite: 621 `contract_terms/` objects were modified between 20:00 and 21:00 UTC on 2026-09-29.
- From 21:35Z, 19 amendment filings for *other* templates were posted, several dated months earlier. For example, DOTMINMAX's is dated 2025-05-27 and already carries a "$25,000 per strike" Position Accountability Level.

**Exact textual change.** A whitespace-insensitive character diff of the full extracted text, reviewed → new, is identical for BTC and ETH:

| | text |
|---|---|
| removed | "**Position Limit:** The Position Limit for the $1 referred Contract shall be **$1,000,000** per strike, per Member." |
| added | "**Position Accountability Level:** The Position Accountability Level for the $1 referred Contract shall be **$25,000** per strike, per Member." |

Nothing else in either document differs, not even by one character.

## 2. Outcome-relevant language: **no change**

Each of these clauses is textually identical, reviewed vs new, for both BTC and ETH:
- Underlying (the BRTI/ERTI 60-second average before `<time>`, with post-expiration revisions ignored);
- Source Agency (CF Benchmarks);
- Type, Issuance, and the `<price>`/`<date>`/`<time>` strike and listing definitions;
- Payout Criterion; Minimum Tick; Last Trading Date;
- Expiration Date and Expiration time, including the no-data branch ("the market resolves to No");
- Expiration Value; Settlement Date; Settlement Value;
- Contingencies (Market Outcome Review, Rule 6.3(c)).

The registry's live-rules markers (`CF Benchmarks`, `BRTI`/`ERTI`) are present in the new PDFs.

**Therefore:**
- settlement, payout, strike, determination-source, cancellation and material-error language is unchanged;
- `between_inclusive`, `no_data = ALL_NO` and the documented common-determination basis are unaffected.

## 3. Does the $25,000 Position Accountability Level affect the structural-lock assumptions? **No, at the frozen sizes**

- **Rule 5.18 (DCM Rulebook v1.29, sha `3b6d4ffd…`).** A Participant *exceeding* the level must:
  - provide information;
  - "refrain from increasing … or reduce … if instructed"; and
  - may have the position liquidated below the level if it fails to reduce.

  It is not a hard cap. Rule 5.19's Position Limit, by contrast, makes merely exceeding it a violation.
- **Size.** The frozen evaluator's largest size is 100 contracts per leg (`SIZE_GRID = (1, 10, 100)`), at most $100 per strike. That is 250× below $25,000, so the accountability provisions cannot be triggered by any size the protocol evaluates.
- **Model.** The payoff model never uses position limits.
- **Residual note for any future scaling beyond this experiment.** Above $25,000 per strike, the Rule 5.18(c) liquidation authority is an Exchange-discretionary action that could remove one leg of a lock. It would join Rules 5.11/6.3(c)/7.2 as a listed residual risk. It is not relevant to the frozen protocol.

## 4. Does the existing verification protocol permit accepting the new PDFs? **No. It requires a filing. Stopping here.**

The pre-specified standard, as approved and implemented, is:

1. **TERMS_AUDIT.md §6 (principle):** "`TERMS_VERIFIED` must mean that a human verified the **currently controlling filed terms**, that nothing newer or pending exists, and that **the served copy and the live market rules do not contradict them**. Any doubt yields a non-verified status."
2. **`sarb/terms.py` (docstring and schema).**
   - It is a registry of terms "VERIFIED by reading the CONTROLLING FILED terms".
   - `citations` must quote the controlling filing's Appendix A.
   - `controlling_filing` must be a `regulatory/` bucket key (enforced in `VerifiedTerms.__post_init__`).
3. **TERMS_AUDIT.md §6.3, test 5:** "Served text contradicts the filing → `TERMS_SOURCE_CONFLICT`", a non-verified status.
4. **§6.2:** "Never auto-promote. Any non-verified status needs a human re-review that writes a new registry entry (**new controlling filing** and hashes)."
5. **The approved BTC/ETH re-key basis** (STRUCTURAL_TERMS_V2.md, decision 1): "every sentence of the served PDFs occurs in the Amendment 2 Appendix A".

**Facts against that standard:**
- The new served PDFs contain one sentence that is in **no** posted BTC/ETH filing.
- That sentence **contradicts** the controlling filing: Amendment 2 Appendix A says "Position Limit … $1,000,000 per strike, per Member".
- By Rulebook 5.18(a)/5.19(a), the level is itself a contract term ("as specified in each contract's Terms and Conditions"), not an exchange-wide setting.
- Kalshi's own practice is to file position-level changes as 40.6 contract amendments. For example, the ECONSTAT amendment lists "A simple increase of the Position Accountability Limit" as a numbered change.

**Conclusion.**
- The served copy contradicts the controlling filed terms, and no filed text backs it. Under the existing standard BTC/ETH **cannot** be verified. Independent verification against the settlement rules is **not** sufficient: the standard has no materiality carve-out for non-outcome terms.
- Adopting "only outcome-relevant contradictions matter", or keying the registry to the served PDF instead of a filing, would weaken or reinterpret the standard. I have done neither.
- A filing that exists only on the CFTC portal cannot be used under the current protocol either, because the controlling filing must be a bucket object. Using one would also be a protocol change.

**What would unblock BTC/ETH without changing the standard:**
1. Kalshi posts a BTC/ETH amendment to the bucket whose Appendix A contains the new text.
   - The code will then report `TERMS_SUPERSEDED`.
   - A human re-review would write new entries keyed to that filing, with a new CONFIG_VERSION, commit and manifest, and your sign-off.
   - The frozen `AMENDMENT_PENDING_S` (16 days, counted from the filing's bucket LastModified) then applies before the status can be `OK`. This holds even if the filing is back-dated, which is conservative.
2. Or the served copies revert to the filed text.

Until one of these happens, 0 markets are terms-verified, and per your instruction structural_arb is not frozen or started.
