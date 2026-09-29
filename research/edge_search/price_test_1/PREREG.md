# PRICE TEST 1: pre-registration (frozen before any price or order-book retrieval)

- **Date:** 2026-09-29.
- **Scope:** M2-NO, M5-GOLF, M6-REWARDS and M8-T20 only.
- **These are falsification tests, not strategy backtests.**

**When the freeze happens.** This file and the scripts it names are committed and pushed *before* any candlestick, trade, order book or quote is retrieved for M2, M5 or M6.

**What was read before the freeze.** Only rules, filed terms, program parameters and settlement-state fields (`result`, `settlement_value_dollars`, `close_time`, `settlement_ts`).

**Changes after the freeze.** Only the following, each recorded in RESULTS.md:
- bug fixes that do not change a definition, threshold, sample or assumption;
- data-access fallbacks.

**Frozen code (sha256 at freeze)**

| file | sha256 |
|---|---|
| `pt1_common.py` | `562377307f8cebe0c65256455cdf713be686a3fdf0f558c1fadf35f8125f3cd4` |
| `m2_no.py` | `ea5ed8f4ffcaa37026b19fa5db90b8804ee7096f9a5f39ba0f1463356478804e` |
| `m5_golf.py` | `ccb868a9beaec1e9e360dd3b4b5e85e198fecda8cbff7a2d53923dea7119d563` |
| `m6_rewards.py` | `a67a6752ae0778e42ab96dcf0c62a27a305f75f4c9a4a5e241bf4c852c1c57ff` |

**Common rules.**
- Public, unauthenticated GETs only. No orders, no credentials.
- H038 and H039 are untouched. `structural_arb` is not modified (its fee constants are copied, not imported).
- No threshold, date, sport, league, price range, horizon or execution assumption may be changed after results are seen.

**Fees.**
- Model: taker fee = M × 0.07 × C × P(1−P); maker fee = M × 0.0175 × C × P(1−P), charged only in `quadratic_with_maker_fees` series.
- Rounding: ceil to 6 dp, then to the balance precision: $0.0001 for a direct member (primary, since the user is a direct member) and $0.01 for non-direct (reported).
- M comes from the series fee-change history at the relevant time, plus any event override.

---

## M8-T20: killed before any price test (no price data retrieved)

**Payoffs** (CRICKETMATCHWIN, served PDF 2026-09-10; the market rules agree). Two markets, A and B, over three states:

| state | YES_A | YES_B |
|---|---|---|
| A declared winner | 1 | 0 |
| B declared winner | 0 | 1 |
| X: tie with no super over; no result; abandoned; cancelled; pre-start forfeit; insufficient play | 0.5 | 0.5 |

**Pricing implication**
- The payoff vectors are YES_A = (1, 0, ½) and YES_B = (0, 1, ½), so YES_A + YES_B = (1, 1, 1) in every state.
- No arbitrage therefore requires p_A + p_B = 1. That is exactly the existing R1/R4 cover-pair (complementarity) constraint.
- Under state prices π: p_A = π_A + ½π_X and p_B = π_B + ½π_X. Any π_X ∈ [0, 2·min(p_A, p_B)] is consistent with the prices, so the prices do not identify π_X.
- The pair spans only a two-dimensional payoff space, so no portfolio of the two contracts isolates state X.
- **Other contracts on the same match** (CRICKETENTITYSTAT totals and sixes; CRICKETPROPS) settle every not-yet-achieved statistic at a discretionary "last fair price" on cancellation or abandonment. None of them pays a rule-defined amount in state X, so no cross-contract constraint involving X exists either.

**Decision.** The 50¢ state produces no constraint beyond R1/R4 complementarity. **M8 is KILLED before price testing.** Any remaining use would need a predictive model of q and of P(A | decided), which the brief forbids.

---

## M2-NO: already-decided NO markets

**Universe (fixed; built from settlement and game data only)**
- **KXNBAWINS**, 2025-26 regular season: "at least k wins", template ENTITYOUTCOME. Games come from KXNBAGAME events whose `close_time` UTC date is in [2025-10-21, 2026-04-13] and that settled yes/no.
  - The 3 game events that settled at a fair price (postponed, replayed later as separate events) are excluded.
  - Every team must have exactly 82 decided games, or all of that team's markets are invalid.
- **KXNFLWINS**, 2026-27 season, markets settled at test time. Template WINTOTAL. Games come from KXNFLGAME events with `close_time` date in [2026-09-09, 2026-09-30].
  - A 0.50/0.50 settlement is a tie (played, no win).
  - Any other fair-price settlement is excluded.
- **NCAAF is excluded ex ante**: its regular-season schedules cannot be verified from Kalshi data.

**NO-certainty time t\*.** With G = 82 (NBA) or 17 (NFL), W = wins and P = games played after each game, NO is certain for "at least k" at the first game where W + (G − P) < k.
- **t\*** is that game market's `close_time`: the earliest Kalshi record by which the result was known.
- A missing game can only *delay* t\*; the 82-game check prevents any extra game from advancing it.
- **Secondary variant, reported only:** t\* = that game market's `settlement_ts`.
- **Universe-only dry run** (settlement data only):
  - NBA: 126 NO-certain markets, all still open after t\*; window p10/p50/p90 = 229 / 1,024 / 2,295 h.
  - NFL: 47 NO-certain markets, window p50 = 2 h.
  - 0 invalid rows.

**Price data read after t\*** (and only after it), up to the market's close:
- hourly candlesticks (`yes_bid.close`, `yes_ask.close`);
- every public trade (`yes_price`, `count`, `taker_side`).

**Frozen metrics, per market**
- **Remaining trading duration:** `close_ts − t*`.
- **Executable NO ask after t\*:** NO ask = 1 − YES bid. Reported as:
  - the YES bid on the first hourly close after t\*;
  - the time-median of hourly YES-bid closes (a missing bid counts as 0);
  - the maximum;
  - the fraction of hours with a YES bid ≥ $0.02.
- **Available size.** Historical depth is not published, so the executed contracts after t\* are the observable lower bound.
- **Maximum gross capture (executed, after the fact):** Σ over trades after t\* of yes_price × count, split two ways:
  - taker bought NO: the taker captured yes_price;
  - taker bought YES: a resting NO bid captured yes_price.
- **Fees:** the taker fee on the NO buy at 1 − yes_price, and the maker fee where applicable.
- **Rule 5.11.** Once NO is certain, fair YES = 0. Trades at yes_price ≤ $0.20 are inside the no-cancellation band ("safe"). Trades above $0.20 are reviewable and cancellable if the counterparty asks within 15 minutes ("unsafe"). Net capture counts **safe trades only**.

**Primary question.** Did executable value exist after certainty became public? No optimal delay is searched: the only times used are t\* (primary) and the settle variant (reported).

**Kill criteria (primary variant)**

| code | condition |
|---|---|
| K1 | Σ over all markets of net 5.11-safe executed capture (taker plus maker, direct fees) < **$250** |
| K2 | Across markets, the median of the per-market time-median YES bid after t\* ≤ **$0.01** — the typical decided market offered only the price-grid floor |

**KILL if K1 or K2 holds; otherwise SURVIVE.**

---

## M5-GOLF: top-N "including ties" pricing and calibration

**Pricing statistic, derived before reading prices (GOLFFINISH).**
- S = Σ over the complete field of YES payouts = #{i : official position_i ≤ N} + Σ pre-tee-off fair prices.
- Under competition ranking the N-th best finisher has position ≤ N, so **S ≥ N** in every completed tournament. The excess S − N is caused by ties and is random.
- For a correctly priced field: E[S] ∈ [B − F_sell, A + F_buy], where at a fixed time t_s:
  - A = Σ ask_i (the cost of one YES of every player);
  - B = Σ bid_i;
  - M = Σ mid_i.
- Per valid event:
  - U = S − A − F_buy: payout beyond the cost of buying the whole field;
  - O = B − F_sell − S: proceeds from selling the whole field beyond the payout.

  Both use fees for one contract per player; the direct fee is primary and non-direct is reported. This is a calibration test, not an arbitrage claim: S is random and settles only after the tournament.

**Universe and complete-field coverage**
- Universe: every settled event of KXPGATOP10 (**primary**), plus KXPGATOP5 and KXPGATOP20 (secondary, reported only).
- **Coverage rule:** valid only if the listed players who teed off (markets that settled yes/no rather than at a pre-tee-off fair price) equal the **official field size**.
- **Sources for the field size and first-round date:**
  - pgatour.com, masters.com, pgachampionship.com, usga.org, theopen.com, golfchannel.com, golfweek.usatoday.com or espn.com;
  - retrieved by web search after this freeze, because the environment blocks those hosts directly;
  - recorded with URL and quote in `inputs/golf_coverage.csv`.
- A missing or unsourced value, or any mismatch, **invalidates the observation**. Missing golfers are never imputed.

**Snapshot and quotes**
- t_s = 16:00 UTC on the day before the official first-round date. That is the eve of play, before any shot.
- Quote per player: the last hourly candle ending at or before t_s, within 72 h.
  - A missing YES bid counts as 0.
  - A missing or zero YES ask counts as 1.00 (the player can't be bought).
- Liquidity: historical depth is not published. Top-of-book prices, the count of two-sided markets and 24-hour candle volume are reported. Any SURVIVE is conditional on depth, which cannot be verified historically.

**Test and kill (primary series KXPGATOP10)**
- Compute the one-sided 95% Student-t lower bounds of mean(U) and mean(O) across valid events.
- **KILL** ("the field price already reflects expected payouts, ties included, within bid/ask + fees") if both lower bounds are ≤ 0.
- **SURVIVE** otherwise.
- **INCONCLUSIVE** if there are fewer than 8 valid events.
- Reported only: mean(S − M) with its 95% CI (tie reflection at the mid), mean(M − N) and mean(S − N).

---

## M6-REWARDS: capital compatibility for a very small account

**Filed formula.** Liquidity Incentive Program terms filed 2026-07-15 (effective 2026-07-30), as modified 2026-07-30:
- Eligibility: all members except IB/FCM-routed trading.
- Per-second random snapshots.
- A snapshot is excluded unless the resting size meets **Target on both sides**.
- The Reference Price is the level where cumulative size reaches Target/5.
- Score = DF^(ticks below the Reference) × size, normalised per side.
- Payout = period score × Reward × non-excluded fraction, paid only if **≥ $1.00**.

**Analytic minimum capital (before looking at any book).** Target T (97% of live programs use 1,000); b_y and b_n are my YES and NO bid prices.
- **Empty or short side** (others' depth < T):
  - A lone provider must post the shortfall, up to T on both sides.
  - Committed capital = T(b_y + b_n) + max(T·b_y, T·b_n): the resting orders plus the worst plausible one-side fill, re-posted.
  - With a spread of at most 10¢ (b_y + b_n ≥ 0.90) this is **≈ 1.35T–1.8T**, i.e. **$1,350–$1,800 per market at T = 1,000**. That alone exceeds a $1,000 account.
  - The formula-only alternative (1¢/1¢ quotes, ≈ 0.03T) is **excluded as inconsistent with the Program's purpose**, and exposed to revocation by the Chief Regulatory Officer. It is reported only.
- **Contested side** (others already ≥ T):
  - Joining at the Reference Price (N = 0) earns a share of about x / (x + Q_others).
  - The payout floor needs (σ_y + σ_n)/2 × Reward ≥ $1.
  - So x can be small when Q_others is modest, but it grows linearly with competing depth.
  - Distance decay: a quote one tick below the Reference earns 50% of the score (DF = 0.5), two ticks 25%.

**Frozen configuration.**
- Equal size x on both sides.
- Join the current best YES and NO bids if their combined spread is ≤ 10¢; otherwise quote a 10¢ market centred on the mid (0.50 if both sides are empty).
- Full uptime and static competition are assumed. Both are **optimistic**, so a KILL is robust and a SURVIVE is weak.
- x_min is the smallest x whose payout is ≥ $1.00.
- C\* = x·b_y + x·b_n + max(x·b_y, x·b_n) + the maker fee on that fill.
- L\* = max(x·b_y, x·b_n) + the maker fee.
- Zero 24-hour volume is **not** treated as zero fill risk.

**Account definition (fixed now).**
- Very small account V = **$1,000**.
- A market is **compatible** if C\*(x_min) ≤ **$200** (V/5, so at least five markets can run at once) and the payout is ≥ $1.00 per period.

**Sample**
- Every live liquidity program with at least 1 h remaining whose market is active, fetched at run time.
- Two strata by the market's 24-hour volume (= 0 or > 0), with `random.Random(20260929)` drawing 30 programs from each, sorted by program id.
- One order-book snapshot per sampled market (the **first pass** decides).
- A second pass about 60 minutes later is reported for stability only.

**Kill.** KILL M6 for this project if **fewer than 10%** of sampled programs are compatible. Otherwise SURVIVE as capital-compatible. That verdict says nothing about profitability: adverse selection is not measured here.

---

## Structural terms-verification audit

This is separate from the price tests and uses no price data. It is reported in `research/edge_search/TERMS_AUDIT.md`.
