# M6 paper experiment: implementation interpretations (for final reviewer approval)

These are the ten interpretations listed in `PRE_START_AUDIT.md` §4, in complete detail, plus the choices made since (section B). Each is fixed in the hash-frozen code (`PREREG_M6_PAPER.md`).

**Materiality key.** Could a reasonable alternative materially change **E**ntries, **F**ills, **R**ewards, **C**apital usage or **P**&L?

## A. The ten interpretations

### 1. Fee state used by selection (reviewer: approved provisionally)
- **Design said (v2 §4.2):** "Fee state comes from the series fee history at the epoch, plus any event override. An unknown fee state is treated as maker fees at M = 1."
- **Implementation:**
  - Selection uses only the **series-level** fee fields from `GET /series` at the epoch, with the receive time recorded. The market's series comes from `GET /events?status=open`.
  - An unknown series means maker fees at M = 1.
  - Event overrides are **not** used for selection. They are fetched per tracked market (`GET /events/{e}`, receive time recorded) and used for **fills** (see B1).
  - A fee state observed after the epoch is never used for selection.
  - Code: `selection.fee_state`, `selection.candidates` (records `fee_provenance`), `collector.epoch`.
- **Why necessary:**
  - The public events list carries no fee-override fields; this was verified live.
  - One `GET /events/{e}` per program market would be about 5,000 requests per epoch: roughly 42 min at 2 requests/s, every 6 h.
- **Alternative and materiality:**
  - The alternative is to fetch overrides for the top candidates before ranking. That would change C\* only through the maker fee on the one-side fill reserve: at most 0.0175·x·p(1−p) ≤ 0.0044·x dollars, i.e. ≤ 0.5% of C\*.
  - **E:** only at the capital boundary, and only in the rare markets with an override. **F/R:** none. **C:** negligible. **P&L:** none, because fills pay the applicable fee regardless (B1).
  - **Not material.**

### 2. Formal checkpoint across the three fill assumptions (reviewer: approved)
- **Design said (v2 §10):** "Require at least 20 completed programs per capital limit … Take the minimum over V_T, V_P and V_C." It did not say how "20 completed" applies when the variants hold different programs.
- **Implementation:**
  - A capital arm reaches its formal sample requirement only when **each** of V_T, V_P and V_C has ≥ 20 completed episodes.
  - Each variant's decision set is its own completed episodes at that checkpoint. The minimum NET decides, and variants are never pooled.
  - Code: `sim.Replay._checkpoints`.
- **Why necessary:** capital use depends on fills, so the variants can admit different programs, and their counts differ.
- **Alternative and materiality:**
  - Counting a single variant, or entries common to all three, would change **when** an arm is decided and **which** episodes form each decision set.
  - **E:** entry closure timing. **P&L:** the decision-set composition. **Material**, which is why it needed approval (given).

### 3. The V_P (proportional) cancellation-credit formula
- **Design said (§6):** "V_P | Q −= Δ·Q/(level − n)".
- **Implementation:**
  - Q −= Δ·Q/L_prev, where L_prev is the **real** level size at our price in the previous snapshot. Q is clamped at ≥ 0.
  - Code: `fills.queue_update`.
- **Why necessary:**
  - The design formula assumed the level size includes our order n.
  - A paper order is never in the real book, so the real level already excludes n. Subtracting n again would double-count and, when n ≥ level, divide by zero or a negative number.
- **Alternative and materiality:**
  - The literal level − n gives a smaller denominator, so a larger credit and more V_P fills.
  - It affects **F/P&L under V_P only**. V_P always stays between V_T (no credit) and V_C (full credit).
  - The decision uses the worst of the three, so it matters only if V_P is the worst variant, and even then only in size.
  - **Low materiality.**

### 4. Order sizes: whole contracts; fills can be fractional
- **Design said (§4.2, §5):** x15 is a size in contracts. "desired YES bid = max(0, min(x, x − q)) … A shortfall … is posted as a new order."
- **Implementation:**
  - New and replenishment orders are whole contracts (floor).
  - Public trades report fractional counts (`count_fp`, e.g. 5.41), so fills, remaining sizes and positions can be fractional. A fractional remainder is not topped up with a fractional order.
  - Code: `sim.VariantState._quote`.
- **Why necessary:** the design assumed integer contracts, but the feed is fixed-point.
- **Alternative and materiality:**
  - Fractional replenishment would add less than one contract of resting size per side, occasionally.
  - **R/F/C/P&L:** below one contract per side. **Not material.**

### 5. Reward coverage and payout SE (tightened in v3 to "no compensation")
- **Design said (§7):** "P̂ = R × (T_cov / T_period) × mean_k[(s_y,k + s_n,k)/2]. T_cov is our time in the period, excluding gaps. Gaps earn 0. … SE uses hourly batch means." (§2: "no book for > 60 s is in a gap".)
- **Implementation (v3):**
  - Coverage:
    - Each inter-poll interval of the episode counts toward T_cov **in full if ≤ 60 s and not at all if longer**.
    - The 60 s cap was chosen ex ante: at the 10 s mean poll a longer silence occurs by chance with probability e^−6 ≈ 0.25%.
    - The ~2-min selection pause and any loop stall therefore earn nothing (reviewer: no compensation).
  - Score mean:
    - It is the unweighted mean over polls. Poll times are Poisson and independent of the book, so it estimates the time average.
  - Payout SE:
    - The SE of P̂ uses clock-hour batch means.
    - With fewer than 2 batches the conservative payout is 0. Episodes last ≥ 24 h, so this never binds in practice.
  - Code: `sim.covered`, `sim.VariantState.on_poll`, `sim.payout`.
- **Why necessary:** the design did not define how a poll interval maps to covered time, or the batching clock.
- **Alternative and materiality:**
  - v2's "each poll covers ≤ 60 s" credited 60 s of every longer gap. That is about 4 × 60 s a day, i.e. **≈ 0.3% of reward time**. v3 removes it.
  - Time-weighting the scores instead of the plain mean differs negligibly under Poisson sampling.
  - **R:** ≤ 0.3%. **Not material.**

### 6. Valuation consistent with $1 netting
- **Design said (§8):** "min(a, b) pairs are redeemed at $1 as they form (netting) … YES pays the settlement value; NO pays 1 − value … unsettled then is marked at liquidation value: best bid on our side minus the taker fee, or 0 if there is no bid."
- **Implementation:**
  - **Settled:** YES = v and NO = 1 − v per contract.
  - **Unsettled at the cutoff:**
    - Net YES inventory: YES = m (best YES bid − taker fee, or 0 with no bid) and NO = 1 − m.
    - Net NO inventory: the reverse.
    - Flat: the split is at the best-bid mid, or 0.5 without quotes.
  - The market-account total is exactly pairs × $1 + net × mark. Every fill is valued with these per-contract values.
  - Code: `accounting.contract_values`, `accounting.fill_pnl`, `sim.episode_ledger`.
- **Why necessary:** the design gave the total but not the per-contract values needed to attribute P&L to fills and episodes.
- **Alternative and materiality:**
  - Marking gross positions (each side at its own bid, ignoring netting) would undervalue pairs, since bids sum to less than $1. That lowers P&L **materially if many round trips remain unsettled**. Kalshi nets positions, so netting is the correct basis.
  - The flat split changes per-episode attribution only when two episodes share a market-account. Totals and event clusters are unaffected.
  - **P&L:** material only for the rejected alternative.

### 7. When an episode ends
- **Design said (§5):** "Stop. At program end, market close, or market status ≠ active, cancel everything."
- **Implementation:**
  - The end is the earliest of: program end; the market's recorded `close_time`; the first **observation** of a non-active status (market state is polled every 5 min).
  - Code: `sim.VariantState.expire`, `sim.World.ended`.
- **Why necessary:** a status change is only known when observed.
- **Alternative and materiality:**
  - Backdating to the true status-change time is impossible from public data.
  - While a market is halted or closed there are no trades, so quoting for up to 5 more minutes produces no fills. Coverage in that window is negligible.
  - **Not material.**

### 8. The Arm U seed and de-duplication
- **Design said (§4.4):** "Draw 10 at random from each 24-hour-volume stratum (= 0 and > 0) with `random.Random(20261001 + epoch_day)`." `epoch_day` was not defined.
- **Implementation:**
  - `epoch_day` is the UTC day number (days since 1970-01-01) of the 00:00 epoch.
  - Candidates are de-duplicated to one program per market (highest score, ties by id), sorted by program id, then drawn per stratum.
  - Code: `selection.epoch_day`, `selection.u_draw`.
- **Why necessary:** the seed offset needed a definition, and a market can carry two programs.
- **Alternative and materiality:**
  - A day-since-start offset would draw a different but equally random sample. It is fixed ex ante, so it is not a choice after data.
  - Without de-duplication a market could be drawn twice as two independent standalone episodes.
  - **E (Arm U only):** a different random draw, but no bias. Arm U does not decide M6. **Not material.**

### 9. Tracking breaches
- **Design said (§4.5):** "Any Arm P choice outside the tracked set is logged as a breach and reported."
- **Implementation:**
  - An entered market counts as tracked if its `tracked` record arrives within 10 min of entry. The collector writes it right after the epoch record, whose collection takes ~2 min.
  - An untracked entry would have no book data, so no quotes, fills or rewards, while its fill reserve still counts against capital. That is conservative, and it is reported.
  - Code: `sim.episode_ledger` (`tracked_ok`), `collector.epoch`.
- **Why necessary:** by construction the tracked record is written just after the epoch record.
- **Alternative and materiality:**
  - Requiring tracking before entry would flag every entry.
  - The collector tracks the top 100 per epoch, and Arm P held ≤ 16 in the feasibility snapshot, so breaches should not occur.
  - **Not material unless breaches occur**, and they are reported.

### 10. Liquidation marks at the settlement cutoff
- **Design said (v2 §10):** "trading P&L is settled value where the market settled by the settlement cutoff; otherwise the liquidation mark at the cutoff … settlement cutoff: its formal checkpoint + 30 days."
- **Implementation:**
  - The replay is re-run to exactly the cutoff.
  - The mark uses the last recorded book at or before the cutoff: settlement mode polls books of every unsettled ever-tracked market every 6 h. The taker fee uses the applicable fee state.
  - Code: `analysis.decide`, `sim.episode_ledger`.
- **Why necessary:** the design fixed the time but not which book observation is used.
- **Alternative and materiality:**
  - Marking at the checkpoint, or at the mid instead of the bid, would change P&L for inventory unsettled at the cutoff. **Potentially material** for far-dated markets: the feasibility snapshot included 2027 settlements.
  - The bid − taker fee mark is the conservative choice and was approved in the design. Its possible under-valuation is disclosed: the realised P&L of such inventory could be higher.

## B. Choices made since the first audit (also frozen; please confirm)

**B1. Known vs applicable fee on fills** (implements reviewer item 4).
- Every paper fill records two fees:
  - the fee **known** at the fill: only observations made at or before it;
  - the fee **applicable** at the fill, reconstructed from everything observed by the settlement cutoff: the series state at the fill, adjusted by the fee-change history, plus any event override.
- Each carries provenance: which observations were used, and their receive times.
- **P&L uses the applicable fee.** Known-fee P&L is reported as a sensitivity.
- If a series state was observed only after a fee change scheduled after the fill, the fee at the fill is undetermined. Maker fees at M = 1 are then used (conservative).
- Selection never uses either (A1).
- Code: `sim.World.fee_state`.
- *Materiality:* **P&L (fees only)**, small; conservative when uncertain.

**B2. Incremental fee-object fetching.** Fee objects for newly tracked markets, and the 6-hourly full refresh, are fetched 2 markets per loop pass, interleaved with book polls.
- A local validation showed the previous all-at-once refresh blocked polling for about 40 s at each start and every 6 h. That was an unplanned, uncompensated gap.
- *Materiality:* **R:** removes about 40–120 s of gap every 6 h.

**B3. Collection gaps are recorded explicitly.** The `ops` stream records `collection_gap` entries (`reason` epoch or loop_stall) with start and end. They are never compensated (A5).

**B4. Validation quarantine.** Validation runs write a `validation` meta record into a directory whose path must contain `validation`. The collector refuses to mix validation and prospective data, and the simulator refuses any directory containing validation data.

**B5. Request ceiling 2.0/s** (reviewer item 2).
