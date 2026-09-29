# Structural terms-verification audit (GLOBALTEMPERATURE stale-terms discovery)

- **Date:** 2026-09-29.
- **Scope:** a read-only audit of `research/structural_arb`. **Nothing in `structural_arb` was modified**: no code, registry, data or frozen rules. H038/H039 were not touched.
- **Evidence:**
  - `evidence/terms_audit/terms_audit.py` (reproducible; public GETs only);
  - outputs in `evidence/terms_audit/outputs/terms_audit.{txt,json}`.

## 1. Question and answer

**Can the current architecture label a series `TERMS_VERIFIED` while a later filed amendment supersedes its hashed PDF?**

**Yes. It is doing so today, for all 61 GLOBALTEMPERATURE series.**

- `sarb/terms.py:92` (`lookup`) compares one thing: the SHA-256 of the PDF served at `contract_terms_url` against the hash recorded in `REGISTRY`.
- The collector computes that hash from the served PDF, at build time (`sarb/collector.py:128`) and again live at P3 (`sarb/collector.py:187`).
- Nothing looks at the filing record. Verification therefore lapses only if Kalshi replaces the served PDF.
- Kalshi amended GLOBALTEMPERATURE twice under CFTC Reg. 40.6 without replacing the served PDF:
  - Amendment 1, dated 2026-08-17 and posted 2026-08-18;
  - Amendment 2, dated and posted 2026-09-02.
- The served PDF still has its 2025-12-12 bytes (sha `160281687c…`). `lookup` returns `TERMS_VERIFIED`, and `_terms_ok` (`sarb/evaluator.py:311`) accepts it.

The Exchange is already operating under the amendments.
- All 25 open weather markets sampled today (5 series × 5 markets) name **The Weather Company** as the source.
- All 25 carry the **material-error** clause.
- Neither phrase appears in the hashed PDF.

## 2. Every frozen-registry entry

| registry URL | series bound | `lookup` today | filings in the regulatory bucket (dated or posted) | served terms vs latest filing | verdict |
|---|---|---|---|---|---|
| `contract_terms/GLOBALTEMPERATURE.pdf` (sha `160281687c…`) | **61** | TERMS_VERIFIED | certification 2025-12-12; **Amendment 1 2026-08-18; Amendment 2 2026-09-02** | **Different** (below) | **SUPERSEDED. Verification is invalid.** |
| `contract_terms/BTC.pdf` (sha `e7d8573699…`) | 9 | TERMS_VERIFIED | certification 2024-03-14; Amendment 1 2024-11-12; Amendment 2 2025-04-28 | Every served sentence appears in Amendment 2. The only extra lines are filing letterhead and page headers. | Not superseded |
| `contract_terms/ETH.pdf` (sha `ae07924109…`) | 6 | TERMS_VERIFIED | certification 2024-03-14; Amendment 1 2024-11-12; Amendment 2 2025-04-28 | Same as BTC | Not superseded |

**Bound series:**
- **GLOBALTEMPERATURE (61):**
  - KXHIGH: AUS, CHI, DEN, LAX, MIA, NY, PHIL.
  - KXHIGHT: ATL, BOS, DAL, DC, EGLL, EHAM, EWR, HOU, KSAN, LFPG, LV, MIN, NOLA, OKC, PHX, SAN, SATX, SDF, SEA, SFO, TTN, VHHH, ZSPD.
  - KXLOW: NY.
  - KXLOWT: ATL, AUS, BOS, CHI, DAL, DC, DEN, EWR, HOU, KSAN, LAX, LV, MIA, MIN, NOLA, NYC, OKC, PHIL, PHX, SAN, SATX, SDF, SEA, SFO, TTN.
  - KXWEEKHT: LAS, LAX, MIA, NYC, PHX.
- **BTC (9):** BTC, BTCD, BTCD-B, KXBTC, KXBTCD, KXBTCD-B, KXBTCE, KXBTCEU, KXBTCYEAR.
- **ETH (6):** ETH, ETHD, KXETH, KXETHD, KXETHE, KXETHEU.

**The BTC/ETH case also shows that a date rule alone is wrong.**
- Their Amendment 2 was posted (2025-04-28) *after* the served PDF was last modified (2025-03-17), so a newest-filing-date test flags them.
- Yet the served PDF already carries the amended text. Kalshi updated the served copy before posting the filing.
- An amendment-aware check therefore has to compare text, not just dates.
- No other filings exist for these three templates. Similarly named templates are different contracts: BTCMINMAX, ETHMINMAX, BTCPRICE, BTCETHCOMP, GLOBALTEMPERATURESUSTAINED, INTERNATIONALTEMPERATURE, LOCALTEMPERATURE.

## 3. What changed in GLOBALTEMPERATURE (served PDF → Amendment 2)

| clause | served PDF (what the registry verified) | controlling Amendment 2 |
|---|---|---|
| Source Agency | "in hierarchical order, National Weather Service, the national weather service for <area>…" | "in hierarchical order, **The Weather Company (TWC)**, National Weather Service, …" (Amendment 1) |
| Station | "…primary official weather measurement station(s) … **as designated by the National Weather Service, or as otherwise specified by the Exchange**" | "…primary official weather measurement station(s) for that location." |
| Report used (the registry's `common_determination` basis) | "Only the first official non-preliminary report … will be used for resolution. Revisions after the Expiration Date are not included in the Payout Criterion." | "… will be used for resolution **unless otherwise explicitly specified by the Exchange**. Revisions that the Exchange determines, in its sole discretion, do not remedy a material error are not included …" |
| Material error | (absent) | "If the Exchange determines, in its sole discretion, that the initial non-preliminary publication contains a material error, it **may delay expiration** until the earlier of (i) publication of revised data or (ii) the Expiration Date … If no reliable data is available by the Expiration Date, all markets will resolve to the last fair price…" |
| Operators, "between" inclusive, full precision, no-data → last fair price | as registered | **unchanged** |

**When the amendments took effect.**
- The posted filings state no effective date.
- A Reg. 40.6(a) self-certification may take effect 10 business days after filing, so both had taken effect by about 2026-09-17.
- The live market rules show the Exchange applying them.
- Every `structural_arb` validation run (2026-09-27) therefore ran under Amendment 2 while crediting the superseded PDF.

## 4. Do any previous structural conclusions change?

**Records whose label depended on the stale entry.**
- 47 local validation records hold `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE`, all `R1_SHORT` on weather families:

  | run | config | records |
  |---|---|---|
  | audit_smoke | `2026-09-27.5-audit` | 1 |
  | validation_run1 | `.2` | 3 |
  | validation_run2 | `.2` | 11 |
  | validation_run3 | `.3` | 2 |
  | validation_run4 | `.4` | 30 |

  The series are KXHIGHPHIL, KXHIGHDEN, KXHIGHLAX, KXHIGHTDAL and KXHIGHCHI.
- That status is reachable only through `_terms_ok`, which requires `TERMS_VERIFIED`.
- **Their terms provenance is invalid.** Under a fail-closed policy all 47 read `CANDIDATE_TERMS_UNVERIFIED` until GLOBALTEMPERATURE is re-verified against Amendment 2.
- No BTC/ETH record reached a lock-like status in any run.

**Top-level conclusions.**
- **No `RULE_DEFINED_LOCK` was ever emitted** by any run.
- The structural conclusion therefore stands: no executable rule-defined lock was found, and the scanner is READY_TO_FREEZE.
- All 47 records already failed an execution gate, so no "executable" claim is withdrawn.

**Does the lock mathematics survive under Amendment 2?**
- The facts the payoff model uses are unchanged:
  - inclusive "between";
  - real-valued full precision;
  - no data → discretionary last fair price.
- So `R1_SHORT` payoff L = N − 1 still holds in every non-discretionary state.
- **One substantive question must be settled at re-verification; this audit does not settle it.**
  - The amendment adds a discretionary channel: an Exchange-specified report, and a material-error expiration delay "until publication of revised data".
  - Contracts in a family can expire at different instants: GLOBALTEMPERATURE keeps the Rule 7.2 early-expiration clause.
  - So one contract could settle on the initial publication while another, still open, is held and settles on a revised one.
  - The registry standard admits discretionary states as residual risk. But the reasoning that removed INX (no forced common determination instant) applies in part here.
  - A reviewer must decide whether GLOBALTEMPERATURE stays registrable with a revised `common_determination`, or is removed as INX was.

**Stale documentation** (noted only; not edited, per instructions):
- `sarb/terms.py`, GLOBALTEMPERATURE entry: its `common_determination` quotes a sentence that no longer exists verbatim, and the citations omit the Source Agency.
- `DESIGN.md` A9 and line 408 cite `contract_terms/GLOBALTEMPERATURE.pdf` as the verified source.
- `DESIGN.md` line 175 still says "(or MECNET for categorical R1-short/pairs)", although `_terms_ok` and DESIGN.md line 367 record that this exemption was removed.

**Not caused by this defect.** 362 further `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE` records are MECNET `R1_EXCLUSIVE_PAIR` on unregistered series, from configs `.2`–`.4`. They come from the MECNET terms exemption that commit `c8dd6b8` already removed. The post-audit smoke run (`.5-audit`) shows none.

## 5. Why the architecture failed (root causes)

1. **Wrong object of verification.** The registry pins the bytes of a *convenience copy* (the served PDF) rather than the *controlling legal document* (the latest effective filing). Kalshi can amend a contract without touching that copy.
2. **No discovery of amendments.** Nothing enumerates filings, so a new filing cannot invalidate anything.
3. **No consistency check against operative market rules.** `rules_primary` and `rules_secondary` name "The Weather Company" while the registry's source basis is NWS. The collector's fingerprint gate (`metadata_matches_template`) only detects *changes* after build, not *contradictions* with the registry.
4. **Fail-open default.** An unchanged hash is treated as positive evidence that nothing changed.

## 6. Proposed fail-closed, amendment-aware verification design (not implemented)

**Principle:** `TERMS_VERIFIED` must mean that a human verified the **currently controlling filed terms**, that nothing newer or pending exists, and that the served copy and the live market rules do not contradict them. Any doubt yields a non-verified status.

### 6.1 Registry entry (keyed to the controlling filing)

The key is `template`. Each entry holds:

| field | contents |
|---|---|
| `controlling_filing_key`, `controlling_filing_sha256` | e.g. `regulatory/notices/GLOBALTEMPERATURE Amendment 2 (for posting).pdf` |
| `filing_dated`, `filing_posted` | date on the filing, and the S3 LastModified |
| `terms_text_sha256` | hash of the normalised Appendix A text: format characters stripped, whitespace-insensitive |
| `known_filings` | the complete ordered list of filing keys and their sha256 at review time |
| `served_url`, `served_sha256_at_review`, `served_equivalent` | whether the served copy was judged text-equivalent at review |
| `rules_markers` | phrases that must appear in live `rules_primary`/`rules_secondary` (e.g. the Source Agency), and phrases that must not |
| model facts | `between_inclusive`, `no_data`, `common_determination`, citations quoting the **controlling** text |
| review record | `reviewer`, `reviewed_utc` |

### 6.2 Resolution at build, and again at P3

Each check below is evaluated in order, and the first that fails determines the status:

| # | check | status on failure (none is verified) |
|---|---|---|
| 1 | **Complete fresh listing.** List the regulatory bucket for the template with prefix queries, paginated to completion:<br>• `regulatory/product-certifications/<T>`<br>• `regulatory/notices/<T>`<br>• `contract_terms/<T>`<br>Keep only keys for exactly `<T>` (BTC ≠ BTCMINMAX).<br>Any HTTP error, parse error, truncation or listing older than `MAX_LISTING_AGE` (e.g. 6 h; P3 may reuse a listing from the same run) fails. | `TERMS_FILINGS_UNAVAILABLE` |
| 2 | **Unknown documents.** A key for `<T>` that is neither in `known_filings` nor matches a known filing pattern (certification, "Amendment n", "for posting") fails. | `TERMS_FILINGS_UNRECOGNISED` |
| 3 | **Superseded.** Any filing newer than `controlling_filing_key`, or a controlling-filing sha different from the registry's, fails. This is what would have caught GLOBALTEMPERATURE on 2026-08-18. | `TERMS_SUPERSEDED` |
| 4 | **Pending.** If the controlling filing is less than 10 business days old and states no effective date, either version may be in force. | `TERMS_AMENDMENT_PENDING` |
| 5 | **Served copy.** Fetch the served PDF; if its sha equals `served_sha256_at_review`, accept. Otherwise extract its normalised text and require that every sentence also appears in the controlling Appendix A (the BTC/ETH case passes). Any substantive divergence fails. | `TERMS_SOURCE_CONFLICT` |
| 6 | **Live rules.** For every market in the family, the fresh `rules_primary`/`rules_secondary` must contain every required marker and no forbidden marker. For example, a registry claiming NWS while rules say "The Weather Company" fails. | `TERMS_RULES_CONFLICT` |
| 7 | Otherwise. | `TERMS_VERIFIED` |

- **Never auto-promote.** Any non-verified status needs a human re-review that writes a new registry entry (new controlling filing and hashes). Code may *demote*, never *promote*.
- **Provenance in every record.**
  - Every candidate record carries `controlling_filing_key`, `controlling_filing_sha256`, `listing_utc`, `served_sha256` and the rules fingerprint.
  - `reconstruct.py` and `report.py` re-run steps 1–3 against the filing history. A record made while a newer filing existed is relabelled `CANDIDATE_TERMS_UNVERIFIED (TERMS_SUPERSEDED_AT_SNAPSHOT)` retroactively.
  - Under this rule the 47 weather records above would be relabelled mechanically.
- **Scope of trust.** Filings posted to the public regulatory bucket are treated as the filing record, because `cftc.gov` is not reachable from this environment. That is a documented residual (see 6.4).

### 6.3 Tests to add with the implementation

Fixture-based; no network.

1. Served hash matches, but a newer amendment exists → `TERMS_SUPERSEDED` (the GLOBALTEMPERATURE regression).
2. Listing raises, is truncated or is stale → `TERMS_FILINGS_UNAVAILABLE`.
3. A controlling filing 3 business days old with no effective date → `TERMS_AMENDMENT_PENDING`.
4. A BTC/ETH-style case: served PDF modified before the amendment was posted, text contained in the filing → `TERMS_VERIFIED`.
5. Served text contradicts the filing → `TERMS_SOURCE_CONFLICT`.
6. Live rules name a source agency the registry doesn't list → `TERMS_RULES_CONFLICT`.
7. Prefix collisions (BTC vs BTCMINMAX; GLOBALTEMPERATURE vs GLOBALTEMPERATURESUSTAINED) are not counted.
8. An unrecognised key for the template → `TERMS_FILINGS_UNRECOGNISED`.
9. Retroactive relabel of a recorded candidate after a later filing appears.
10. Code paths may demote but never promote. A property test: no code path returns `TERMS_VERIFIED` without an exact registry match on the controlling filing sha.

### 6.4 Residual risks the design cannot remove

- **Filing record.** A filing absent from the bucket, or posted late, is invisible. Check 3 only knows what the bucket holds. The CFTC portal is authoritative but unreachable here.
- **Rule changes outside product filings.** Rulebook amendments, Exchange notices, or `rules_secondary` clarifications issued under "unless otherwise explicitly specified by the Exchange". Check 6 catches only markers someone thought to list.
- **Discretion inside the controlling text.** Market Outcome Review, last fair price, material-error delay. These are residual states for any registered template, as before.
- **Text-extraction fidelity.** The filing PDFs contain zero-width and bidi characters and drop inter-word spaces. Comparison must be whitespace-insensitive, which `terms_audit.py` implements. An extraction bug fails *closed* under check 5 only if divergence is the default on error.

## 7. Recommendation (no action taken)

Before any further `structural_arb` run is interpreted:
- treat GLOBALTEMPERATURE as `TERMS_SUPERSEDED`;
- relabel the 47 weather records `CANDIDATE_TERMS_UNVERIFIED`;
- re-verify BTC and ETH against their Amendment 2 filings. Their text is contained in the filings, so a re-review should only re-key them.

Implementing section 6 in `structural_arb` awaits explicit approval, as instructed.
