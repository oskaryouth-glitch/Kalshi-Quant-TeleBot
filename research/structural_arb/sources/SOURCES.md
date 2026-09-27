# Official sources used by the audit

Every fee or settlement assumption in `sarb/` must cite a row in this file. A fact that no row
below establishes is **UNRESOLVED**. It is not assumed.

## Files

| File | SHA-256 | Provenance | Effective / retrieved |
|---|---|---|---|
| `kalshi-fee-schedule_2026-07-07.pdf` | `c326a69f596a11e8f8be2620402d39a8d4823920c21cc97c93a114d862699601` | Uploaded by the project owner on 2026-09-27 as the official PDF at `https://kalshi.com/docs/kalshi-fee-schedule.pdf`. It could not be fetched independently, because kalshi.com serves a Vercel bot checkpoint (HTTP 429) to automated clients. PDF title: "Fee Schedule for July 2026 - 7.7.26 Update". 12 pages, rendered by Google Docs. | Every page says "Last updated and effective: July 7, 2026" |
| `docs/getting_started_fee_rounding.md` | `7591cf0fb277eaf8fac8aedaf1645e58b61dacb22b5fed20ba7d8ea9f76ffa22` | `https://docs.kalshi.com/getting_started/fee_rounding.md` | retrieved 2026-09-27 |
| `api_series_fee_changes_2026-09-27.json` | `8558cf2d877f4193d48d5ed4037c760c490d543592535c007b77a6d2f213e810` | `GET https://api.elections.kalshi.com/trade-api/v2/series/fee_changes?show_historical=true` | retrieved 2026-09-27. 149 changes, 2025-10-04 → 2026-09-23. None scheduled in the future. |

| `Kalshi_DCM_Rulebook_v1.29.pdf` | `3b6d4ffd5b32330d3466179d4cae610372d07511123c9976bc6cbb1b5185240b` | `https://assets.kalshi.com/regulatory/rulebook/Kalshi%20DCM%20Rulebook%20v.1.29.pdf`. The same bytes are on `kalshi-public-docs.s3.amazonaws.com`. Cited rules: 5.11, 6.3, 7.1, 7.2, and the "Market Outcome" definition. | v1.29, uploaded 2026-08-17 |
| `contract_terms/contract_terms_BTC.pdf` | `e7d857369971e75e9db14c5e2d91c29b94eb9a06e83e2acd9777991c4f2a0e2f` | `https://assets.kalshi.com/contract_terms/BTC.pdf` (KXBTC and KXBTCD) | retrieved 2026-09-27 |
| `contract_terms/contract_terms_ETH.pdf` | `ae079241099608c13c0c0ed31a6c91be174c6e61abe706dd76e8976ba682cc6d` | `https://assets.kalshi.com/contract_terms/ETH.pdf` (KXETH and KXETHD) | retrieved 2026-09-27 |
| `contract_terms/contract_terms_INX.pdf` | `9f79e958a612e605d37ec091cbbdc8d1748f4d2831ff338a808814eb75ea9d38` | `https://assets.kalshi.com/contract_terms/INX.pdf` (KXINX and KXINXU) | retrieved 2026-09-27 |
| `contract_terms/contract_terms_GLOBALTEMPERATURE.pdf` | `160281687cf9d3cd694c1c419522f3d53a8e1a6d4eddd40a7f5559c3a06211d0` | `https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf` (KXHIGH*) | retrieved 2026-09-27 |
| `contract_terms/contract_terms_GOLFFINISH.pdf` | `0aa490eb7fc077b38797e2e9b312214eb0d32ae8a8dbc3a597b908c11a36c9f1` | `https://assets.kalshi.com/contract_terms/GOLFFINISH.pdf`. Evidence for "withdrawal before tee-off → last fair price" and ties. | retrieved 2026-09-27 |
| `contract_terms/contract_terms_FOOTBALLSTATS.pdf` | `09d5c07d186bee6f632b78732a6c31bc378fd67fe80d4972117b56e7c4e1d64c` | `https://assets.kalshi.com/contract_terms/FOOTBALLSTATS.pdf` (KXMVECROSSCATEGORY combos). Evidence for "product of payouts, floored to the cent". | retrieved 2026-09-27 |
| `docs/*.md` | see `sha256sum sources/docs/*` | `https://docs.kalshi.com/...` pages and schema excerpts: settlement, lifecycle, order books, fixed point, multi-orderbooks (auth required), event fee changes, get-series/get-event/get-market field definitions | retrieved 2026-09-27 |

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

## Member class

The owner states the account was opened directly with Kalshi (not via a broker), so it is
treated as a **direct member** ($0.0001 balance precision). At the owner's request, research
results are also computed under non-direct $0.01 precision, and `ARBITRAGE` requires a positive
edge under that conservative case as well. No credentials are used.

## UNRESOLVED

See DESIGN.md §F.
