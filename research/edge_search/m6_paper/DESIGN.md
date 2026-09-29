# M6-REWARDS: prospective paper experiment (frozen design v2, NOT STARTED)

- **Status (2026-09-29):** IMPLEMENTED AND TESTED. **NOT STARTED.**
  - The collector, simulator and analysis exist and are hash-frozen in `PREREG_M6_PAPER.md`. See also `PRE_START_AUDIT.md`.
  - No collection has started. The collector refuses to run without an explicit approval flag. No order has been or will be placed. No credentials are used.
  - H038/H039 are not touched.
  - v2 incorporates the reviewer amendments of 2026-09-29 (§10).
- **Why:** PRICE TEST 1 found M6 **capital-compatible** (`../price_test_1/RESULTS.md` §M6). It measured *no* fills, adverse selection, competitor response or payout-floor risk. This experiment measures those.
- **Freeze procedure.** Implementation starts only after this design is approved. The collector, the simulator and their tests are then written to this specification. They are committed with sha256 hashes in `PREREG_M6_PAPER.md` **before the first collection request**. Any later change is a recorded deviation.
- **Smoke test.** A ≤ 2-hour technical smoke test of the collector is allowed before the freeze. Its data is deleted unread.

## 1. Question

    NET = liquidity rewards earned + trading P&L from fills − all applicable costs

The experiment asks this for a small participant who quotes both sides of LIP markets with **paper** orders, prospectively, under three maximum committed-capital limits:

**K ∈ {$30, $100, $200}.** These are research constraints, not trading instructions.

## 2. Data (public, unauthenticated GETs only; all raw responses recorded append-only)

| stream | endpoint | cadence |
|---|---|---|
| programs | `GET /incentive_programs?type=liquidity&status=active` and `status=upcoming` | every 10 min |
| epoch universe | all live programs' books via `GET /markets/orderbooks?tickers=…` (≤ 100 per call); `GET /markets?tickers=…`; `GET /series` and `/series/fee_changes`. The per-program ex-ante metrics of §4.2 are recorded. | every 6 h (00, 06, 12, 18 UTC) |
| tracked books | `GET /markets/orderbooks` for every tracked market (full depth) | Poisson times, **mean 10 s**, independent of book state |
| trades | `GET /markets/trades` (all markets), `min_ts` overlapping by 30 s, deduplicated by `trade_id` | every 5 s |
| trade completeness | tracked market `volume_fp` vs summed trades; a gap > 1% triggers a per-ticker backfill and marks the interval | every 10 min |
| tracked market state | `GET /markets?tickers=…` (status, close, result, settlement value) and `GET /events/{e}` (fee overrides) | every 5 min, and after close until settled |
| rules watch | the regulatory bucket listing (as in `proposals/structural_terms_v2.patch`) for new LIP filings | hourly |

**Rate and clock.**
- Sustained rate ≤ 3 requests/s, with exponential backoff on 429.
- Every record carries the local receive time (UTC and monotonic ns). Trades carry exchange timestamps.
- A tracked market with no book for > 60 s is in a **gap**.

**Measured headroom.** 4,940 live programs need 50 book calls per epoch. Up to about 600 tracked markets need ≤ 6 book calls per poll (≈ 0.6 requests/s at the mean 10 s poll).

## 3. Units

- An **episode** is one (account, program) pair. It runs from entry to the earlier of program end or market close.
- Accounts:
  - three **portfolio accounts** P30, P100, P200 (Arm P);
  - one **representative arm** U, where each episode stands alone.

## 4. Frozen market selection

### 4.1 Eligibility (evaluated at an epoch from that epoch's data only)

A program is eligible if all of the following hold:
- it is a liquidity program with `target_size_fp` set;
- its market status is `active`;
- the market is not a multivariate combo (no `mve_collection_ticker`);
- at least **24 h** of the program period remain.

The 24-hour rule is fixed ex ante. Payout-floor risk and snapshot-estimation noise dominate shorter stays, and the unrestricted ranking selects programs with hours left (§11).

### 4.2 Entry size and ex-ante metrics (PT1-frozen functions `configure` and `side_share`)

| metric | definition |
|---|---|
| **x15** | smallest equal per-side size whose static projected payout over the *remaining* period is ≥ **$1.50** (1.5 × the $1.00 floor). Search up to 20,000. |
| C\*(x15) | x(p_y + p_n) + max(x·p_y, x·p_n) + maker fee on that fill (PT1). |
| L\*(x15) | max(x·p_y, x·p_n) + maker fee |
| score | projected reward per day ÷ C\* |

- Fee state comes from the series fee history at the epoch, plus any event override.
- An unknown fee state is treated as maker fees at M = 1.

### 4.3 Arm P (portfolio accounts P30, P100, P200; independent of each other)

At every epoch:
1. Take the eligible programs not already held by the account. Keep one per market: the higher score (ties by program id).
2. Sort by score, descending (ties by program id).
3. Admit programs in that order while `committed(account) + C*(x15) ≤ K`. Here `committed` is the current resting-order reservation, plus inventory at cost, plus the fill reserve max(x·p_y, x·p_n) of every held program.
4. An admitted program is quoted at its entry x15 until the episode ends. The size is never changed after entry.

### 4.4 Arm U (representative; no capital pooling)

- **Who is drawn.** At each daily epoch (00:00 UTC), consider eligible programs that **started within the previous 24 h** and have C\*(x15) ≤ $200.
- **How.** Draw 10 at random from each 24-hour-volume stratum (= 0 and > 0) with `random.Random(20261001 + epoch_day)`. If fewer are available, take all.
- **Simulation.** Each episode runs standalone at x15.

### 4.5 Nothing else

- No re-ranking after entry.
- No exits or additions based on P&L, fills or rewards.
- No selection after the fact.

**Collector coverage.** The collector tracks every Arm U draw and the **top 100** programs by score at each epoch, each for the rest of its period. At K ≤ $200 the greedy fill admitted 16 programs in the feasibility snapshot. Tracking 100 covers the admitted programs plus those skipped as unaffordable. Any Arm P choice outside the tracked set is logged as a breach and reported. Expect up to about 600 tracked markets at once: ≤ 6 book calls per poll.

## 5. Frozen quoting rule (every episode)

- **Target prices** at every tracked-book poll, from the real book (our paper orders are not in it). This is the PT1 `configure`:
  - if best YES bid + best NO bid ≥ 0.90, join both best bids;
  - otherwise quote a 10¢-wide market around the mid (0.50 if both sides are empty);
  - clamp prices to [0.01, 0.99] on the market's price grid.
- **Latency.** Orders become live **1.0 s** after the snapshot's receive time. This is REST polling with no credentials; there are no websockets.
- **Reprice.** If a side's target price differs from its live order's price, cancel it and place a new order at the target. The new order goes to the back of that level's queue as seen in the triggering snapshot.
- **Size, net-position limit.** Let q be the net YES position; pairs net at $1, as Kalshi nets positions. Then:
  - desired YES bid = max(0, min(x, x − q));
  - desired NO bid = max(0, min(x, x + q)).

  So |q| ≤ x at all times: at most one clip of one-sided inventory per market.
- **Replenishment.** A partially filled order keeps its queue place. A shortfall against the desired size is posted as a new order at the back. An excess is cancelled newest-first.
- **Capital limit** (Arm P). No order is placed or enlarged if `committed` would exceed K. The size is cut to the largest integer that fits, and a side is left empty if nothing fits. Sides that reduce |q| have priority.
- **Stop.** At program end, market close, or market status ≠ active, cancel everything. Inventory is **held to settlement**.
- There is no taking, no unwinding and no cross-market hedging.

## 6. Frozen fill model (paper, causal, event-ordered)

Our order has side s, price p, remaining size n, queue ahead Q (the level size at the triggering snapshot) and becomes live at t₀. After t₀, trades and snapshots are processed in time order.

- **Matching.**
  - A trade with `taker_side = no` at `yes_price = y` consumes YES bids at y.
  - A trade with `taker_side = yes` consumes NO bids at `no_price`.
- **At our level.** Q −= count. Once Q < 0, we fill min(n, −Q) and set Q = 0; later volume at the level fills us directly.
- **Trade-through.** A print strictly worse than p on our side means the bids at p were exhausted first. We fill min(n, count).
- **Level vanished.** If the level vanishes from a snapshot without a trade-through, set Q = 0 (we are at the front).
- **Queue cancellations.** Between snapshots, a size decrease Δ at p that trades don't explain is attributed three ways. All three are run.

  | variant | treatment of Δ |
  |---|---|
  | **V_T** | ignored: fewest fills |
  | **V_P** | Q −= Δ·Q/(level − n) |
  | **V_C** | Q −= Δ: most fills |

- **Fees.** Each fill pays the maker fee in force (series history plus event override): direct-member rounding $0.0001 primary, $0.01 reported. There are no taker fees, because we never take.
- **Trade completeness.** Intervals flagged incomplete stay in the primary result and are excluded in a reported sensitivity.

## 7. Frozen reward model

- **Snapshot score.** At every tracked-book poll, compute our per-side share with PT1 `side_share`:
  - our live paper orders are added at their price and remaining size;
  - the Reference Price, Target exclusion and discount follow the filed Liquidity Incentive Program (modified 2026-07-30);
  - an excluded snapshot scores 0;
  - **all other resting size is assumed eligible**, which is conservative for our share.
- **Payout estimate.** P̂ = R × (T_cov / T_period) × mean_k[(s_y,k + s_n,k)/2].
  - T_cov is our time in the period, excluding gaps. Gaps earn 0.
  - Because polls are independent of book state, the sample mean estimates the time average. Its SE uses hourly batch means.
- **Payment.**
  - Primary: floor-to-cent of P̂, paid only if P̂ ≥ $1.00.
  - **Conservative:** paid only if P̂ − 1.645·SE ≥ $1.00.
- **Decision uses the conservative variant.**

## 8. Frozen P&L and capital accounting

- **Positions.** Per market, YES count a and NO count b. min(a, b) pairs are redeemed at $1 as they form (netting). Cash moves at each fill price and fee.
- **Settlement.** YES pays the settlement value (1, 0 or scalar); NO pays 1 − value.
- **Analysis cutoff: collection end + 30 days.** Inventory still unsettled then is marked at **liquidation value**: best bid on our side minus the taker fee, or 0 if there is no bid.
- **Committed capital** = Σ resting reservations (both sides, cost of each buy) + Σ net inventory at cost + held programs' fill reserves. Report its time average, maximum and capital-days.
- **Capital-cost sensitivity** (reported only): 4.0%/year on average committed capital.

## 9. Adverse selection and diagnostics (reported, not decisive)

- **Markouts.** For every paper fill: mid after 10 s, 1 min, 5 min, 30 min, 2 h and at settlement, relative to the fill price, per contract and per $.
- **Decomposition.**
  - spread capture on round trips;
  - inventory P&L on one-sided fills.
- **Reward diagnostics:**
  - realised vs ex-ante projected share;
  - fraction of time scored or excluded;
  - repricings per hour;
  - payout-floor misses;
  - changes in competitor depth at our level.
- **Other:**
  - inventory time series;
  - worst realised |q|·price per market;
  - daily NET marked to market;
  - maximum drawdown.

## 10. Frozen duration, stopping and decision rules (v2, reviewer amendment of 2026-09-29)

**Arms.** Every arm is evaluated separately:
- the ranked portfolio arms **P30**, **P100** and **P200**;
- the random-sample arm **U**.

Results are **never pooled** across arms.

**Clock.** Day 0 is the first 00:00 UTC after collection starts. Checkpoints fall at 00:00 UTC.

**Stopping rule, per arm.**

| step | rule |
|---|---|
| day 35 | First formal checkpoint. Let n be the number of the arm's **completed** episodes: episode end ≤ checkpoint. |
| n ≥ 20 at day 35 | Formal decision on exactly the episodes completed by day 35. The arm makes no new entries after day 35. Its still-running episodes are simulated to the end and **reported**, but are not part of the decision. |
| n < 20 at day 35 | The arm keeps entering programs under the unchanged frozen rules. It is checked at every daily checkpoint from day 36 to day 60, **counts only**. At the first checkpoint where n ≥ 20, the formal decision is made on exactly the episodes completed by then, and the arm stops entering. |
| day 60 and still n < 20 | **INSUFFICIENT EVIDENCE.** No decision, and the threshold is not changed. |

**No peeking.** Until an arm reaches its formal checkpoint, the analysis code outputs only its episode counts. That is enforced in code (`analysis.py`); no profitability of a continuing arm is computed or shown. No parameter is changed after collection starts.

**Collection end.**
- Book and trade collection runs until every arm has reached its formal checkpoint, or until day 60.
- Episodes entered before an arm's checkpoint are followed to their end.
- Market-state polling for every ever-tracked market continues until the arm's **settlement cutoff**: its formal checkpoint + 30 days.

**Invalid runs.** Cumulative collector downtime > 24 h, or loss of the trade feed for > 6 h, before the last formal checkpoint makes the run **INVALID**. It would be re-registered and restarted, not patched.

**LIP rules.** If an LIP filing modifies the rules during the window, results are split at its effective date. Episodes spanning the change are reported separately.

**Primary metric per arm A.**
- NET_A = Σ over the decision set of (conservative payout + trading P&L − fees).
- Trading P&L is settled value where the market settled by the settlement cutoff. Otherwise it is the liquidation mark at the cutoff: best bid on our side − taker fee, or 0 with no bid.
- Take the **minimum over the three fill assumptions V_T, V_P and V_C**: the worst decides.

**Uncertainty.**
- LB95_A comes from a cluster bootstrap. Resample the `event_ticker` clusters of the worst variant's decision set with replacement, with clusters sorted by name before resampling. Use 10,000 resamples and `random.Random(20261001)`. LB95 is the **500th smallest** resampled NET: the order statistic ceil(0.05 × 10,000).

**Decision per ranked arm (P30, P100, P200).**

| verdict | condition |
|---|---|
| **SURVIVE (paper)** | n ≥ 20 **and** NET > 0 **and** LB95 > 0 **and** NET > 0 with the single most profitable episode removed |
| **KILL** | n ≥ 20 and NET ≤ 0 |
| **INCONCLUSIVE** | n ≥ 20 and neither of the above |
| **INSUFFICIENT EVIDENCE** | n < 20 at day 60 |

**M6 overall.**
- **SURVIVE** if any ranked arm survives (the report names which).
- **KILL for this project** if all three ranked arms are KILL.
- **INCONCLUSIVE** otherwise.

A paper SURVIVE is not authorisation to trade.

**Arm U** follows the same stopping rule. It reports NET, LB95, mean NET per episode and per $ of C\* per day, all separately. It is representative evidence, not the M6 decision.

## 11. Feasibility at K = $30 / $100 / $200 (static; no fills; `outputs/feasibility_20260929T0435.txt`)

This comes from one snapshot of all 4,942 live programs (2026-09-29 04:35 UTC). It uses the same PT1 functions and the §4.2–4.3 entry rule.

**With the frozen ≥ 24 h entry rule:**

| K | affordable individually | greedy selection | committed | static reward/day | static $/day per $ | worst-case one-side fill loss |
|---|---|---|---|---|---|---|
| $30 | 1,291 | 4 programs | $27.90 | $2.51 | 0.090 | $11.11 |
| $100 | 2,798 | 9 | $99.97 | $8.12 | 0.081 | $39.57 |
| $200 | 3,350 | 16 | $199.55 | $14.43 | 0.072 | $83.51 |

- C\*(x15) across 4,210 markets: p10 **$14.16**, p50 **$55.80**, p90 **$623.39**.
- Contrast, without the 24 h rule: $30 buys one table-tennis program with 0.1 days left, at a "$24.84/day" static rate. That is why the rule is fixed ex ante.

**Reading.** The per-dollar static rates (7–9% a day) are not credible as realised returns. They assume:
- full uptime;
- frozen competitors;
- no fills;
- no payout-floor misses.

Their size is exactly why the untested terms (fills, adverse selection, competition, floor risk) decide M6. What the table does establish:
- At every K a small account can hold several programs at the minimum floor-clearing size.
- Worst-case one-side loss is capped at about 40% of K by the netting and inventory rules.
- Absolute stakes are small: at most dollars per day, even if the static rates held.

## 12. Known limitations (accepted, disclosed)

1. **Paper orders are absent from the real book.** There is no impact and no competitor reaction to us. The queue position is modelled, and three fill variants bracket it.
2. **A slow participant.** REST polling at about 10 s with 1 s latency models someone slow. Faster (credentialed websocket) participants would face less staleness, but credentials are excluded by design.
3. **Snapshot sampling.** Kalshi's per-second random snapshots are approximated by Poisson polls, and the SE is reported.
4. **Order eligibility of others is unobservable.** Treating it all as eligible is conservative.
5. **Trade feed.** It may be incomplete; completeness is checked and a sensitivity reported.
6. **Settlement lag.** Liquidation marks for unsettled inventory are conservative. Scalar settlements are handled.
7. **Ignored for sizes of this scale:** order rejections, self-trade prevention, position limits, deposit and withdrawal costs.

## 13. Implementation plan after approval (not done now)

- `m6_paper/collector.py`: the §2 streams only; GETs only; no order endpoints anywhere in the code.
- `m6_paper/sim.py`: an offline, deterministic, causal replay of §4–8 over the recorded streams.
- Tests:
  - queue fills;
  - trade-through;
  - partial fills;
  - V_T/V_P/V_C;
  - repricing resets;
  - netting;
  - the |q| ≤ x cap;
  - the capital limit;
  - the payout floor and its conservative variant;
  - gap handling;
  - selection determinism;
  - no look-ahead: a property test that shuffling future data does not change past decisions.
- `PREREG_M6_PAPER.md`: code hashes, start date, and this document's hash.
