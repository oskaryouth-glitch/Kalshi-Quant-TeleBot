# PRICE TEST 1: results (falsification tests, not strategy backtests)

- **Date:** 2026-09-29.
- **Pre-registration:** `PREREG.md`, commit `88e3bca`, pushed 2026-09-29 03:54 UTC, before any candlestick, trade or order book was retrieved.
- **Decisions:** every decision below applies the frozen criterion exactly. Numbers labelled *reported only* are descriptive and decide nothing.
- **Constraints kept:** no orders, no credentials, no collector; H038/H039 not touched; `structural_arb` not modified.

## Summary

| mechanism | frozen decision | one line |
|---|---|---|
| **M8-T20** | **KILLED before price testing** | The 50¢ state adds no constraint beyond R1/R4 complementarity (PREREG §M8). No price data was retrieved. |
| **M2-NO** | **KILL** (K2) | After NO became certain, the typical market offered only the price-grid floor. The median over markets of the time-median YES bid was $0.00. Executed value existed: $17.36k net 5.11-safe. It was almost entirely 1¢ floor fills: 99¢ NO bids filled by holders exiting over about 11 days, plus stale YES bids in three NFL markets on one evening. |
| **M5-GOLF** | *see §M5* | |
| **M6-REWARDS** | **SURVIVE (capital-compatible)**, weak by construction | 52/60 sampled programs (87%, kill threshold 10%) let a small participant earn ≥ $1 per Time Period with C\* ≤ $200 (median C\* $19). It works only because other providers already meet the Target on both sides. Where they don't, C\* ≈ $1,750–1,790, as derived. Profitability and adverse selection were **not** tested. |

## Changes after the freeze (all disclosed)

1. **Data-access fix in `pt1_common.get()`.**
   - The first M6 attempt (about 03:56 UTC) died on `http.client.RemoteDisconnected` while fetching event objects. It wrote no output and no result was seen.
   - `get()` now also retries `ConnectionError` and `http.client.HTTPException`: one import plus one `except` tuple.
   - This changes no definition, threshold, sample or assumption. The sha256 of `pt1_common.py` moved from `562377…` to `87827e…`.
   - `m2_no.py`, `m5_golf.py` and `m6_rewards.py` are byte-identical to the freeze (hashes verified).
2. **M6 re-sampling.** The aborted attempt may have fetched some order books before dying. They were never saved or viewed. M6 was rerun from scratch at 03:58 UTC with the frozen seed against the then-live program set, so the drawn sample is the one the frozen procedure produces at 03:58, not at 03:56.
3. **M2 ran on the pre-fix module** (started before the fix). It completed without error.
4. **Golf coverage file.**
   - `inputs/golf_coverage.csv` was filled after the freeze, as PREREG requires: web search, because pgatour.com and similar hosts are blocked here.
   - It was filled **before** any golf price was read.
   - Where two sources disagreed on the field size (TECHO26: 133 vs 135; WYC26: 144 vs 147), or no source was found (THCCBN26), the size was left blank. The event is therefore invalid.
   - This strict convention is the literal PREREG rule ("a missing or unsourced value … invalidates the observation"). It was written down before prices were seen.
5. **Reported-only additions written after the runs:**
   - `m2_detail_reported.py`: price distribution and fill-to-close time of post-certainty NBA trades;
   - `tables.py`: per-market CSVs from the frozen outputs.

   Neither feeds any decision.

---

## M8-T20: KILLED before price testing

See PREREG §M8.
- YES_A = (1, 0, ½) and YES_B = (0, 1, ½) sum to 1 in every state, so the only no-arbitrage restriction is p_A + p_B = 1 (R1/R4).
- The tie/no-result state probability π_X ∈ [0, 2·min(p_A, p_B)] is not identified.
- No other contract on the match pays a rule-defined amount in that state.
- No predictive cricket model was built. No prices were retrieved.

---

## M2-NO: already-decided NO markets

**Universe:** 173 market–certainty rows (primary variant), 0 invalid.
- **KXNBAWINS 2025-26:** 126 markets. Every team had exactly 82 decided games. The 3 fair-price-settled postponed games were excluded as frozen.
- **KXNFLWINS 2026-27:** 47 markets.

**Were all rows valid, and did any market close before certainty?**
- Every row settled NO. No market was NO-certain by formula but settled YES.
- **All 173 were still open after t\***, so certainty preceded closure in every case.

**Remaining trading duration** (close − t\*):

| league | p10 | median | p90 |
|---|---|---|---|
| NBA | 229 h | 1,024 h | 2,270 h |
| NFL | 0.9 h | 1.6 h | 2.7 h |

WINTOTAL early-closes NO markets. The exception is KXNFLWINS-27LAR-17, which stayed open 258 h after certainty.

**Executable NO ask after t\*** (NO ask = 1 − YES bid, hourly candle closes):

| | NBA (126) | NFL (47) |
|---|---|---|
| first hourly YES bid after t\* = $0 (no NO for sale below $1) | 120 | 45 (2 without candles) |
| … = $0.01 / ≥ $0.02 | 4 / 2 | 0 / 0 |
| per-market time-median YES bid | $0 in **all 126** | $0 in all 45 |
| maximum hourly YES bid over the whole window | 0: 89; 1¢: 33; 2¢: 3; 3¢: 1 | 0 in all 45 |
| fraction of hours with YES bid ≥ 2¢ (mean) | 0.16% | 0% |

**Available size** (executed contracts after t\*, a lower bound; historical depth is not published):

| | NBA | NFL |
|---|---|---|
| taker bought NO (lifted a YES bid): contracts / gross | 12,515 / $125.75 | 16,468 / $3,021.10 |
| taker bought YES (a resting NO bid captured): contracts / gross | 1,268,309 / $14,397.12 | 0 |
| 5.11-unsafe (yes > $0.20): contracts / gross | 38 / $8.69 | 200 / $50.00 |
| fees on safe captures (direct; quadratic, M = 1, no maker fee) | $8.72 | $172.48 |
| **net 5.11-safe capture, direct** | **$14,514.15** | **$2,848.61** |

All markets combined: **$17,362.77 direct** ($17,362.23 non-direct).

**Where the value came from** (*reported only*, `outputs/m2_detail_reported.txt`):
- **NBA.**
  - 92% of post-certainty contracts (1,165,726) traded at YES = 1¢ with the taker buying YES. In Kalshi's unified book that is a NO holder **selling NO at 99¢**, typically to free capital before settlement. It is filled by a resting NO bid at 99¢.
  - The capital-weighted mean time from fill to market close was **11.0 days**. So the capture is 1¢ on 99¢ of capital for about 11 days: a time-value/liquidity-provision trade at the tick floor, not a mispricing.
  - The queue at 99¢ is unobservable.
  - Per market: median $26, p90 $305, maximum $1,311 (KXNBAWINS-LAL-25-T60).
- **NFL.**
  - $2,455.89 came from KXNFLWINS-27NO-16 and $565.10 from KXNFLWINS-27DAL-16.
  - Resting YES bids (equivalently, stale sell-NO orders) at 19¢ and 16¢ for 12,926 and 3,532 contracts were lifted 34–57 minutes after the deciding games closed (00:17–00:40 UTC on 2026-09-28).
  - TB-15 traded 200 contracts at 25¢, which is outside the 5.11 band and cancellable on request.
  - All of it happened on one evening, in three markets.
  - These bids never appear in an hourly candle close. They lived for well under an hour.

**Rule 5.11.**
- 99.7% of post-certainty gross ($17,543.97 of $17,602.66) traded at YES ≤ $0.20. That is inside the no-cancellation band around fair value 0, so it is not reviewable.
- The remaining $58.69 was reviewable on the counterparty's request within 15 minutes.

**Settle-time variant** (reported only). Identical totals: no post-certainty trade fell between a deciding game's close and its settlement.

**Frozen decision:**
- **K1** (net safe capture < $250): **false** ($17,362.77).
- **K2** (median per-market time-median YES bid ≤ $0.01): **true** ($0.00).
- **Decision: KILL.**

**Primary question: was there executable value after certainty became public?**
- **As a taker in the typical market: no.** There was no YES bid, so no NO was offered below $1.00 for most of every window. NBA taker-side capture after certainty was $125.75 over 126 markets and a whole season.
- **What existed was of two kinds:**
  - the 1¢ floor, harvested by resting 99¢ NO bids against exiting holders (queue unknown; capital tied up until close);
  - rare stale orders, taken by others within the hour.
- The price grid (floor) and early closure eliminated the rest.
- **Limitation, disclosed.** K2 is measured on hourly candle closes, so it cannot see bids that live less than an hour. That is exactly how the NFL stale bids appeared. Those bids are captured by K1's trade-level sum, and K1 did not fire.

**Per-market detail:** `outputs/m2_per_market.csv` has one row per market. Columns: t\*, deciding game, close, remaining hours, first NO ask, time-median and maximum YES bid, contracts by role, 5.11 split, gross, fees, and net direct/non-direct.

---

## M5-GOLF: top-N "including ties"

*(pending: filled in from `outputs/m5_summary.txt`)*

---

## M6-REWARDS: capital compatibility for a very small account

**Filed formula and units confirmed.**
- The Liquidity Incentive Program as modified on 2026-07-30 applies the Time Period Reward per Time Period (≤ 31 days). The $1.00 payment floor applies to each Time Period's payout.
- `period_reward` is the "total reward for the period in centi-cents" (API schema).
- No sampled program set `max_reward_per_account`.
- Order books were fetched at full depth (the API default, `depth = 0`, returns all levels).

**Sample (first pass, 03:58–03:59 UTC).**
- 4,881 live liquidity programs: 2,986 with zero 24-hour volume and 1,895 with nonzero volume.
- 30 drawn from each stratum with seed 20260929.
- Target 1,000 in 58 programs and 2,500 in 2. Time Period Reward $100–$500 over 1–14 days (median 7). 3 programs were in maker-fee series.

**Analytic minimum, confirmed empirically.**
- **Lone provider.** In the 7/60 books where other providers' resting size is below Target on one side (an empty side), a small participant must post the Target itself.
  - x_min = 1,000 contracts;
  - **C\* = $1,750–$1,790**, matching the pre-registered 1.35T–1.8T;
  - worst-fill loss L\* ≈ $850–$890.

  That is fundamentally incompatible with a $1,000 account. The formula-only 1¢/1¢ configuration would cost $30 ($75 at T = 2,500). It is excluded as frozen.
- **Contested books.** 53/60 books already had ≥ Target on both sides, so a small order joining at the best bids takes a pro-rata share of the per-side score. The frozen configuration is: join the best bids if the spread ≤ 10¢ (38 programs); otherwise improve to a 10¢ market (22).

| (first pass) | compatible (C\* ≤ $200 and payout ≥ $1) | median C\* |
|---|---|---|
| zero-volume stratum | 26/30 | $20.84 |
| nonzero-volume stratum | 26/30 | $22.06 |
| **all** | **52/60 = 87%** | **$21.39** |

- **Compatible programs:**

  | | p10 | p50 | p90 |
  |---|---|---|---|
  | x_min (contracts per side) | 5 | 12 | 51 |
  | C\* | $6.85 | $19.32 | $90.71 |
  | L\* (worst plausible filled inventory) | — | $8.55 | $42.21 (p90) |

- **Incompatible (8):**
  - the 7 lone-provider books (C\* ≈ $1,790);
  - KXAAL-26OCTPLF-88.0 (C\* $244: 124 contracts per side needed against 13.8k/18.6k competing depth).
- *Reported only:* payout if the whole $200 per-market budget is posted is median **$9.71 per Time Period** (p10 $2.04, p90 $33.54), or $1.22/day median. This assumes full uptime and static competition, and ignores fills, adverse selection and competitor response.

**Frozen decision:** compatible fraction 87% ≥ 10% → **SURVIVE (capital-compatible)**.

**What this does and does not say.**
- It says the **capital requirement** does not kill M6 for a very small account, **provided the book already has other providers at Target on both sides**.
- A small participant cannot create an eligible book, but can free-ride on one.
- It says nothing about profitability. The frozen configuration rests at the **best bid**, so fills are likely, and zero 24-hour volume was not treated as zero fill risk. The adverse selection of those fills is the untested question. So are the stability of competitors' depth, uptime, and the ≥ $1 floor under dynamic competition.
- In the join-best configuration, one side is often priced near certainty (e.g. a NO bid at 98¢). A fill there risks up to 98¢ per contract to earn a small reward share.
- **Second pass** (+60 min, 04:59–05:00 UTC, the same 60 programs, reported only): **the small-capital opportunities persisted.**
  - Compatible: 52/60 = 87% again, and the **same 52 programs**, with 0 lost and 0 gained. Competing depth changed in 49 of them.
  - Median C\* across all 60 was $25.65 (first pass $21.39).
  - Among compatible programs: x_min p10/p50/p90 = 5/14/51 contracts; C\* $8.70/$23.66/$90.71; L\* median $10.32 (p90 $45.12).
  - The per-program C\* ratio second/first was median 1.00 (p10 0.79, p90 1.57). 39/60 kept identical quotes.
  - The 8 incompatible programs were the same 7 lone-provider books plus KXAAL.
  - Payout at the $200 budget: median $8.51 per period.

**Per-program detail:** `outputs/m6_per_program_first.csv` and `outputs/m6_per_program_second.csv`.

**Next step (designed, not started):** `../m6_paper/DESIGN.md` tests net economics with fills, at K = $30/$100/$200.

---

## Files

| file | contents |
|---|---|
| `outputs/m2_universe.json`, `m2_results.json`, `m2_summary.txt` | M2 frozen run (run logs are git-ignored; the summaries hold their content) |
| `outputs/m2_per_market.csv`, `m2_detail_reported.txt` | M2 reported-only tables |
| `outputs/m5_results.json`, `m5_summary.txt` | M5 frozen run |
| `outputs/m6_first.json`, `m6_summary_first.txt`, `m6_per_program_first.csv` | M6 decision pass |
| `outputs/m6_second.json`, `m6_summary_second.txt`, `m6_per_program_second.csv` | M6 stability pass (reported only) |
| `../TERMS_AUDIT.md` | separate structural terms-verification audit |
