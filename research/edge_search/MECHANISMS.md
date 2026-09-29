# Kalshi small-participant edge search — ten candidate mechanisms (research only)

- **Status:** research document for independent review. Nothing has been implemented, collected, backtested or traded.
- **Snapshot date:** 2026-09-29 (UTC). All counts come from the public API snapshots listed in `evidence/EVIDENCE.md`.

## Scope and discipline

- No orders were placed, no credentials were used, and nothing from H038/H039 (or any other H0xx experiment) was opened, inspected or used.
- The structural-arbitrage project (`research/structural_arb`, frozen at READY_TO_FREEZE) is referenced only to avoid duplicating it.
- **No outcome-conditioned statistic was computed.** This means no price-versus-result, calibration, P&L or hit-rate figure for any market. The falsification tests below are therefore pre-registered: their kill criteria were written before any of their test statistics were looked at.
  - The only price-derived numbers in this document are prevalence counts: the spread distribution and how many markets quote at the 1¢/99¢ grid edge.
- **No ranking or overall score is given.** The comparison matrix in §4 is qualitative and per-dimension.
- **Independence rule applied.** Two ideas are only separate mechanisms if they rest on different economic reasons *and* different falsification tests. A different asset, horizon, threshold or category does not qualify. §3 records the closest pairs and why they were kept apart; §5 lists ideas that were merged or excluded for failing this rule.

---

## 1. Universe map (2026-09-29)

### Two exchanges

- **Predictions exchange (event contracts):**
  - 115,126 active markets in 12,320 open events and 4,125 series.
  - The markets are sharded by `exchange_index`: combos went to shard 1 in August 2026, and new crypto, commodities, tennis, baseball and basketball events to shards 2 and 3.
  - Collateral must be pre-allocated per shard.
- **Margin exchange:** 27 perpetual futures (23 crypto, 4 metals), with funding payments. The BTC perp traded about $579M notional in the snapshot's trailing 24 hours. Perps have no RFQs. They matter here only as context and as a hedge instrument (§5).

### Composition of active markets

| dimension | breakdown |
|---|---|
| Category | Sports 56,187 · Elections 22,224 · Financials 9,846 · Entertainment 8,808 · Economics 5,365 · Crypto 4,514 · Politics 2,658 · Climate/Weather 1,372 · Commodities 1,320 · Mentions 1,138 · Science/Tech 1,063 · Companies 568 |
| Series frequency | custom 49,553 · one-off 36,696 · annual 13,474 · hourly 7,708 · monthly 3,007 · weekly 2,496 · daily 2,129 · 15-min 24 |
| Strike type | structured 33,123 · greater 32,590 · greater_or_equal 21,041 · custom 19,621 · between 3,333 · less 527 · none 4,862 |
| Price grid | linear_cent 105,419 (92%) · tapered_deci_cent 9,226 · deci_cent 383 · half-cent 66 · centi-cent 32 |
| Fees | taker-only quadratic 107,974 · quadratic with maker fees 7,152 · multiplier 1 / 0.5 / 0 on 114,080 / 834 / 212 markets |
| Early close | `can_close_early` = true on 115,017 of 115,126 markets |
| Terms | 1,016 distinct contract-terms PDFs |

The most common named settlement sources are news organisations (ESPN 750 series, Reuters 696, WSJ 667, CNN 554, …).

### Activity is extremely concentrated

- 96,847 of 115,126 active markets (84%) had zero volume in the last 24 hours, and 62,898 had zero open interest.
- The top 1% of markets carry 90.6% of 24-hour volume.
- Only 2,401 of 4,125 series traded at all in 24 hours.
- Across the 72,724 markets quoted on both sides, the summary spread is 1¢ at p10, 9¢ at the median and 57¢ at p90.
- In a roughly 5-second slice of the public trade tape, 131 of 1,000 prints were combos (KXMVE*).

### Settlement mechanics (12,000 non-combo markets settled in the last 3 days)

- 8,797 settled NO, 3,198 YES and 5 **scalar**. The scalar cases were:
  - an abandoned USL game split 0.34/0.33/0.33;
  - a T20 cricket no-result settled at 0.50/0.50.
- The settlement timer was 60 s for 78% of markets, and 30–60 min for most of the rest.
- Settlement followed close by 157 s at the median, and by 1,877 s at p90.
- Of the 5,000 most recently settled combos, 39 settled scalar, and **all 5,000 had zero volume**: the RFQ created the market, but no quote was ever executed.

### Subsidies and carry

- **Liquidity incentives (LIP)** — 4,139 programs are live, all of the liquidity type, with a combined pool of **$494,770**:
  - median $100 per program, or $18.76 per market-day (p10 $8.21, p90 $150.16);
  - target size 1,000 contracts in 97% of programs, and a discount factor of 0.5 per tick in all of them;
  - **2,015 live programs ($224,335 of pool) sit on markets with zero 24-hour volume.**
- **Interest.** Kalshi pays a variable APY, stated as 3.25%, on cash **and open positions** for balances of at least $250 (D8).

### Grid-edge prevalence

| grid | markets | YES ask at 1¢ | YES bid at 1¢ | YES bid at 99¢ | YES ask below 1¢ |
|---|---|---|---|---|---|
| linear_cent | 105,419 | 8,493 | 8,166 | 1,329 | 0 (impossible) |
| tapered_deci_cent | 9,226 | — | — | — | 503 |
| deci_cent | 383 | — | — | — | 137 |

### Existing-work check

**Inside this repository:**

- **`research/structural_arb`** covers guaranteed, rule-defined locks on:
  - R1 — mutually exclusive and exhaustive (MEE) buckets;
  - R2 — nested thresholds;
  - R3 — adjacent ranges;
  - R4 — duplicates;
  - R5 — combos.

  It works within a family of one real-valued underlying, or within a categorical event. Its findings:
  - no RULE_DEFINED_LOCK observed;
  - the cross-series AAA gas and SOL candidates are TERMS_EQUIVALENCE_UNRESOLVED;
  - INX was de-registered.

  None of the ten mechanisms below re-proposes an R1–R5 lock. The nearest, M7, is discussed explicitly.
- **`research/position_hedge`** is a design only (offsetting positions under Rule 5.3(c)). No overlap.
- **`src/`** contains generic news-sentiment, cointegration and volatility strategies. These are excluded by the brief, and none of the ten mechanisms uses them.

**Outside this repository:** the H0xx hypothesis records are **not** here — H022, H024, H029, H031, H038 and H039 are all absent. The ones named in the brief (H024/H029/H031) could not be checked. To make that check quick for the reviewer, each mechanism starts with a one-sentence **core claim**. If an earlier H0xx tested the same core claim, drop that mechanism rather than re-testing it under a new name.

---

## 2. The ten mechanisms

Conventions used throughout:

- **Fee model.** "Fees" means the current fee model: taker fee = multiplier × 0.07 × C × P(1−P), with the direct-member rounding as the expected case and non-direct per-order cent rounding as the stress case. Resting orders pay no fee in taker-only (`quadratic`) markets.
- **5.11-safe.** An executed price within ±20¢ of any defensible fair value at the time of the trade. Outside that band, Rule 5.11 lets Kalshi review and cancel the trade if the counterparty asks within 15 minutes (D2).
- **Ordering.** Each test is price-free first wherever possible, so a mechanism can die before any market price is examined.
- **Evidence references.** D1–D12 are the numbered official-document facts in `evidence/EVIDENCE.md`.

### M1 — Stale resting orders after a discrete public determination (halt latency)

**Core claim:** In live-event markets, the outcome becomes publicly known before Kalshi halts trading, and resting orders placed earlier stay executable in that gap.

- **Mechanism.**
  - For sports, awards, live-speech "mention" markets and similar events, the determining event is public on live feeds and broadcasts.
  - Kalshi ends trading by moving `close_time` earlier. That is an operational action, allowed because `can_close_early` is true on 99.9% of markets (D1, D3). It is not an automatic trigger.
  - Until close, every resting order posted before the determination can be hit.
- **Economic reason.**
  - A resting limit order is a free option written by its owner.
  - Kalshi has no cancel-on-determination and imposes no quoting obligation on ordinary members. Occasional liquidity providers in low-attention markets (minor soccer leagues, ITF tennis, T20 cricket, earnings-call mentions) often do not run kill switches.
  - Exchange halt latency plus owner inattention gives a recurring, mechanical window.
- **Expected manifestation.**
  - Trades time-stamped after the public determination (plus a realistic latency) at prices far from the eventual settlement, with the taker on the winning side.
  - These should be concentrated in low-attention series and near zero in heavily traded ones.
- **Required data.**
  - The public trade tape (`/markets/trades`, `/historical/trades`: µs timestamps, price, taker side).
  - Market lifecycle fields.
  - **An independently time-stamped public determination time**, e.g. ESPN play-by-play `wallclock`, or another public feed that records when a result was published. This is the hard part.
- **Causal timing and look-ahead/latency risks.**
  - The signal time is when the result was *published*, not when it happened. Broadcast and stream delays (about 5–60 s) and the participant's own latency must be added before a stale trade counts as capturable.
  - Using the settled result to label a trade "stale" is look-ahead unless the feed timestamp shows the result was knowable at that trade's time.
  - `settlement_ts` and the final `close_time` are post-event fields and must not be used as the determination time.
- **Settlement/rules risk.**
  - **Rule 5.11 is the central limit.** A trade more than 20¢ from fair value (which, after a public determination, is near 0 or 1) can be reviewed on request within 15 minutes and cancelled at Kalshi's discretion. Rule 5.11(b) says trader-preventable errors are not "extraordinary", but the discretion stays with Kalshi.
  - So the capturable edge is effectively only the 5.11-safe band: buying the winner at 80¢ or more.
  - Other risks:
    - stat corrections after the game, for player props;
    - official-versus-provisional sources (F1 pays only on the final FIA classification);
    - disputes: determined → disputed → amended.
- **Execution risk.**
  - A race with other takers: whoever arrives first gets the stale order.
  - The market can close mid-order (`MARKET_INACTIVE`).
  - Stale orders are often small.
  - Rate limits.
  - A "determination" can be reversed by video review or a challenge.
- **Cheapest falsification test (not optimised).**
  - One class: the next 100 completed FBS college-football games that have Kalshi game-winner, spread and total markets, with the final-play time taken from ESPN's public play-by-play `wallclock` field.
  - For each game, sum the executed volume in trades that:
    - are time-stamped more than 60 s after the final play (a fixed latency allowance, not tuned);
    - have the taker on the side that settles YES;
    - are priced between 0.80 and 0.95 (5.11-safe, and an edge of at least 5¢).
  - Compute the edge dollars net of taker fees.
- **Kill result (fixed in advance).** Kill if either:
  - the median per game is below $5 of net edge and the 100-game total is below $500; or
  - more than 80% of that total comes from 5 or fewer games.
- **Result justifying deeper research.**
  - A median of at least $20 per game;
  - present in at least 30% of games;
  - with both halves of the sample (games 1–50 and 51–100) individually above the kill line.
  - Only then extend to one low-attention class that has timestamped public determinations.
- **Capacity estimate.** $0 to about $5k per week gross across all live-event markets, and quite possibly around zero. It is bounded by stale resting size, which is small in exactly the markets where competition is thin. Uncertainty spans orders of magnitude.

### M2 — Partially realised settlement statistics (averages, running extremes, cumulative counts)

**Core claim:** When a contract settles on a statistic accumulated over a window, the already-published part of the window narrows or one-sides the distribution in a way that quotes do not reflect.

- **Mechanism.**
  - Many contracts settle on a window statistic rather than a point value. Examples:
    - the arithmetic mean of daily Ornn values for a month (KXDDR5MS);
    - the 60-second BRTI average (KXBTCD);
    - a daily maximum temperature (KXHIGHNY);
    - "above 9M views at any point during" a week (KXYTVIEWSW);
    - monthly max/min "ever above/below" markets (KXWTIMAX/MIN, KXBTCMINMON, KXAAAGASMAX).
  - Rules-text prevalence: "average" appears in 7,654 markets across 229 series; "at any point / ever" in 1,159 markets across 64 series.
  - Once part of the window has been published, the conditional distribution narrows (for an average, the remaining variance scales with the square of the remaining fraction) or becomes one-sided (a running maximum can only rise).
  - This excludes cases already fully determined — a running maximum already through the strike. Those are M1.
- **Economic reason.**
  - Liquidity providers in thin series quote with a generic model of the *spot* level, not the window statistic.
  - Keeping a daily ledger of the realised part is a fixed cost that is not worth it for large providers in series with tiny volume. KXDDR5MS, for instance, shows 0.53/0.62 quotes and zero volume.
  - The information is public but carries a bookkeeping cost, which makes it a low-capacity niche.
- **Expected manifestation.**
  - Late in the window, strikes that are near-certain given the realised part (say below 2% or above 98%, even under deliberately inflated volatility) trade at prices inconsistent with that bound.
  - Mid-window, implied dispersion is wider than the remaining-window arithmetic implies.
- **Required data.**
  - Intra-window values from the named Source Agency, with the time each value was published (its vintage).
  - Kalshi books at pre-set checkpoints.
  - The volatility of the source series over a trailing pre-period, used only for a fixed conservative model.
- **Causal timing and look-ahead/latency risks.**
  - Only values published *by the checkpoint time* may be used. Publication lags matter: YouTube Charts daily views appear with a delay; AAA updates overnight.
  - Rebuilding "realised so far" from a later, revised series is look-ahead.
  - For weather, preliminary and final values differ by rule (D10).
- **Settlement/rules risk.**
  - "Revisions after expiration not accounted".
  - Rounding to two decimals (Ornn).
  - Source-specific display rules ("values displayed from a New York IP address").
  - Discretionary settlement if the source is missing (D4).
- **Execution risk.**
  - The targets are thin by construction, so spreads can exceed the edge.
  - Depth may be a single resting order.
  - For BRTI, the last 60 s is heavily competed.
- **Cheapest falsification test.**
  - **Pre-registered selection rule** (no cherry-picking): take the first family, in alphabetical order of series ticker, among the averaging and running-extreme series whose rules name a Source Agency that publishes daily values for free with timestamps and without revisions.
  - Snapshot its books read-only at 50% and 80% of each window, for 20 consecutive windows.
  - Compute the fair value under a fixed random-walk model: volatility is 2× the trailing 60-day volatility, estimated before each window, with no fitting to outcomes.
  - Record every executable deviation of 5¢ or more after fees with at least 10 contracts of depth, on the side the model calls at least 98% or at most 2%.
- **Kill result.** Kill if either:
  - fewer than 10 such deviations occur across the 40 checkpoints; or
  - once the windows settle, the model's "at least 98%" side wins less than 95% of the time.
- **Result justifying deeper research.**
  - At least 10 deviations;
  - the near-certain side winning at least 97% of the time;
  - net depth-limited edge above zero under the non-direct fee stress case.
- **Capacity estimate.** Roughly $10–$200 per window per series, across perhaps a few dozen eligible series, so about $0–$2k per month. Low, with wide uncertainty.

### M3 — The settlement measurement differs from the salient public proxy

**Core claim:** When the contract's settlement source or measurement differs from the proxy most traders watch, and the difference is predictable, prices anchored to the proxy are biased by a computable amount.

- **Mechanism.** Contracts bind to one specific measurement, while the market watches a proxy. Examples:
  - **NYC daily high.**
    - Settlement: The Weather Company at station CLINYC.
    - Proxies: hourly METARs, AccuWeather, Google.
    - The rules themselves warn that "Not all weather data is the same" and that preliminary values have "rounding and conversion differences".
  - **Crypto.** The 60-second BRTI average versus Coinbase or Google spot, again flagged in the rules.
  - **FX.** "The open price of the Euro/Dollar … at 10 AM EDT" from ICE via TradingView FX_IDC, versus other feeds.
  - **Economic data.** The first BLS print versus revised values.
  - **Mention markets.** The exact phrase counts, and so do plural and possessive forms, but "grammatical/tense inflections" do not.

  Where proxy and settlement value differ *predictably* — station versus city, °C→°F rounding, continuous versus hourly sampling, bar open versus mid — prices anchored to the proxy are biased by a computable amount.
- **Economic reason.**
  - Attention cost and salience. The proxy is free and visible, while the settlement series can be delayed, gated or awkward to find.
  - Kalshi's own warnings in the rules show that users trade off proxies.
  - **Source change.** The weather terms PDF names the National Weather Service as Source Agency, but the live market rules name The Weather Company (D10). A source change like this is exactly when proxy habits lag.
- **Expected manifestation.** Near close, on days when the proxy sits on one side of a bucket boundary and the settlement measurement predictably sits on the other, prices track the proxy.
- **Required data.**
  - The historical settlement value (the `expiration_value` of settled markets).
  - A proxy series for the same window with availability timestamps: for NYC, ASOS hourly and 6-hour-maximum METARs for KNYC from the Iowa Environmental Mesonet archive.
  - Kalshi prices (only in step 2).
- **Causal timing and look-ahead/latency risks.**
  - The settlement value is often published *after* close. The weather markets close at 05:00 UTC, which is 1:00 AM EDT or midnight local standard time.
  - So the signal may use only the proxy and preliminary values available before close.
  - Labelling days with the final value is legitimate for the outcome, but not for the signal.
- **Settlement/rules risk.**
  - Terms say NWS, market rules say TWC (D10), which is unresolved.
  - "Only the first official non-preliminary report" counts.
  - A material-error hold can delay expiry.
  - If data is missing, markets settle at "the last fair price determined by Kalshi".
- **Execution risk.**
  - Weather is a flagship retail category with specialised automated traders, so competition is likely.
  - Liquidity sits in a few city/day buckets.
  - The edge exists only on boundary days.
- **Cheapest falsification test (step 1 needs no prices).**
  - **Step 1.**
    - Take the past 365 settled NYC daily-high markets.
    - Compare the settlement value with the proxy bucket known at 8 PM local time. The proxy is the maximum of the hourly METAR temperatures together with any 6-hour maximum group reported by then.
    - Measure (a) how often the bucket assignment differs and (b) whether the difference has a consistent sign.
  - **Step 2 (only if step 1 passes).**
    - Take Kalshi snapshots at 8 PM local over the next 60 days.
    - Compare the price of the proxy bucket and the adjacent bucket with the step-1 conditional frequencies. Those frequencies come only from the prior-period data.
- **Kill result.** Kill if either:
  - step 1 finds bucket disagreement on fewer than 5% of days, or no signed bias (sign test p > 0.2); or
  - step 2 finds the settlement bucket's 8 PM price already within fees and half the spread of its step-1 conditional frequency, on average.
- **Result justifying deeper research.**
  - Step 1: disagreement on at least 10% of days, with a consistent sign.
  - Step 2: prices following the proxy, leaving a gap of at least 3¢ after fees at 10 contracts or more of depth on at least 25% of boundary days.
- **Capacity estimate.** About $10–$100 per day per liquid city if it works, and only on boundary days. Other pairs (FX open, mentions) would need their own step-1 check under the same mechanism. Moderate-to-low, with high uncertainty.

### M4 — Price-grid floor plus fee rounding at the tails

**Core claim:** In 1¢-grid markets the 1¢ floor, not risk or capital cost, keeps near-impossible outcomes overpriced. Contracts on a finer grid are the natural control.

- **Mechanism.**
  - In linear-cent markets YES cannot trade below 1¢.
    - 8,493 markets show a YES ask at 1¢.
    - 8,166 have resting YES *bids* at 1¢, i.e. long-shot buyers.
  - Outcomes with a true probability well below 1% therefore cannot be priced correctly.
  - Selling them — hitting 1¢ YES bids, or equivalently buying NO at 99¢ — earns at most 1¢ minus fees.
  - Tapered and deci-cent markets (503 + 137 already quote below 1¢) show what happens without the floor.
- **Economic reason.**
  - The binding tick floor is a hard mechanical constraint, and it meets steady lottery-style demand.
  - The usual excuse for tail overpricing — sellers' capital lock-up — **mostly disappears on Kalshi**, because open positions earn the same variable APY as cash (D8).
  - What remains is the floor plus per-order fee rounding. At P = 0.99, the taker fee is about 0.069¢ per contract under direct rounding. But under per-order cent rounding a single-contract order pays a full 1¢, which erases the edge.
  - If overpricing persists, it is a grid constraint, not a risk premium.
- **Expected manifestation.**
  - Among contracts whose YES ask is exactly 1¢ at a fixed horizon, the realised YES rate is well below the break-even rate after fees.
  - Economically comparable deci-cent contracts sit below 1¢.
- **Required data.**
  - Historical settled markets with the best bid/ask and resting size at a fixed pre-close horizon, from the public trade and candlestick history; results.
  - The grid type of each market.
- **Causal timing and look-ahead/latency risks.**
  - Prices must be read at a fixed horizon before scheduled close (T−7 days). Last prices are already moved by early information and early close.
  - Include every market that met the condition at T−7 days, including ones that later moved (no survivorship).
  - Use cluster-robust inference by event: long shots in the same event, or on the same shock, resolve together.
- **Settlement/rules risk.**
  - Discretionary settlements (D4).
  - Scalar settlements at "fair value" when the tail event is ambiguous.
  - Early-expiry rules (D3).
- **Execution risk.**
  - The tail loss is 99× the per-contract edge, and it is correlated across related long shots.
  - Depth at 1¢ bids is unknown until books are sampled.
  - Capital-intensive: about $0.99 of collateral per contract.
- **Cheapest falsification test.**
  - Take all binary markets settled between 2026-01-01 and 2026-06-30 whose YES ask was exactly 1¢ at T−7 days and whose 1¢ YES bid had at least 10 contracts resting.
  - Measure the realised YES rate with an exact event-clustered confidence interval.
  - As a control, take deci-cent and tapered markets with an ask of 1¢ or less at T−7 days, and record their realised rate and their price level.
- **Kill result.** Kill if either:
  - the realised YES rate is at least 0.8% (break-even after fees, direct-rounding case); or
  - fewer than 200 events qualify.
- **Result justifying deeper research.** All three of:
  - the realised rate is 0.3% or less, with a cluster-robust 95% upper bound below 0.6%;
  - the control markets' realised rate is similar while their prices sit below 1¢, which shows the floor rather than demand is doing the work;
  - no single event cluster contributes more than 20% of the "wins".
- **Capacity estimate.** Opportunity-rich but capital-bound: an edge of at most about 0.7¢ per contract, with about $0.99 of collateral. A $10k account holds about 10k contracts, so it earns perhaps $0–$70 per holding cycle, and one correlated tail event could erase many cycles. Low return on capital, with fat left-tail uncertainty.

### M5 — Payout multiplicity: tie conventions that break the "exactly N winners" normalisation

**Core claim:** Where the rules let more than N contracts pay in full, prices normalised to N winners (or copied from dead-heat venues) understate YES.

- **Mechanism.** Kalshi's tie rules differ by series:
  - **Golf top-5/10/20** pays **in full to everyone tied at the boundary** (GOLFFINISH terms, D9: "if … tied for 10th … resolves to Yes").
  - **NCAA conference "top 4/5"** treats all teams with identical conference records as having achieved the position — no official tiebreakers.
  - **Round-leader and fantasy "top N"** markets use dead-heat 1/N (rounded *down* to the cent).
  - **FIDE ratings** use the official tiebreakers.

  (Tie or dead-heat wording appears in about 15,348 markets across 354 series, an upper bound.)

  So the expected number of paying YES contracts per event can exceed N. Pricing normalised to "N winners", or copied from sportsbook top-N prices, which carry dead-heat reductions, underprices Kalshi YES.
- **Economic reason.**
  - Normalisation heuristics, plus anchoring *hypothesised* on reference venues whose dead-heat rules pay less.
  - Conference standings as published apply tiebreakers, so the salient "projected standings" undercount YES outcomes.
  - Short conference schedules (8–9 games) make ties at the cutoff common. The frequency is to be measured in step 1, not assumed.
- **Expected manifestation.** The sum of YES mids over the whole field sits near N, rather than near the empirical expected number of YES outcomes.
- **Required data.**
  - Public final standings or leaderboards (FBS conference records for 10 seasons; PGA Tour final leaderboards) to estimate E[number of YES outcomes].
  - Kalshi books for the full field at a pre-set time (step 2 only).
- **Causal timing and look-ahead/latency risks.**
  - E[count] must come only from seasons or tournaments *before* the test period.
  - Kalshi snapshots are taken at fixed times (T−24 h before the first tee; for season-long conference markets, one pre-registered date).
  - Field size, cut rules and no-cut events change E[count] and must be matched.
- **Settlement/rules risk.**
  - Tie rules vary per series and can change per event, so each event's rules text must be re-read and hashed.
  - Withdrawal before tee-off settles at fair-market price; withdrawal after tee-off settles NO (D9).
  - Dead-heat series pay 1/N rounded down, so the opposite direction applies there.
- **Execution risk.**
  - Per-player premia are small (1–3¢) against spreads of 4¢ or more (e.g. 0.05/0.09).
  - Buying across the whole field pays the spread many times.
  - Only passive, zero-maker-fee execution is plausible.
  - Most such markets have zero 24-hour volume.
- **Cheapest falsification test (step 1 needs no prices).**
  - **Step 1.**
    - From 10 prior FBS seasons, compute E[number of teams with a conference record at least as good as the N-th best], for each Kalshi-listed conference and its N.
    - From at least 100 prior PGA Tour events, compute E[number of top-10 finishers including ties].
  - **Step 2.**
    - Take one read-only snapshot of every live KXNCAAF*REGTOP and KXNCAAMB*REGTOP event.
    - Take T−24 h snapshots of the next 8 KXPGATOP10 events.
    - Compute the sum of YES mids over markets with a mid of at least 3¢. This cutoff limits contamination from M4's floor effect. Compare that sum with the step-1 E[count] for the same subset of the field.
- **Kill result.** Kill if either:
  - step 1 gives E[count] − N < 0.25 for both golf top-10 and the conference top-N; or
  - in at least 70% of step-2 events, the sum of mids is within ±(½ × average spread × number of markets) of E[count], i.e. the market already prices multiplicity.
- **Result justifying deeper research.**
  - E[count] − N ≥ 0.5;
  - the sum of mids close to N rather than E[count] in at least 70% of events.
- **Capacity estimate.** Small. Conference top-N events have open interest in the hundreds of contracts, and golf top-N depth is thin. Perhaps $50–$1,000 per event across about 50–100 events a year, with very high uncertainty.

### M6 — Subsidised passive liquidity: zero maker fees plus LIP rewards in neglected markets

**Core claim:** In rewarded markets that nobody else quotes, meeting the two-sided target alone captures a subsidy larger than the adverse-selection cost.

- **Mechanism.**
  - 94% of active markets charge no maker fee.
  - 4,139 live LIP programs pay $494,770 to resting liquidity.
  - Scoring (D7):
    - the book is snapshotted each second at a random moment;
    - an order's score is size × 0.5^ticks from the Reference Price, where the Reference Price is the level holding 1/5 of the target, and scores are normalised per side;
    - **a snapshot pays only if both sides reach the target**, which is 1,000 contracts in 97% of programs;
    - payouts scale with the share of snapshots that qualified.
  - 2,015 live programs ($224k of pool) are on markets with zero 24-hour volume.
  - There, a provider who alone meets the two-sided target may capture most of a pool that would otherwise go largely unpaid.
- **Economic reason.**
  - Kalshi deliberately subsidises liquidity in new and thin markets; its regulatory filing states this purpose.
  - Professional market makers ration capital and attention toward large markets.
  - A fixed per-market pool of about $19/day is immaterial to them but large relative to a $1,000 two-sided quote.
  - In markets with no trading at all, informed flow is rare.
- **Expected manifestation.**
  - In many rewarded zero-volume markets, public books lack two-sided depth at the target (qualifying snapshots are rare).
  - A hypothetical 1,000-lot quote on each side would hold a large share of the qualifying score.
  - Hypothetical fills would be infrequent and small.
- **Required data.**
  - Incentive programs.
  - Periodic public order-book snapshots, to measure qualifying depth per side and the hypothetical share.
  - The public trade tape, to identify trades that would have filled the hypothetical order, assuming it sits last in the price-time queue.
  - Results, to mark hypothetical inventory to settlement.
- **Causal timing and look-ahead/latency risks.**
  - The share must be computed from books as observed at the time.
  - Hypothetical fills must follow queue priority.
  - Must not assume other providers will not join once a new provider appears.
- **Settlement/rules risk.**
  - Program terms are set per period and can change.
  - The help-center page and the regulatory filing differ in detail, including on eligibility; the "most regular U.S. members" eligibility wording comes only from a web-search summary and is unverified (D7).
  - Payouts below $1 are not made, and payment comes after the period.
  - **Quotes must be bona fide.** A variant that posts to be scored but never filled — cancelling on approach, or hovering at the scoring edge — is excluded as a compliance risk (§5).
- **Execution risk.**
  - **M1 is this strategy's main risk.** When news hits a neglected market, a resting 1,000-lot is the stale order someone else takes.
  - Inventory held to settlement.
  - About $1,000 of collateral per market.
  - Continuous uptime requires automated quote management and rate-limit budgeting.
- **Cheapest falsification test (read-only paper measurement).**
  - Take 30 live rewarded markets: 15 with zero volume and 15 active, stratified by category, chosen by a pre-registered random draw.
  - Snapshot their books every 60 s for one full program period.
  - Measure:
    - (a) the fraction of snapshots where both sides meet the target without the hypothetical order;
    - (b) the hypothetical share if a 1,000-lot is posted each side at the Reference Price;
    - (c) hypothetical fills from public prints, assuming last in queue, and their mark-to-settlement result.
  - Compute net = hypothetical reward − adverse selection − settlement loss, per $1,000 of collateral per week.
- **Kill result.** Kill if either:
  - net ≤ 0 in at least 60% of the 30 markets (point estimates); or
  - in the zero-volume stratum, the median hypothetical share is below 20% (already contested).
- **Result justifying deeper research.**
  - A median net of at least 0.5% per week on collateral;
  - positive in at least 60% of markets;
  - robust to a doubled adverse-selection assumption.
  - Any live test would come later and needs explicit permission.
- **Capacity estimate.** Bounded by the pools. A small participant can credibly cover about 10–50 markets, which is ≤ $100–$1,000 per week gross before adverse selection.
  - The apparent subsidy-to-capital ratio (about 2% per day if unopposed) is implausibly high.
  - That is itself the strongest hint that it is either already contested or eaten by adverse selection; the test measures both.
  - Uncertainty is very high, because per-participant scores are not public.

### M7 — Cross-series compositional coherence (many-to-one arithmetic)

**Core claim:** Separately listed series whose outcomes are deterministic functions of each other's (per-meeting decisions → yearly cut count → year-end level) are priced incoherently beyond fees, because their liquidity is fragmented.

- **Mechanism.** Some series are arithmetic compositions of others, but have different wording and separate books. The Fed example:
  - **KXFEDDECISION** — per-meeting decision buckets, mutually exclusive. A cancelled meeting counts as "maintain".
  - **KXFED** — the target-range upper bound after each meeting.
  - **KXRATECUTCOUNT** — the number of 25 bp-equivalent cuts in 2026, where a 50 bp cut counts as 2.

  With two scheduled 2026 meetings left and the year-to-date count public, the count and the level are almost determined by two per-meeting marginals. Their prices must then satisfy Fréchet-type bounds.

  Other compositions of the same kind: per-game results ↔ season win totals (KXNCAAFWINS); per-state results ↔ national totals.
- **Why this is not structural-arb repackaging.**
  - `structural_arb` locks live within one real-valued underlying, or one categorical event.
  - Here the map runs across different underlyings and is many-to-one.
  - Joint outcomes are not identified, so the result is bounds under explicit rule mappings, i.e. statistical-or-bound violations, not a RULE_DEFINED_LOCK.
  - The AAA gas and SOL equivalence lesson applies in full: rule mismatches must be resolved first (see settlement/rules risk).
- **Economic reason.**
  - Liquidity is fragmented across series.
  - Market makers specialise by series, and retail trades the headline series.
  - Enforcing coherence needs a joint model and multi-leg execution, which lets violations survive in the "derived" series with less liquidity.
- **Expected manifestation.** Violations of the composition bounds that exceed fees plus spreads, concentrated in the derived series (e.g. wide KXFED quotes, and floor-priced RATECUTCOUNT tails).
- **Required data.**
  - Synchronous books for all component and derived series, using the structural-arb timing discipline (maximum leg skew and book age).
  - The rules and terms of each series, hashed.
  - The FOMC calendar and the year-to-date decisions.
- **Causal timing and look-ahead/latency risks.**
  - Snapshots must be synchronous.
  - All series close between 18:55 and 18:59 UTC on decision day. No post-statement data may be used.
- **Settlement/rules risk. This decides the test.**
  - Inter-meeting cuts count in RATECUTCOUNT ("starting Jan 1 … before 2027") but have no KXFEDDECISION market.
  - Hikes enter the level but not the cut count.
  - A cancelled meeting counts as "maintain".
  - "Upper bound published on the Fed's website" versus the statement.

  Every one of these must be mapped with the common-determination standard before any bound is computed.
- **Execution risk.**
  - Multi-leg, on thin derived books (e.g. KXFED quoted 0.60/1.00).
  - Joint legs cannot be filled atomically.
- **Cheapest falsification test.**
  - Terms review first (price-free): if any mismatch listed above cannot be bounded, kill.
  - Then take read-only synchronous snapshots of the three Fed series at three pre-set times before each of the next 2 FOMC meetings (6 snapshots).
  - Compute the Fréchet bounds for P(count ≥ k) and P(upper bound ≤ x) from the per-meeting marginals, and record any executable violation after fees with at least 10 contracts of depth.
- **Kill result.** Kill if the rules cannot be mapped unambiguously, or if no violation larger than fees plus spread appears in any of the 6 snapshots.
- **Result justifying deeper research.**
  - Violations of at least 3¢ after fees at 10 contracts or more, in at least 2 of the 6 snapshots;
  - with an unambiguous rule mapping.
- **Capacity estimate.** Very low: about 8 decision cycles a year, on thin derived books. Perhaps $0–$500 per cycle.

### M8 — Contingency-state settlement: fixed-value fallback payouts in rare states

**Core claim:** Where a contract pays a fixed value in a rare non-completion state (not a refund-like "fair price"), prices that ignore that state, or treat it as void, are biased by P(state) × (fixed payout − price).

- **Mechanism.** Contracts define non-standard payouts for rare states. Examples:
  - **T20 cricket:** a tie, no-result, abandonment or pre-match forfeit settles *all markets at $0.50*.
  - **Golf:** withdrawal after tee-off settles NO. Before tee-off, winner markets settle NO and finishing-position markets at fair-market price.
  - **FOMC:** a cancelled meeting settles "maintain" as YES.
  - **Refund-like cases:** a soccer game cancelled or rescheduled beyond 48 h, and missing weather data, both settle at "fair price" / "last fair price". So does an NFL player who is active but takes no snap (fair price before game start).

  (Postpone/cancel wording appears in 18,836 markets across 396 series, fair-value wording in 14,179 across 294 — both upper bounds. Recent scalar settlements include a T20 no-result at 0.50/0.50 and an abandoned USL game split three ways.)

  "Fair price" fallbacks roughly behave like refunds and offer little edge. **Fixed-value** fallbacks ($0.50, NO, "maintain" YES) change fair value by P(state) × (fixed payout − price).
- **Economic reason.**
  - Rare states are neglected.
  - *Hypothesised* anchoring to reference venues where the same state is **void** (stakes returned) — e.g. sportsbook cricket match odds on a no-result.
  - A 90¢ favourite in a match with a no-result probability q is worth about 0.9 − 0.4q on Kalshi. It is not 0.9.
- **Expected manifestation.** Where q is material (rain-affected cricket seasons, certain venues), Kalshi favourites trade close to void-anchored prices instead of contingency-adjusted ones.
- **Required data.**
  - Public historical no-result/abandonment rates by league, venue and month (Cricinfo, Cricbuzz).
  - Kalshi books at T−1 h (step 2).
  - Optionally, sportsbook prices.
- **Causal timing and look-ahead/latency risks.**
  - q must be estimated from pre-period seasons only.
  - Pre-match weather forecasts are allowed only with their publication timestamp.
- **Settlement/rules risk.**
  - Definitions of "insufficient play" and results decided by the Duckworth–Lewis–Stern (DLS) method.
  - Kalshi discretion in states the rules do not cover (D4).
  - Per-event rules text can differ.
- **Execution risk.**
  - Minor-league cricket books are often empty (e.g. quotes of 0.04/0.95).
  - The trade is to sell the favourite (buy NO) when q is high.
- **Cheapest falsification test (step 1 needs no prices).**
  - **Step 1:** compute q per Kalshi-listed cricket league from the previous 3 seasons of public results.
  - **Step 2:** only for leagues with q ≥ 5%, take T−1 h snapshots of the next 30 matches and compare favourite prices with the contingency-adjusted value implied by the void-anchored price.
- **Kill result.** Kill if either:
  - q < 2% in every listed league, which caps the mispricing at 0.8¢ for a 90¢ favourite — below typical spreads; or
  - in step 2, the adjusted-versus-traded gap is below fees plus half the spread in at least 60% of matches.
- **Result justifying deeper research.** q ≥ 5% in at least one listed league, and a gap of at least 2¢ after fees in at least 60% of that league's observed matches.
- **Capacity estimate.** Tiny, because the relevant books are thin: perhaps $0–$300 per month. Its main value may be as a **risk overlay** for M1 and M5.

### M9 — Cross-venue clientele segmentation on the same proposition

**Core claim:** Segmented capital and clienteles leave strictly equivalent propositions on Kalshi and another US-accessible venue priced apart by more than two-venue costs, for long enough for a slow participant.

- **Mechanism.**
  - The same proposition trades on segmented venues:
    - Kalshi (US, USD);
    - Polymarket US (a CFTC-designated contract market with its own book, taker-only fee, open to US residents in most states);
    - Polymarket International, which is view-only for US persons.
  - Their clienteles differ, capital cannot move instantly (pre-funding, KYC, deposit rails) and fees differ.
  - Published work reports persistent deviations of 2–4% on average between semantically equivalent markets after execution costs (third-party, context only).
- **Economic reason.**
  - Limits to arbitrage: segmented capital, legal access that varies by state, position limits, and — above all — **non-equivalent settlement rules** (source, deadline, definition).
  - Clientele effects: partisan or regional skews differ by venue.
- **Expected manifestation.** Two-venue executable edges above both venues' fees, which persist for minutes to hours, concentrated in less liquid or politically charged propositions.
- **Required data.**
  - Synchronous books on both venues (public).
  - Both rulebooks and the full contract text for each pair.
  - A strict equivalence review for each pair, using the structural-arb common-determination standard: same source, same deadline to the minute, same definition, same fallback.
- **Causal timing and look-ahead/latency risks.**
  - Snapshots must be synchronous, and each leg's latency counts.
  - Rebalancing capital takes days; there is no mid-trade funding.
- **Settlement/rules risk. This is the dominant risk.**
  - Two Kalshi series (AAA gas, SOL) already failed equivalence in this project.
  - Across venues, source and deadline differences are documented. One example: Kalshi funding markets closing at 10:00 AM ET versus Polymarket's 11:59 PM ET.
  - The observed "deviation" may be the fair value of the rule difference.
- **Execution risk.**
  - Two venues must be pre-funded.
  - Legging risk; different tick grids and fees; state-level availability.
  - Public cross-venue scanners already exist, so competition is visible.
- **Cheapest falsification test (step 1 needs no prices).**
  - **Step 0:** confirm this participant's legal access to Polymarket US in their state. Without it, kill.
  - **Step 1:** equivalence review of the top 50 overlapping propositions by Kalshi volume.
  - **Step 2:** for pairs that pass, take read-only synchronous snapshots 3 times a day for 2 weeks, and record the executable two-leg edge after both venues' fees at 10 contracts or more, and how long it lasts.
- **Kill result.** Kill if any of:
  - no legal access;
  - fewer than 10 strictly equivalent pairs;
  - net edge ≤ 0 in more than 90% of snapshots;
  - positive edges last under 10 minutes (too fast for a slow participant).
- **Result justifying deeper research.** At least 10 equivalent pairs, with a net edge of at least 2¢ in at least 20% of snapshots, lasting at least 10 minutes.
- **Capacity estimate.** Moderate but competed. Only about 2% of Kalshi markets have any cross-venue equivalent (third-party estimate). Perhaps $50–$500 per equivalent pair per event, or $0–$3k per month for a small, slow participant, with high uncertainty.

### M10 — Combo (parlay) RFQ quoting: dealer margin on correlated legs

**Core claim:** Combo requesters pay a premium over fair joint probability that a small member can collect by quoting RFQs.

- **Mechanism.**
  - Combos exist only through RFQs.
  - RFQs are broadcast to all members; "any other Member … may choose to respond" (D5, D6). The requester can accept only the best quote.
  - The quoter confirms within 3 s, and orders execute after 1 s: every combo is a High Volatility Market.
  - Retail parlay demand is widely held to be biased (lottery preference, neglect of leg correlation).
  - Kalshi additionally shares combo fees with leg market makers through a sports-prop program.
- **Economic reason.** Uninformed, high-demand requesters pay a margin to whoever quotes, and pricing that margin needs a correlation model and infrastructure.
- **Expected manifestation.** Executed combo prices above fair joint probability; the realised YES frequency below traded prices.
- **Required data.**
  - Observational: the public tape of executed combo prints, the market objects (`mve_selected_legs`), leg prices at execution time, and results.
  - Quoting side: the authenticated `communications` channel. This is out of scope in this phase (no credentials).
- **Causal timing and look-ahead/latency risks.** Leg prices must be taken at the combo's execution time (1 s timer), never settled leg prices.
- **Settlement/rules risk.**
  - Leg voids and fair-price legs produce scalar combo settlements (39 of 5,000).
  - Multi-leg rules text.
- **Execution risk (structural).**
  - Quotes are private, sealed and best-price-wins.
  - A small quoter is filled **only when its quote is the most generous** of all quoters, including professional dealers with better correlation models. That is a winner's curse by construction.
  - Most RFQs are never executed: all 5,000 recent settled combos had zero volume.
  - Needs authenticated real-time infrastructure.
- **Cheapest falsification test (observational, public).**
  - Take 1,000 executed combo prints whose legs are all in **different games**, where independence is defensible.
  - For each, compute the traded premium over the product of leg mids at execution time.
  - After settlement, compare realised frequency with traded prices.
- **Kill result.** Kill if the median premium ≤ 0, or if the realised frequency ≥ traded price.
- **Result justifying deeper research.** A premium of at least 10% of price, with a realised frequency consistent with the independence product.

  Even that would show only that *professional* quotes carry a margin. It would not show that a small quoter can win RFQs profitably (see §6).
- **Capacity estimate.** The flow is large (13% of prints in the tape sample), but the small participant's share is plausibly zero, because winning requires outbidding professional dealers. $0 to about $2k per week, with very high uncertainty.

---

## 3. Independence notes (closest pairs)

| pair | why they were kept separate |
|---|---|
| M1 vs M2 | M1 is an outcome already fully determined and public, where the edge is taking stale orders. M2 is an outcome not yet determined, where the edge is a mis-modelled conditional distribution; it exists even with fresh quotes. Running extremes that have already crossed the strike were moved to M1. |
| M2 vs M3 | M2 is accumulation over time within the correct measurement. M3 is using the wrong measurement. Different tests: M2 checks vintage-clean partial windows, M3 checks proxy-versus-source disagreement. Both can apply to a single weather market; the tests keep them apart. |
| M3 vs M5 | M3 is about which number settles the contract. M5 is about how many contracts pay, given that number. |
| M5 vs M8 | M5 covers ties within completed events (multiplicity). M8 covers non-completion states (fixed fallback payouts). They share one hypothesised channel — anchoring on reference venues — but differ in the paying state and in the test. |
| M6 vs M1 | Mirror images. M6 *provides* resting liquidity; M1 *harvests* stale resting liquidity. M1's existence is M6's main risk, so their test results should be read together. |
| M6 vs M10 | Both are liquidity provision, but M6 is a public limit order book with an exchange subsidy and scoring, while M10 is a private sealed-quote auction on bundled payoffs with a winner's curse. |
| M7 vs structural_arb | Many-to-one maps across underlyings with differently worded series. The result is bound violations, not a lock. See M7. |
| M9 vs M5/M8 | M9 needs a second venue and rests on capital segmentation. M5 and M8 need no second venue, and their bias can be computed from Kalshi's rules alone. |
| M4 vs M5 | M4's floor effect inflates the sum of prices over a field, which runs against M5's multiplicity underpricing. M5's test excludes markets priced below 3¢ for that reason. |

## 4. Comparison matrix (qualitative; no score, rank or winner)

| # | Strength of causal mechanism | Likely competition | Data quality | Execution difficulty | Capacity | Falsification cost / time | Biggest reason the edge could be fake |
|---|---|---|---|---|---|---|---|
| M1 stale orders after determination | Strong: exchange halt is manual; free options exist | High in liquid sports; unknown in the long tail | Good for trades (µs); **hard** for independent determination timestamps | High (latency race, closes mid-order) | Low–unknown, possibly zero | Moderate: ~100 games; building the determination-timestamp join is the effort | Rule 5.11 cancellation beyond ±20¢, plus faster bots, leave nothing capturable at a small participant's latency |
| M2 partially realised statistics | Moderate–strong: arithmetic of windows plus inattention | Low in neglected series; high in BRTI's last 60 s | Mixed: depends on source vintage availability | Moderate (thin books, spreads) | Low | Low–moderate: 20 windows; the model is fixed | Spreads and depth in neglected series exceed any modelled gap, and the "near-certain" side is less certain than the model says |
| M3 measurement ≠ proxy | Moderate: documented proxy use and a recent source change | High in weather | Good (settlement values via `expiration_value`; free archived proxies) | Moderate | Low–moderate | **Low**: step 1 needs no prices, about a day of work | Divergence is either unsigned noise or already priced by specialist weather traders |
| M4 grid floor at tails | Strong as a constraint; weak as an edge (demand may be rational) | Moderate (a well-known bias; calibration papers exist) | Good (history plus results); depth history thin | Low per trade, but a capital and tail problem | Opportunity-rich, capital-bound | Low: one historical pass | True tail frequencies are about 1% (the floor is not binding), or correlated tail clusters wipe out the edge |
| M5 tie multiplicity | Strong where the rules say "including ties" or "all tied teams" | Low–moderate (niche, thin markets) | Good: public standings and leaderboards; Kalshi snapshots | Moderate–high (spreads larger than per-player premium) | Low | **Low**: step 1 needs no prices | Ties at the cutoff are too rare (E[count] − N small), or prices already reflect them |
| M6 LIP plus zero maker fee | Strong: explicit subsidy with a documented purpose | Unknown (per-participant scores not public) | Good for books and programs; per-participant shares unobservable | High (continuous quoting, uptime, inventory) | Low–moderate (pool-bound) | Moderate: one program period of read-only books | Adverse selection (M1 from the other side) and hidden competitors absorb the subsidy; eligibility or terms change |
| M7 cross-series composition | Moderate: fragmentation plus multi-leg cost | Moderate (macro specialists) | Good (synchronous public books) | High (multi-leg, thin derived books) | Very low | Low: 6 snapshots over 2 meetings, plus a terms review | Rule mismatches (inter-meeting moves, hikes, cancellation) make the "violation" the price of a real difference |
| M8 fixed-value contingencies | Moderate: rare-state neglect; anchoring is a hypothesis | Low | Good for historical contingency rates; books often empty | Moderate–high (empty books) | Very low | **Low**: step 1 needs no prices | Contingency rates are too low (q < 2%) to matter against spreads |
| M9 cross-venue segmentation | Moderate: limits to arbitrage are documented | Moderate–high (public scanners) | Good (both books public); equivalence review is manual | High (two venues, pre-funding, legging) | Moderate | Moderate: equivalence review plus 2 weeks of snapshots | Deviations are the fair price of settlement-rule differences, not mispricing |
| M10 combo RFQ quoting | Moderate for requester overpayment | High (professional dealers) | Observational only; the quoter side needs authentication | Very high (real-time authenticated quoting, 3 s confirmation window) | Plausibly zero for a small quoter | Moderate (tape plus leg reconstruction), and does not answer the small-quoter question | Winner's curse: a small quoter is filled only when it is the most generous quote |

## 5. Considered and excluded (not among the ten)

| idea | reason for exclusion |
|---|---|
| Trading scheduled economic releases after publication | **Fatal:** these markets close before the release (e.g. KXPAYROLLS closes at 8:29 AM ET on release day). There is no window. |
| Integer or discrete-support "duplicates" (e.g. "above 70.5" ≡ "≥ 71" for integer-reported data) | Repackages structural-arb R4 under a looser, unverified assumption about the support. The frozen protocol deliberately treats X as real-valued unless the terms verify otherwise. |
| Time decay against static quotes in "by date X" markets | Stale resting orders (M1's economic reason) plus a statistical hazard model. Not independent. |
| Single-venue lead–lag (Polymarket International as a signal) | Stale-quote logic (M1) and correlation-driven. Not independent. |
| Perp funding or basis carry | Not an event-contract inefficiency; generic leveraged crypto carry. |
| Hedging-pressure risk premia (weather/recession "insurance") | Compensation for risk, not an inefficiency. |
| Fan or partisan sentiment bias, generic favourite–long-shot calibration, technical analysis | Excluded by the brief. |
| Rule-text drift between events of a series | A trigger for M3 (a proxy habit lagging a rule change), not a separate mechanism. |
| Quoting for LIP score only (orders intended not to fill) | Compliance risk (bona fide order requirements). M6 covers bona fide two-sided quoting only. |
| RFQ last look on standard (non-combo) markets | Untestable without authentication, and the requester controls acceptance. Usage is likely negligible. |

## 6. Recommended immediate rejections (reviewer's decision)

- **M10 — reject as a small-participant strategy, without testing.**
  - The structural problem is fatal for this participant profile. Quotes are private, sealed and best-price-wins, so a small quoter is filled only when its price is the most generous among all quoters, including dealers with better models of leg correlation. That selection happens by construction, not as an empirical question.
  - Operating it also needs authenticated real-time infrastructure, which is out of scope here.
  - The public observational test can show whether *requesters* overpay. It cannot show that a small participant would win those RFQs, so no cheap result could justify deeper work.
- **Not rejected, but carrying a structural cap to keep in mind:**
  - **M1:** Rule 5.11 limits any safely capturable edge to the ±20¢ band. The kill test is defined inside that band, so gains beyond it are treated as unavailable.
  - **M9:** gated on the participant's legal access to Polymarket US in their state (step 0). If there is no access, M9 dies without further work.
- **No other mechanism has a structural problem fatal enough to reject it before its cheapest test.**
  - M3, M5 and M8 each begin with a price-free step 1 that is likely to settle them cheaply either way.

## 7. What this document does not claim

- It does not claim that any mechanism is profitable.
- The plausibility evidence is structural only: rules text, market design, prevalence and incentives. It does not come from outcomes.
- Capacity figures are order-of-magnitude bounds on *opportunity*, not forecasts.
- All tests above are specifications only. Nothing has been implemented; any collector, snapshotting or historical pass requires approval first.
