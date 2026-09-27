# `position_hedge`: design only (not implemented)

Status: design document, 2026-09-27. **No code, no orders, and no change to H022, H038 or their
frozen rules.** This is separate from `research/structural_arb/`: it may *import* that package
read-only, pinned to a commit, for fee and payoff math, but it must never modify it.

## 1. Question

A strategy (e.g. H022) has legitimately acquired a binary position. Can later movement in the
executable order book for the **complementary contract** create a hedge that:

* **A.** improves worst-case P&L, or
* **B.** makes P&L positive under **both** ordinary settlements (YES and NO) after all costs?

The classification is **deterministic payoff arithmetic on executable prices**. A model or AI
may *predict or rank* when such opportunities are likely, for example to set monitoring
frequency. It never decides a classification.

## 2. Setting and a key fact about Kalshi

Position: `Q` contracts of side `s ∈ {YES, NO}` in market `m`, acquired by fills
`(p_i, q_i)` with actual fees `f_i`:

    K0 = Σ p_i q_i + Σ f_i        (actual cash cost, from the strategy's own fill records)

The complementary contract in the **same market** is the opposite side. On Kalshi, a
YES bid at p is a NO ask at 1−p (docs: Orderbook Responses). Buying the opposite side while
holding a position **closes the offsetting position at execution**. Rulebook v1.29, Rule 5.3(c)(b)
(SHA-256 `3b6d4ffd…240b`, in `research/structural_arb/sources/`): "If the Transaction involves
entering into one or more Contracts for which a Self-Clearing Member has an offsetting position
… upon execution of the Trade Kalshi will … Close the offsetting position … [and] Credit those
amounts to the Self-Clearing Member Account." API docs (Market Settlement): "Only net positions
are settled".

Consequences, stated plainly:

* A same-market hedge of h ≤ Q contracts is economically identical to **selling h of the
  position**. A same-market `NORMAL_SETTLEMENT_LOCK` exists exactly when the held side's
  executable bid exceeds the cost basis plus all fees. It is a **realized gain from a
  favourable price move, not a structural mispricing.** It must not be reported as arbitrage.
* A full same-market hedge (h = Q) leaves **no open position**. It therefore also removes
  discretionary-settlement risk (Rulebook 6.3(c)/7.1), apart from Rule 5.11 trade cancellation.
  A partial hedge leaves Q − h exposed.

A **cross-market** complement (e.g. "Team A wins" vs "Team B wins" in a MECNET event, or a
threshold vs a bucket set) does *not* net. Such hedges need the structural-arb state-space
machinery: settlement-equivalence proof, envelope semantics, and extra states such as tie,
no-winner and ALL_NO. They are defined in §4 but should be phase 2 of this experiment.

## 3. Same-market equations

Let the hedge buy the opposite side `s̄`, walking the executable ask ladder of `s̄`, which is
`1 −` the bid ladder of `s`, up to quantity `h`:

    principal(h) = Σ_levels a_L · c_L(h)                 (walked asks of s̄)
    F(h)         = hedge fee (sarb.fees: exact documented algorithm per order; strict upper
                   bound when the fill split is unknown; direct $0.0001 and non-direct $0.01)
    H(h)         = principal(h) + F(h)

For h ≤ Q (the held side pays $1 in its winning state; s̄ pays $1 in the other):

    PnL_if_s  (h) = Q·1 − K0 − H(h)
    PnL_if_s̄ (h) = h·1 − K0 − H(h)
    worst(h)      = min(PnL_if_s, PnL_if_s̄) = h − K0 − H(h)        (since h ≤ Q)
    worst(0)      = −K0

For s = YES, `PnL_if_YES = PnL_if_s` and `PnL_if_NO = PnL_if_s̄`; for s = NO they swap.

For h > Q (over-hedge, the net position flips to h−Q of s̄):

    PnL_if_s  (h) = Q − K0 − H(h)
    PnL_if_s̄ (h) = h − K0 − H(h)

The same formulas apply, but the flipped exposure is reported, and it is never needed for a
lock.

Using `ā(h) = principal(h)/h` (the average hedge ask), `b̄(h) = 1 − ā(h)` (the equivalent
average exit bid) and `c0 = K0/Q`:

* Full hedge: `PnL_if_s(Q) = PnL_if_s̄(Q) = Q·(b̄(Q) − c0) − F(Q)`.
* **Lock condition**: `b̄(Q) > c0 + F(Q)/Q`. The walked bid must exceed the all-in cost basis
  plus hedge fees. With h < Q, `PnL_if_s̄(h) = h(b̄(h) − 1) + h − K0 − F(h)` is at most
  `PnL_if_s̄(Q)`, so the smallest locking h is found by search, not assumed to be Q.
* Worst-case improvement: `worst(h) − worst(0) = h·b̄(h) − F(h)`. This is positive whenever the
  walked bid exceeds the fee per contract, so **almost any partial exit is "risk-reducing"**.
  The report must therefore always show the price paid for it in the favourable state:
  `ΔPnL_if_s(h) = −H(h)`.

### Quantities computed for every candidate h (integers 1 … min(depth, H_MAX))

| Field | Definition |
|---|---|
| `PnL_if_YES`, `PnL_if_NO` | as above, mapped by side |
| `min_PnL` | min of the two |
| `hedge_principal`, `hedge_fees` (per scenario) | walked principal, and fees under `direct_expected`, `direct_bound`, `nondirect_conservative` |
| `total_fees` | original fees Σf_i + hedge fees |
| `additional_capital` | for h ≤ Q: none is locked up. Under Rule 5.3(c)(b) an offsetting trade closes the position and credits funds; the maximum-loss funds check in 5.3(c)(a) applies to *non-offsetting* orders. Reported conservatively as `principal + fee` gross debit, with the net `principal + fee − h·$1`. For h > Q, the flipped part needs `(h−Q)` × its price plus fees, per 5.3(c)(a). |
| `partial_fill_exposure` | for an IOC order that fills only h′ < h: `worst(h′)` and `PnL_if_s(h′)` for all h′. Because each order is in a single market, a partial fill is just a smaller h. |
| `unwind_cost` | cost to undo the hedge immediately (re-buy side s at its walked ask) |
| `residual_open_qty` | Q − h (exposed to discretionary settlement and 6.3(c)) |

### Classification (deterministic)

Let `S = {h : quantities computable with full displayed depth}`. Every inequality is evaluated
under the **conservative** fee scenario (non-direct $0.01, worst-case fill split), with the
direct-member figures reported alongside, as in structural_arb.

* `NORMAL_SETTLEMENT_LOCK` if ∃h ∈ S with `PnL_if_YES(h) > 0` **and** `PnL_if_NO(h) > 0`.
  The record gives the lock interval of h, the smallest locking h, and the h maximizing `min_PnL`.
* else `RISK_REDUCING_HEDGE` if ∃h ∈ S with `min_PnL(h) > min_PnL(0) = −K0`. The record gives
  the h maximizing `min_PnL` and the favourable-state cost `−H(h)` at that h.
* else `NO_HEDGE` (no displayed depth on the opposite side, or no h beats the fees).

A classification is valid only if the book passes the structural_arb data gates:
* HTTP 200, not crossed or locked, no CDN cache hit;
* market `active` and not closed;
* book age ≤ 5 s;
* fee type resolvable, using the fee ledger for event overrides.

It is **confirmed** only if it persists on an independent re-fetch after 1 s. The Rule 5.11
check (hedge VWAP within ±$0.20 of the last trade) is recorded as in structural_arb.

## 4. Cross-market complements (phase 2)

The held position and the hedge legs are positions on markets in a proven family (numeric
envelope, or MECNET categorical), using `sarb.semantics` / `sarb.payoff` read-only. For every
rule-defined state σ (including ties, no-winner and ALL_NO where the terms say so):

    PnL_σ(h⃗) = Q·pay_σ(s,m) + Σ_j h_j·pay_σ(leg_j) − K0 − Σ_j H_j(h_j)

* `NORMAL_SETTLEMENT_LOCK` requires `PnL_σ > 0` for **every** rule-defined σ, not just two.
  With more than two states the name is kept, but the record lists every state.
* Legs are separate orders, so the structural_arb leg-risk and unwind metrics apply. There is
  no netting across markets, and capital is the full sum of hedge principal and fees until
  settlement.
* Settlement-equivalence and terms verification rules are exactly those of structural_arb.
  Without a verified family, cross-market results are `STATISTICAL` and never a lock.

## 5. Data required

| Data | Source | Notes |
|---|---|---|
| Position fills: ticker, side, price, qty, fee, timestamp, order id | **Read-only export** of the strategy's own fill log (H022) | Copied after the fact. No access to H022's process, keys or storage paths. |
| Position changes over time Q(t) (adds/exits by the strategy) | same export | the hedge window ends when the strategy exits |
| Opposite-side order book (full depth) at ≥ 1 Hz while the position is open | public `GET /markets/{t}/orderbook` (unauthenticated) by a **separate** process | same timing capture as structural_arb |
| Market status, close time, last price | public `GET /markets/{t}` | for gates and Rule 5.11 |
| Fee type / multiplier at each time; event overrides | `/series`, `/series/fee_changes`, the fee ledger | sarb.fees rules |
| Settlement result and value (`result`, `settlement_value_dollars`) | public `GET /markets/{t}` after settlement | **used only for ex-post P&L attribution, never for classification** |
| The strategy's resting orders on the same market | read-only export | self-trade prevention could cancel a hedge that crosses them |

## 6. Counterfactual evaluation on prospective H022 data (without contaminating H022)

1. **No interaction.** H022 runs unchanged. The monitor places **no orders**, uses **no H022
   credentials**, and runs on a **different host/IP**. Unauthenticated rate limits may be
   per-IP and are undocumented, so collocating could throttle H022. The monitor reads only an
   append-only copy of H022 fills, synchronised one way.
2. **Pre-registration before any hedge data is seen.** A small fixed set of policies, frozen
   in a versioned config:
   * `P0`: hold (H022 as executed; this is the baseline and is H022's own result);
   * `P1`: at the first *confirmed* conservative `NORMAL_SETTLEMENT_LOCK`, execute the
     smallest locking h;
   * `P2`: at the first confirmed lock, execute the h maximizing `min_PnL`;
   * `P3`: a risk-reduction policy with a fixed, pre-declared trigger (e.g. the first time
     `worst(h*) − worst(0) ≥ x·K0` for one pre-registered x).

   There is no tuning of triggers on outcome data. Any change creates a new policy version,
   evaluated only on later data.
3. **Execution realism.**
   * A hypothetical hedge decided at snapshot t executes against the **next** snapshot's book
     (≥ one observed latency later).
   * It walks displayed depth using IOC semantics: partial fills are allowed and recorded.
   * Fees follow the direct-member algorithm, with the conservative case also reported.
   * If H022 itself traded in that market between t and t+latency, the available depth and Q
     are adjusted from H022's fills.
   * Rule 5.11 exposure is recorded.
4. **Attribution.**
   * For each position: `ΔPnL_policy = PnL_policy − PnL_P0`, using the actual settlement
     result, including scalar settlements. For scalar settlements the unhedged remainder earns
     the actual `settlement_value`.
   * Statistics are paired, per position (block bootstrap over days), and report mean,
     median, worst case, variance and drawdown of ΔPnL.
   * Correction for the small fixed number of policies.
5. **Separation of results.** H022's primary result is computed exactly as H022 defines it,
   from H022's own fills, and is never recomputed with hedges. Hedge results are a clearly
   labelled secondary analysis in a separate report, and all positions are included (no
   cherry-picking).
6. **Look-ahead guards.** Classification uses only data with receive time ≤ decision time.
   Settlement data is joined only in the attribution step. Model or AI rankings may be trained
   only on data strictly before the evaluation window, and are evaluated separately
   (calibration of "a lock will appear within τ").

## 7. Execution risks and unresolved items

* **Latency / book movement.** Displayed bids can vanish. Only persistence-confirmed
  classifications count, and the counterfactual uses the next snapshot.
* **Buying-power check**: Rule 5.3(c) describes the funds check only for non-offsetting
  orders, and immediate close-out for offsetting ones. That text is written for Self-Clearing
  Members; whether the owner's direct retail account follows the same processing is UNRESOLVED.
  The monitor therefore reports the gross debit too.
* **Netting semantics**: to be re-verified against the current Rulebook chapter and API docs
  before implementation (the quoted rule must be pinned by hash).
* **Self-trade prevention**: a hedge crossing H022's own resting orders may be cancelled.
* **Rule 5.11**: a hedge executed far from fair value can be cancelled or adjusted.
* **Fees**: small h pays proportionally more because of rounding. Fees are computed per order,
  and the fee type can change at event level (the ledger floor applies).
* **Discretionary settlement**: applies to any unhedged remainder; a full same-market hedge
  removes it.
* **Model misuse**: a predicted probability never upgrades `RISK_REDUCING_HEDGE` to a lock.
  Locks are defined only by the inequalities in §3/§4.
* **Economic interpretation**: a same-market lock is a *realized gain*. Whether taking it
  beats holding is an expected-value question about H022's edge. This experiment measures it
  counterfactually, and must not be sold as arbitrage.

## 8. Minimal implementation plan (for later, on approval)

1. A `hedge_math.py` pure module: same-market equations, search over h, classification. It
   reuses `sarb.fees` and `sarb.orderbook` read-only, with property tests. The key properties:
   * the lock iff the walked bid exceeds cost basis plus fees;
   * `worst(h)` is monotone in the marginal bid condition;
   * scenario ordering.
2. A read-only H022 fill-export adapter (a schema contract agreed with the H022 owner, no
   access to H022 internals).
3. A separate monitor process at ≥ 1 Hz per open position, running on its own host.
4. A counterfactual evaluator and report per §6, run only after pre-registration is committed.
