# Structural Pricing Inconsistency Scanner — Research Design

Status: **DRAFT, awaiting stronger-model validation of §1 (math) and §3 (false-arb modes)
before any relationship code is written.** This is a research project that only reads data.
It does not trade. It starts from the null hypothesis that **no executable structural
arbitrage exists** on Kalshi once fees, spreads, depth, contract rules and timing are
accounted for. The goal is to test that null, and negative results are first-class outputs.

## 0. Isolation guarantees (H022 / H038)

* H022 and H038 are **not in this repository**. No file, branch or commit in
  `oskaryouth-glitch/Kalshi-Quant-TeleBot` mentions them (checked with `git log --all` and a
  full-text grep). Their code, collectors, data and frozen rules live somewhere else, and this
  project never refers to that location.
* All code for this project lives under `research/structural_arb/`. It imports **nothing** from
  `src/` or `telegram_ui/`, and it changes no file outside that directory.
* Raw data goes to `research/structural_arb/data/`, which git ignores. It has its own file
  prefix (`sarb_`), so it cannot collide with any other experiment's data.
* **No credentials.** The HTTP client (`sarb/client.py`) sends only unauthenticated `GET`s to
  public paths on an allowlist: `/series`, `/events`, `/markets`, `/markets/{t}/orderbook`
  and `/exchange/status`. It has no code path for POST, PUT or DELETE. It never reads
  `KALSHI_API_KEY` or any private key, and it never sends an `Authorization` header.
  Tests enforce all of this.

## 1. Mathematical relationships to test (PROPOSED — to be validated)

Notation. A binary contract `m` pays $1 per YES contract if event `E_m` occurs, and $1 per NO
contract otherwise. Kalshi order books show **bids only**:

* executable YES ask = `1 − (best NO bid)`
* executable NO ask = `1 − (best YES bid)`

For size `C`, `cost_side(m, C)` means walking the book: the VWAP of the opposite side's bids,
turned into asks, multiplied by `C`. `fee(P, C)` is the taker fee for each fill (§2.3). Every
candidate is a **portfolio of taker buys**. Each is scored by
`locked_payoff = min over states s of payoff(s)` and
`edge = locked_payoff − Σ cost − Σ fee`. "Guaranteed" means `edge > 0` in **every** state
that the settlement rules allow, and those states include voids and cancellations.

Every relationship is also checked independently by a **state-space verifier**. The verifier
builds the atoms of the underlying's outcome space from every strike involved. It writes each
leg as a 0/1 payoff vector over those atoms and checks `min_s payoff(s)` by brute force. A
template is trusted only if the verifier agrees with its closed form on randomized tests.

### R1 — Mutually exclusive and exhaustive (MEE) buckets
Contracts `m_1..m_n` such that exactly one `E_i` occurs in every allowed state.
* **Long basket**: buy 1 YES of each. The payoff is exactly 1.
  Edge = `1 − Σ yes_ask_i − Σ fee_i`.
* **Short basket**: buy 1 NO of each. The payoff is exactly `n−1`.
  Edge = `(n−1) − Σ no_ask_i − Σ fee_i`, which equals `Σ yes_bid_i − 1 − Σ fee_i`.
* If the set is only mutually exclusive (zero winners are possible), the NO basket still locks
  in at least `n−1`, but the YES basket is **not** guaranteed. It is then classed as a
  statistical relationship.

### R2 — Nested thresholds (monotonicity)
Same underlying `X`, same observation time and source, with `E_B ⊆ E_A`. An example is
`X ≥ B ⇒ X ≥ A` for `A < B`, including the case of equal strikes where `>` is inside `≥`.
* Portfolio: YES_A + NO_B. The payoff is 1, 2 or 1 across the three regions, so it is at
  least 1. Edge = `yes_bid_B − yes_ask_A − fees`. That is, the contract that should be
  cheaper bids more than the ask on the contract that should be dearer.
* "Below" contracts (`X < K`) are mapped onto the same interval representation, and not
  handled as a separate case.

### R3 — Ranges and thresholds (probability mass)
Buckets that partition part of the line, with a threshold `T = ⋃_{i∈S} bucket_i`
(for example `X ≥ L_k = ⋃_{i≥k} [L_i, U_i)`).
* (a) YES on every bucket in S + NO_T. Locked payoff 1.
  Edge = `yes_bid_T − Σ_{i∈S} yes_ask_i − fees`.
* (b) YES_T + NO on every bucket in S. Locked payoff `|S|`.
  Edge = `Σ_{i∈S} yes_bid_i − yes_ask_T − fees`.
* A single range against two thresholds: `[A,B) = {X≥A} \ {X≥B}`. This is the same algebra
  with `|S| = 1` on the other side.
* The general case is an LP over the atoms: choose non-negative quantities of YES/NO buys to
  maximise `min_s payoff(s) − cost − fees`. R1–R3 are the auditable special cases. The LP is
  an optional cross-check, and never the primary detector.

### R4 — Duplicate / economically equivalent contracts
Two markets `m`, `m'` with `E_m = E_{m'}` in **every** allowed state. That requires the same
underlying, source, observation timestamp, strike, strictness, rounding convention and
void/cancellation rule.
* YES_m + NO_{m'} locks in payoff 1. Edge = `yes_bid_{m'} − yes_ask_m − fees`, checked in
  both directions.
* Complementary pair, where `E_{m'} = ¬E_m`: YES_m + YES_{m'} locks in payoff 1.
* If equivalence cannot be **proven** from the rules, the pair is logged as `STATISTICAL`
  and never as arbitrage.

### R5 — Combination (AND) markets vs. components
A combo `c` with `E_c = E_A ∧ E_B`. The legs must be verified to be the same contracts with
the same settlement.
* Upper (Fréchet) bound, `P(c) ≤ P(A)`: YES_A + NO_c locks in payoff 1.
  Edge = `yes_bid_c − yes_ask_A − fees`.
* Lower bound, `P(c) ≥ P(A)+P(B)−1`: YES_c + NO_A + NO_B locks in payoff 1.
  Edge = `1 − yes_ask_c − no_ask_A − no_ask_B − fees`.
* **Caveat.** Kalshi multivariate/combo markets may be quote-based (RFQ) and show no
  orderbook. If there is no displayed executable depth, R5 cannot be tested. That result is
  recorded as a finding, and no depth is ever assumed.

### Not arbitrage (logged separately as `STATISTICAL`)
These are logged with their raw inconsistency size, but they are never scored as locked
payoff:
* related-but-not-nested contracts, such as different stations, observation times or data
  vintages
* hourly vs daily index settlement
* anything that relies on correlation

## 2. Data required

| Data | Endpoint | Used for |
|---|---|---|
| Series metadata: `fee_type`, `fee_multiplier`, settlement sources, `contract_url` | `GET /series/{t}` | fees, source equivalence |
| Scheduled fee changes | `GET /series/fee_changes` | the fee in force at snapshot time |
| Events with nested markets, `mutually_exclusive` | `GET /events?with_nested_markets=true` | building R1/R3 sets |
| Market rules: `rules_primary/secondary`, `strike_type`, `floor_strike`, `cap_strike`, `custom_strike`, `expiration_time`, `close_time`, `can_close_early`, `status`, tick/price structure | `GET /markets`, `GET /markets/{t}` | settlement equivalence, interval mapping |
| Full orderbook depth (YES bids, NO bids) | `GET /markets/{t}/orderbook` | executable prices, depth walk |
| Exchange trading status | `GET /exchange/status` | reject when halted |
| Local timestamps: request-sent and response-received (UTC + monotonic) for every leg | client | skew and staleness gating |

**Historical data caveat.** Kalshi publishes historical trades and candlesticks, but no
historical order-book depth. Executable structural inconsistencies therefore **cannot be
backtested**. They can only be measured by forward collection of snapshots. Trade prints or
candles may be used to generate hypotheses, but never as evidence of executability.

### 2.3 Fees (to be audited)
* Taker: `fee = roundup(M × 0.07 × C × P × (1−P))`, with a series multiplier `M`.
  `fee_type ∈ {quadratic, quadratic_with_maker_fees, flat}`.
* Maker: `0.0175` coefficient on maker-fee series. It is not used, because every detector
  leg is a taker.
* Rounding unit: the public fee schedule has historically said "rounded up to the next cent".
  A secondary source says the 2026 schedule rounds **fee + position cost up to a centicent**
  (1/100 of a cent). That could not be verified here because the environment blocks
  kalshi.com. The implementation therefore keeps the rounding rule configurable and defaults
  to the **conservative** option: round up to a whole cent for each leg and each order. This
  overstates fees, which biases the scanner against finding arbitrage. The size of each
  candidate's result under the alternative rounding rule is logged.
* Settlement: no settlement fee is assumed. This must be confirmed.

## 3. How a false arbitrage can appear (each has a guard)

1. **Asynchronous legs.** REST books for different legs are fetched at different times. Guard:
   record send/receive timestamps for every leg; reject if `max(recv) − min(sent)` exceeds a
   skew limit; require the same opportunity on an **immediate re-fetch**, with the
   persistence duration recorded.
2. **Stale or derived fields.** `yes_ask` and `last_price` on `/markets` can lag the book.
   Guard: prices come **only** from `/orderbook` levels. Mids are never used.
3. **Too little depth.** The top of book may be 1 contract. Guard: walk the book for the
   proposed `C`; record the VWAP and the maximum `C` at which edge > 0.
4. **Fee rounding at small size.** `ceil` makes 1-lot legs expensive, so the scanner scores
   each candidate at several sizes `C`. This is a fixed grid, not optimized.
5. **Incomplete MEE sets.** Causes: tail or "other" buckets missing; strikes Kalshi adds
   during the day; markets closed or settled inside the event; `mutually_exclusive`
   mis-set; a "no winner" outcome. Guard: require complete coverage of the outcome space,
   proven from strikes. Otherwise downgrade to "ME-only" or statistical.
6. **Strike boundary semantics.** Examples: `>` vs `≥`; "50–51" meaning `[50,51)` vs
   `[50,51]`; the underlying reported rounded, such as integer °F or CPI to 0.1; gaps
   between buckets. Guard: explicit interval mapping plus the reporting precision. If the
   mapping is unknown, the candidate is rejected.
7. **Settlement non-equivalence.** Different source, station, time or data vintage; different
   revision policy; `can_close_early`; different expiration. Guard: an equivalence check that
   must prove equality field by field. Anything unknown means "not equivalent".
8. **Void, cancellation or fallback rules** create extra states in which the locked payoff
   fails. Guard: the rules text is kept alongside every candidate. The payoff under void is
   checked where the rules define it.
9. **Non-atomic execution (leg risk).** Kalshi has no multi-leg atomic orders. Displayed depth
   can be cancelled, and your own first fill moves the market. The scanner reports the
   theoretical edge **and** how long it persisted. A "guaranteed" label means guaranteed
   *if all legs fill at the displayed prices*, and the report says so.
10. **Market state.** Market status is not `active`, the exchange is halted, or trading is
    paused. Guard: reject the candidate.
11. **Capital and limits.** Collateral is locked until settlement, which has an opportunity
    cost. Position limits apply. The scanner records days-to-settlement and the annualised
    edge, and does not treat edge as free money.
12. **Multiple testing and data errors.** Thousands of comparisons will produce some glitches.
    Guard: persistence plus re-fetch confirmation. Each positive is investigated before it is
    believed.
13. **Look-ahead.** Only rules and metadata as published at snapshot time are used. Outcomes
    are never used to decide classification.
14. **Tick and precision.** Subpenny levels and fixed-point contract counts are handled with
    `Decimal`, never with floats.

## 4. Test architecture

```
research/structural_arb/
  DESIGN.md                this document
  README.md                how to run, safety notes
  sarb/
    client.py              GET-only, public-path allowlist, no auth, timing capture, rate limit
    models.py              dataclasses: MarketMeta, BookSide, OrderBook, BookSnapshot, Leg, Candidate, Evaluation
    orderbook.py           normalize API formats → Decimal levels; derive asks; depth walk / VWAP / max size
    fees.py                fee schedule model (fee_type, multiplier, rounding mode), conservative default
    timing.py              skew / staleness gates
    payoff.py              state-space verifier (atoms, payoff vectors, min payoff) — independent checker
    contracts.py           [AFTER CHECKPOINT] strike_type → interval mapping, equivalence proof
    relationships/         [AFTER CHECKPOINT] r1_mee, r2_monotone, r3_ranges, r4_equivalent, r5_combo
    evaluator.py           [AFTER CHECKPOINT] candidate + snapshots → Evaluation (pass/fail reasons)
    research_log.py        append-only JSONL log of EVERY candidate, pass or fail
    collector.py           discovery + snapshot loop → data/sarb_snapshots_*.jsonl.gz
    report.py              aggregates: counts by relationship × rejection reason, edge distributions
  tests/                   pytest; every relationship tested against the brute-force verifier
  data/                    git-ignored
```

The status assigned to each candidate is one of:
* `GUARANTEED_STRUCTURAL_EXECUTABLE`: all gates pass; edge > 0 after fees at size ≥ 1.
* `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE`: the displayed prices are inconsistent, but the
  candidate fails on fees, depth, timing or persistence.
* `STATISTICAL`: the relationship relies on correlation and has no locked payoff.
* `REJECTED_*`, with specific reasons: `STALE`, `SKEW`, `INCOMPLETE_SET`,
  `SEMANTICS_UNVERIFIED`, `MARKET_INACTIVE`, `NO_DEPTH`, and so on.

**No parameter tuning.** The skew limit, the size grid and the persistence re-fetch are fixed
in `config.py` before any data is looked at. They are never tuned to the results.
