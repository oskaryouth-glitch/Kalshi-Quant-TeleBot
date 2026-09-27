# Settlement-equivalence review, 2026-09-27

Scope: the `CANDIDATE_TERMS_UNVERIFIED` families from validation run 4. No scanner threshold,
execution assumption, fee logic, candidate generation or gate was changed. **The terms
registry (`sarb/terms.py`) was NOT updated.** Neither family is verified.

## Evidence (this directory)

| File | SHA-256 | Source |
|---|---|---|
| contract_terms_AAAGAS.pdf | 337728c1…102c | https://assets.kalshi.com/contract_terms/AAAGAS.pdf (current terms, used by all 4 AAA series) |
| regulatory_product-certifications_AAAGAS.pdf | 736dcd0c…fc6 | CFTC 40.2 certification, 2023-09-13 (an **older** version, with different expiration rules) |
| contract_terms_CRYPTO.pdf | fde90b9c…c75c | https://assets.kalshi.com/contract_terms/CRYPTO.pdf (used by KXSOLD26 and KXSOL26500) |
| regulatory_product-certifications_CRYPTO.pdf | 4841dd60…f8a1 | CFTC certification of CRYPTO |
| api_snapshot_2026-09-27.json | 3707d915…1824 | GET /markets/{t}, /events/{e}, /series/{s} for every candidate leg |
| aaa_settlement_history_check.json | d2569a1e…8df | all settled KXAAAGASD/W and …NJ markets, compared per date |
| payoff_check_output.json | cf8272e0…69ae | `scripts/equivalence_check.py` (sarb.payoff checker) |

The Rulebook v1.29 is `../Kalshi_DCM_Rulebook_v1.29.pdf` (Rules 6.3, 7.1, 7.2).

## A. AAA gas: KXAAAGASD vs KXAAAGASW, and KXAAAGASDNJ vs KXAAAGASWNJ

Candidates:
* `KXAAAGASD-26SEP28-4.4650` YES / `KXAAAGASW-26SEP28-4.4660` NO
* `KXAAAGASW-26SEP28-4.4840` YES / `KXAAAGASD-26SEP28-4.4850` NO
* `KXAAAGASDNJ-26SEP28-4.3950` YES / `KXAAAGASWNJ-26SEP28-4.4000` NO
* `KXAAAGASDNJ-26SEP28-4.4000` YES / `KXAAAGASWNJ-26SEP28-4.4000` NO (duplicate)

1. **Underlying.** AAAGAS terms: "the average gas price for regular gas in `<area>` on
   `<date>`". Both legs of each pair give the same area (US, or New Jersey) and the same date
   (Sep 28, 2026) in `rules_primary`. Series settlement-source URLs are identical within each
   pair: `gasprices.aaa.com/` for US, `?state=NJ` for NJ. **Same.**
2. **Settlement source.** "The Source Agency is AAA", in both. **Same.**
3. **Observation / reference period.** "on `<date>`", Sep 28, 2026, in both. **Same.**
4. **Timezone and cutoff.**
   * Current terms: "Expiration time … shall be 10:15 AM, 11:00 AM, **or** 3:00 PM ET".
   * "The latest Expiration Date … one month after the scheduled data release … If the data is
     released … expiration will be moved to an earlier date and time in accordance with Rule 7.2."
   * The terms do **not** assign one of the three times to a series or market. The Exchange
     sets and moves expiration per Contract under Rule 7.2(b)/(c).
   * API metadata is identical for the paired markets: `close_time` 2026-09-28T03:59Z,
     `expected_expiration_time` 14:00Z, `latest_expiration_time` 2026-10-05T14:00Z. But 14:00Z is
     10:00 AM EDT, which is none of the three permitted times, so the metadata cannot pin the
     binding expiration time.
   * **The binding terms do not force a common expiration time.**
5. **Revisions.** "Revisions to the Underlying made after Expiration will not be accounted
   for", and the Expiration Value is "as documented by the Source Agency on the Expiration
   Date at the Expiration time". If the two markets expire at different permitted times, an AAA
   revision between them gives **different Expiration Values**.
6. **Rounding / precision.** None stated. Settled expiration values have 2, 3 and 4 decimals
   (e.g. 4.4786, 4.3163), so values strictly between the strikes (e.g. 4.4655) are possible
   states.
7. **Strictness.** Market rules say "strictly greater than $X" for every leg. All 2,281 settled
   AAA markets examined have a `result` consistent with strict `>` on their `expiration_value`.
   **Boundary enumeration** (YES `>4.465`, NO `>4.466`), assuming one common X:

   | X | YES_D pays | NO_W pays | payoff |
   |---|---|---|---|
   | X < 4.465 | 0 | 1 | 1 |
   | X = 4.465 | 0 (not strictly greater) | 1 | 1 |
   | 4.465 < X < 4.466 | 1 | 1 | 2 |
   | X = 4.466 | 1 | 1 (4.466 is not > 4.466) | 2 |
   | X > 4.466 | 1 | 0 | 1 |

   The 4.484/4.485 and 4.395/4.400 pairs give the same table. For the 4.400/4.400 duplicate,
   X ≤ 4.4 pays 0+1 and X > 4.4 pays 1+0, so the payoff is always 1.
8. **Missing data / fallback / scalar.**
   * Current terms: "If no data is available on the Expiration Date at the Expiration time,
     then the market will resolve based on the last available day's data." This is determinate,
     but it is evaluated **at each Contract's own expiration**. With different expiration times,
     one market can use Sep 27's value while the other uses Sep 28's.
   * "If an Expiration Value cannot be determined … Kalshi has the right to determine payouts
     pursuant to Rule 6.3(b)." This is discretionary (Rulebook 6.3(c)/7.1), a residual for
     every candidate.
   * **Discrepancy:** the terms cite Rules "6.3(d)"/"6.3(b)", which don't match Rulebook
     v1.29's numbering (discretionary determination is 6.3(c)).
9. **Cancellation / void.** There is no void provision beyond the Rulebook's (Rule 5.11 trade
   cancellation; Rule 7.2 modifications). Both apply to each Contract separately.
10. **Series and event differences.**
    * The D series is "daily" and the W series "weekly". They have different event objects and
      open times (W opened Sep 25, D opened Sep 27), but identical rules text apart from the
      strike, the same terms PDF and identical timing metadata.
    * **The markets are determined separately:** settlement timestamps differed on 13 of 14
      historical paired dates (e.g. NJ Sep 14: 08:20Z vs 13:12Z).
    * Historical expiration values were **numerically identical on all 14 paired dates**. That
      is evidence, not a binding guarantee.

**Payoff checker.**
* With one common X, including the "last available day" fallback (another common X), the
  **minimum payoff is 1 in every state**.
* With the states the terms permit — each market's own Expiration Value, from its own permitted
  expiration time, revision state and fallback — the **minimum payoff is 0**. For example:
  X_D ≤ 4.465 (Sep 27 fallback, or pre-revision) and X_W > 4.466.

**Result: `TERMS_EQUIVALENCE_UNRESOLVED`** (US and NJ, all four pairs). Underlying, source,
date, area, strictness and fallback rule are identical. But the binding terms let the Exchange
determine each Contract at a different permitted Expiration Date/Time, and they fix the value
at that time (revisions after it are ignored; the no-data fallback applies there). So a state
in which the two legs settle on different values is permitted, and the lock fails in it. The
equivalence is not false by rule (the values are equal whenever determined together, and
historically were), but it is not established by the binding terms. **Not eligible for
`RULE_DEFINED_LOCK`.**

## B. Solana: KXSOLD26 vs KXSOL26500

Candidate: `KXSOLD26-27JAN0100-T449.99` YES (`>449.99`) / `KXSOL26500-27JAN0100-T500` NO (`>500`).

1. **Underlying.** CRYPTO terms: "the spot price of one `<cryptocurrency>` in U.S. dollars at
   `<time>`, according to a simple average of the CF `<cryptocurrency>` `<index>` for the 60
   seconds prior to `<time>`". Both `rules_primary` read "simple average of the sixty seconds of
   CF Benchmarks' SOLUSD_RTI … at 12 AM EST on Jan 1, 2027". **Same.**
2. **Source.** "The Source Agency is CF Benchmarks", in both, with the same series settlement
   source. **Same.**
3. **Observation period.** 60 s before 00:00 EST, Jan 1 2027 (= 05:00Z; strike_date
   2027-01-01T05:00:00Z in both). **Same.**
4. **Timezone and cutoff.**
   * EST is explicit in both rules.
   * "Expiration time … shall be 10:00 AM ET": **one fixed time** (stronger than AAA).
   * Expiration Date: "latest … one week after `<date>`. If an event described in the Payout
     Criterion occurs, expiration will be moved to an earlier date and time in accordance with
     Rule 7.2". This is set per Contract, so a common Expiration *Date* is not forced.
   * API metadata is identical for both (close 05:00Z, expected expiration 05:05Z, latest
     expiration 2027-01-08T05:00Z).
5. **Revisions.** "Revisions to the Underlying made after Expiration will not be accounted
   for". If the Contracts expire on different dates, a CF Benchmarks RTI revision between them
   yields different values.
6. **Precision.** None stated for the average. The terms' "Minimum Tick" differs between
   versions ($0.001 in the current terms, $0.01 in the certification); that is irrelevant to
   settlement.
7. **Strictness.** The terms define it: "'Above X' means strictly greater than X". Both rules
   say "above". **Boundary enumeration** (YES `>449.99`, NO `>500`), assuming one common X:

   | X | YES pays | NO pays | payoff |
   |---|---|---|---|
   | X < 449.99 | 0 | 1 | 1 |
   | X = 449.99 | 0 | 1 | 1 |
   | 449.99 < X < 500 | 1 | 1 | 2 |
   | X = 500 | 1 | 1 (500 is not > 500) | 2 |
   | X > 500 | 1 | 0 | 1 |
   | no data, both | 0 (No) | 1 | 1 |

8. **Missing data / fallback.**
   * "If no data is available **or incomplete** on the Expiration Date at the Expiration Time,
     then **affected strikes** resolve to No."
   * The wording is per strike ("affected strikes"), not "all strikes" (compare BTC.pdf: "the
     market resolves to No"). So a state where the YES leg's strike resolves No while the NO
     leg's strike settles on X > 500 is not excluded by the terms. That state pays 0.
   * Discretionary determination ("Rule 6.3(b)", mis-numbered as in AAA) is a residual.
9. **Cancellation / void.** Rulebook 5.11 and 7.2 only, per Contract.
10. **Series differences.** KXSOLD26 is "annual" and KXSOL26500 "one_off", with different
    events but the same terms PDF, index, time and strictness. Neither series has settled yet,
    so there is no history. The CRYPTO-terms hourly analogues (KXSOLD vs KXSOLE) settled on
    identical values in 4 of 4 groups checked (evidence only).

**Payoff checker.** One common X plus the both-no-data state gives **a minimum of 1**.
Permitted divergent states (separate Expiration Dates with a revision between them, or a
per-strike "affected → No") give **a minimum of 0**. For example: YES leg resolves No (affected
or X_yes ≤ 449.99) while X_no > 500.

**Result: `TERMS_EQUIVALENCE_UNRESOLVED`.** This is closer to equivalence than AAA: the
underlying, index, window, timezone, strictness and expiration time are all identical and
fixed. But (i) the Expiration Date is set per Contract under Rule 7.2 while post-expiration
revisions are ignored, and (ii) the no-data clause applies to "affected strikes" individually.
Both permit a divergent state in which the lock fails. **Not eligible for `RULE_DEFINED_LOCK`.**

## Side finding for the terms registry (no change made)

If `CRYPTO.pdf` is ever added to the registry, its no-data rule is **per strike** ("affected
strikes resolve to No"), unlike BTC.pdf/ETH.pdf ("the market resolves to No"). The payoff model
would then need per-market No states, not only a common ALL_NO state.
