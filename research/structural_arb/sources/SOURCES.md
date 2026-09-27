# Official sources used by the audit

Every fee or settlement assumption in `sarb/` must cite a row in this file. A fact that no row
below establishes is **UNRESOLVED**. It is not assumed.

## Files

| File | SHA-256 | Provenance | Effective / retrieved |
|---|---|---|---|
| `kalshi-fee-schedule_2026-07-07.pdf` | `c326a69f596a11e8f8be2620402d39a8d4823920c21cc97c93a114d862699601` | Uploaded by the project owner on 2026-09-27 as the official PDF at `https://kalshi.com/docs/kalshi-fee-schedule.pdf`. It could not be fetched independently, because kalshi.com serves a Vercel bot checkpoint (HTTP 429) to automated clients. PDF title: "Fee Schedule for July 2026 - 7.7.26 Update". 12 pages, rendered by Google Docs. | Every page says "Last updated and effective: July 7, 2026" |
| `docs_fee_rounding_2026-09-27.md` | `7591cf0fb277eaf8fac8aedaf1645e58b61dacb22b5fed20ba7d8ea9f76ffa22` | `https://docs.kalshi.com/getting_started/fee_rounding.md` | retrieved 2026-09-27 |
| `api_series_fee_changes_2026-09-27.json` | `8558cf2d877f4193d48d5ed4037c760c490d543592535c007b77a6d2f213e810` | `GET https://api.elections.kalshi.com/trade-api/v2/series/fee_changes?show_historical=true` | retrieved 2026-09-27. 149 changes, 2025-10-04 → 2026-09-23. None scheduled in the future. |

## What the fee schedule PDF establishes (event contracts)

* **Taker:** `fees = round up(M × 0.07 × C × P × (1−P))`, where M is the per-contract multiplier
  and defaults to 1.
* **Maker:** `fees = round up(M × 0.0175 × C × P × (1−P))`, where M defaults to **0**. Maker fees
  are charged only when a resting order executes. Cancelling costs nothing.
* **The PDF's definition of "round up":** "rounds up such that the fee + positionCost is rounded
  to a centicent".
* **No settlement fee.** No membership fee.
* **FCM customers** "may be charged fees by their Futures Commission Merchant that vary from the
  above fee schedule". Those fees are outside this schedule and unknown to us.
* **Non-standard multiplier table** (maker, taker). For example, `KXMVE` combos (excluding
  uncorrelated NFL) have maker 2 and taker 1, confirmed from the rendered page 8. Several series
  have 0/0.

## Verification findings

1. **The PDF's own example table follows whole-cent rounding, not centicent rounding.**
   * I recomputed all 42 table cells (21 prices × {1, 100} contracts) from the formula.
   * Rounding up to whole cents matches **42/42**. Rounding up to centicents mismatches 33/42.
     For example, the table charges $0.02 for 1 contract at $0.50, while the raw fee is $0.0175.
   * The docs Fee Rounding page explains the gap:
     * **Direct members** have balances aligned to $0.0001.
     * **Non-direct (FCM-cleared) members** have balances aligned to $0.01.
     * A per-order rounding-fee accumulator issues rebates as fills add up.
   * So the table shows the $0.01-precision case. The fee actually charged depends on the
     account's member class.
2. **The PDF's multiplier table is out of date.**
   * The API records **63 series fee changes after 2026-07-07**. Examples:
     * 18 MLB prop series moved to `quadratic` with M=0.5 on 2026-08-07.
     * `KXMLBGAME` moved to `quadratic_with_maker_fees` with M=0.5.
     * Four `KXMVE*` combo series moved to the new type `quadratic_with_combo_maker_fees` on
       2026-08-20.
     * `KXGDPYEAR` moved to M=0.
   * The PDF itself sends readers to kalshi.com/fee-schedule for changes.
   * **Rule:** coefficients and rounding come from the PDF plus the docs. M and fee_type come
     from the live API: `GET /series/{t}`, overridden by `GET /events/.../fee_changes` at the
     event level, as of the snapshot time. The PDF's multiplier table is never used when the
     API supplies a value.
3. **The PDF uses a different taker M for the same series than the API does.**
   * For example, the PDF lists KXMLBGAME at taker 1, while the API says 0.5 since 2026-08-07.
   * This is consistent with finding 2: the API is the more recent source.
4. **Maker fees are irrelevant to the detectors.** Every candidate leg is an immediate taker buy.
   Maker-fee types matter only to confirm that the taker formula is unchanged for the type.
5. **The `flat` fee type** ("Specific Trading Fees Table" per the API docs) does not appear in
   this PDF. Series using `flat` are **UNRESOLVED** and are rejected.
6. **`margin_market_maker_program_fees`** applies to perpetual futures (`*PERP` series). Those
   are out of scope.

## UNRESOLVED

* **Member class of the project owner's account (direct vs FCM-cleared).** It sets the balance
  precision ($0.0001 vs $0.01) and therefore the rounding fee. It is not exposed by any public
  endpoint. Until it is known, results are reported under **both** precisions, and nothing is
  labelled `ARBITRAGE` unless it holds under the class that applies.
* **FCM-imposed fees**, if the account is FCM-cleared.
