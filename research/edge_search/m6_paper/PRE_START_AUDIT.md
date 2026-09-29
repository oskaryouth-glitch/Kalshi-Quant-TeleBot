# M6 paper experiment: PRE-START AUDIT (for the independent reviewer)

- **Date:** 2026-09-29.
- **Status:** **implemented, tested and hash-frozen. NOT STARTED.**
- **Proposed freeze manifest:** `b8c18ef3881d9c4343fb778d3bd62d9c8bd7352cf8166559ceeded05fda7233d` (`PREREG_M6_PAPER.md`).
- **Constraints kept:** no order placed; no credentials; H038/H039 untouched.

## 1. What exists

| component | file | role |
|---|---|---|
| frozen parameters | `spec.py` | every threshold, cadence, seed and fee constant in one place |
| reward scoring | `lip.py` | filed LIP formula; **identical to the PT1-frozen functions** (asserted on 400 random books) |
| selection | `selection.py` | eligibility, x15, C\*, L\*, score, ranked Arm P admission, Arm U draw |
| fill model | `fills.py` | queue position, own-order priority, trade-through, V_T/V_P/V_C cancellation credit |
| accounting | `accounting.py` | fees (direct/non-direct rounding), netting, settled/liquidation valuation |
| simulator | `sim.py` | offline, deterministic, causal replay; 3 variants in lockstep; stopping rule |
| inference/decision | `analysis.py` | cluster bootstrap LB95, verdicts, no-peek enforcement |
| monitor | `status.py` | counts and data integrity only; never P&L |
| collector | `collector.py` | public GETs only, via an endpoint allowlist; streams per `storage.py`; restart recovery; **refuses to start without `--i-have-reviewer-approval-to-start`** |
| smoke check | `smoke_check.py` | live format conformance; data deleted |

## 2. Tests: 43 passed (`python -m pytest m6_paper/tests`)

| area | tests | what they pin down |
|---|---|---|
| reward/fees/accounting | 6 | PT1 equality (400 random books, fees at both roundings); excluded snapshot scores 0; netting releases capital; liquidation and settlement valuation equal pairs × $1 + marked net |
| fill model | 10 | queue depletion then fill; taker-side mapping; trade-through; better-priced prints ignored; latency; own-order priority with exact real-queue accounting; V_T < V_P < V_C credit; vanished level |
| selection | 4 | 24 h, combo and status eligibility; x15 minimality and the C\* formula; one per market with ties by id; greedy admission; deterministic, stratified, windowed Arm U draw |
| simulator end-to-end | 8 | entry at the epoch; 1 s latency; queue fill; \|q\| ≤ x; capital ≤ K in every variant; rewards and payout floor; program-end stop; V_T ≤ V_P ≤ V_C fills; **no look-ahead** (future data cannot change past fills or entries); stopping rule (day 35; continue to day 40; day-60 INSUFFICIENT; per-arm entry closure); **no peeking** (`decide` raises before checkpoint + cutoff; `status` output has no P&L fields); ledger identity |
| collector/analysis | 15 | GET-only allowlist rejects `/portfolio/*` and order paths; epoch records raw data and tracks the top 100; change-only books; trade dedupe and tracked filter; completeness backfill; restart restores tracking; epoch boundaries; refuses to start without approval; source scan (no order or credential code); deterministic bootstrap; verdict matrix; ranked arms only decide M6 |

**Bugs found and fixed during implementation**, each caught by the tests before any data existed:
1. The merged event stream late-bound the stream name, so every record was treated as an epoch.
2. `entries_open` ignored *when* an arm was decided.
3. Tracking state was in memory only, so a restart would have stopped tracking entered programs. Restart recovery was added.
4. A performance issue: per-event loops over every account. An index and an end-time heap were added, and the behaviour is unchanged per the tests.

## 3. Live technical smoke check (2026-09-29, about 2.3 min; data deleted unread; no episodes, rewards or P&L computed)

**Recorded in one epoch:**
- 5,456 live program markets, with all 5,456 books and 0 missing;
- 12,069 event→series mappings and 4,134 series fee states;
- 4,178 programs evaluable under the ≥ 24 h rule.

**Formats and polls:**
- Book, trade, program, market and fee-state field formats all match what the simulator reads. This is the class of bug that affected M5 (live vs historical field names).
- A tracked-book poll of 100 markets takes 0.34 s. Fee state covers `quadratic` and `quadratic_with_maker_fees`. The rules watch lists 35 LIP-related filings.

**Rate:** 286 requests in 139 s; **17 × HTTP 429 (6%)**, all retried successfully; 0 errors.

## 4. Implementation interpretations the reviewer should confirm

Each is fixed in code now, but was not spelled out in DESIGN v2.

1. **Selection fee state.** The public events list carries no fee overrides. Selection therefore uses the exact **series** fee state (series found through the events list; an unknown series means maker fees at M = 1). Event overrides are fetched for tracked markets and applied to **fills** and valuation. This affects only the maker-fee part of C\*.
2. **Formal checkpoint across variants.** Capital use differs by fill variant, so the three variants can hold different programs. An arm reaches its formal checkpoint only when **all three** variants have ≥ 20 completed episodes. Each variant's decision set is its own completed episodes; the worst NET decides.
3. **V_P formula.** "Q −= Δ·Q/(level − n)" is implemented with the real level size at the previous snapshot as the denominator. Our paper order is never in the real book.
4. **Sizes.** New and replenishment orders are whole contracts. Public trades can be fractional (`count_fp`), so fills and remainders can be fractional.
5. **Coverage.** Each poll covers the interval since the previous poll, capped at 60 s, so T_cov excludes silences. The payout SE uses clock-hour batch means. With fewer than 2 batches the conservative payout is 0.
6. **Valuation with netting.**
   - Unsettled at the cutoff, the net side is marked at best bid − taker fee (0 without a bid), and the other side at 1 − mark. So pairs are worth exactly $1.
   - A flat position is split at the mid. This is only an attribution split; the total is unchanged.
7. **Episode end.** The earliest of: program end, recorded `close_time`, or the first observation of a non-active status.
8. **Arm U seed and dedupe.** The seed is `20261001 + UTC day number`. Candidates are de-duplicated to one program per market before the per-stratum draw.
9. **Tracking breaches.** An entered market counts as tracked if its `tracked` record arrives within 10 min of the entry. The tracked record follows the epoch record by the epoch's collection time.
10. **Liquidation marks** use the book at the arm's settlement cutoff (formal checkpoint + 30 days). The replay is re-run to exactly that time.

## 5. Operational risks and decisions

1. **Where it runs (decision needed).** This cloud container is ephemeral and is reclaimed after inactivity, so it **cannot host a 35–60-day collection** plus 30 days of settlement polling. A persistent host is required: your machine or a small server, with Python ≥ 3.11 and no other dependencies. Data volume will be modest, but I have no estimate yet because the tracked-set size is unknown in practice. I recommend 20 GB free.
2. **Epoch blocking.** An epoch takes about 2–2.5 min every 6 h, and the single-threaded collector does not poll tracked books meanwhile. Those minutes count as **gaps**: rewards 0, conservative. Fills are unaffected, because trades are fetched afterwards from the last poll time. That is about 0.7% of time.
3. **Rate limits.** 6% 429s at the spec's 3 requests/s ceiling. The retries worked, but sustained 429s during an epoch lengthen gaps. The option is to lower `MAX_REQUESTS_PER_S` to 2.0 before the freeze (longer epochs, fewer 429s). No recommendation either way; your call.
4. **Replay cost.** A synthetic benchmark ran at about 28 s per day for 50 fully quoted markets. That extrapolates to roughly 1–2 h per full replay; `decide` replays up to twice per arm. Acceptable offline.
5. **Invalid-run rule.** Cumulative collector downtime > 24 h, or a trade-feed silence > 6 h, before the last formal checkpoint makes the run INVALID. That is checked by `status.py` from heartbeats. Host reliability therefore matters.

## 6. Decisions requested from the reviewer

1. Approve (or amend) the interpretations in §4.
2. Choose the collection host (§5.1), and whether to lower the request ceiling to 2.0/s (§5.3).
3. Approve the start with this exact manifest, or request changes (then re-hash and re-audit).

Until then nothing runs.
