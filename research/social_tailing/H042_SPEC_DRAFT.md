# H042 — Kalshi Social Prospective Tailing: frozen-specification CANDIDATE (DRAFT, NOT FROZEN)

**State: BLOCKED / NOT STARTED.** This document is a design draft. It is not frozen, no data is collected, and it may
be frozen only after (1) Kalshi's written authorization of the capture route (`AUTHORIZATION.md`), (2) owner review,
(3) implementation of the frozen code with tests, (4) a hash manifest of spec + code + parameters + seed.
Every numeric parameter below marked **[P]** is a *proposal* awaiting owner approval; none was chosen from outcome data.

Isolation: no shared code, data or parameters with H038/H039/H040/H041, M6 or structural_arb. Formulas restated here
(fees, book parsing) are re-implemented for H042, not imported.

---

## 1. Question and non-question

* **Question.** Following public Kalshi Social position posts from a frozen set of accounts, entering only at the
  first legitimately available executable market state after our system detects the post, holding to settlement and
  paying fees: what is the follower's net return, how uncertain is it, and does it exceed matched placebo entries?
* **Not the question.** Which trader has the highest lifetime profit; whether traders' own displayed returns are real.
  Trader P&L is never substituted for follower P&L.

## 2. Data scope

* **Social data:** only what the Kalshi-authorized capture route returns (`AUTHORIZATION.md`). No scraping, browser or
  app automation, undocumented endpoints, third-party scrapers, manual selection, or external channels
  (X, Discord, pick services) unless a later protocol version explicitly freezes such a source.
* **Market data:** Kalshi Trade API v2 public market data (order books, market/event/series objects, trades, fee
  changes, settlement), subject to the same authorization covering research storage/analysis.
* **Pre-freeze material** (manual profile inspection, `CANDIDATE_DISCOVERY_NOTES.md`): discovery/design only; never data.

## 3. Population, inclusion and exclusion

* **Post:** one object returned by the authorized Social feed with a unique platform post id (or, if none, a capture id
  = sha256 of account id + platform timestamp + canonical body). Inner Circle / private / non-public posts: excluded
  (out of scope even if visible to the owner).
* **Position post:** a post carrying a **structured** position reference (machine-readable market ticker(s) + side),
  as provided by the feed. Text-only mentions ("I like the Jets") are logged as `COMMENTARY` and never traded —
  parsing free text into trades would be subjective.
* **Primary population:** single-market (one ticker, binary YES/NO) position posts by frozen-manifest accounts,
  **captured by our system after START**, whose market is **tradeable at detection** (timing class ≠
  `POST_RESOLUTION`). All timing classes other than `POST_RESOLUTION` are in the primary population (the follower can
  observe class at detection, but primary does not filter on it; classes are pre-specified strata, §11.9).
* **Excluded from the primary follower-ROI test, still logged:** combos/multivariate (2-leg, 3–4, 5+; descriptive
  only — no apparently-executable follower ROI is computed without an authorized reproducible quote), commentary,
  `POST_RESOLUTION` posts, posts by non-manifest accounts, scalar/non-binary contracts.
* **Never excluded:** losing posts, deleted/edited posts (first captured version is the observation), accounts that go
  private or stop posting (attrition is reported; their earlier observations stay).

## 4. Capture procedure (requires authorization; mechanical and complete)

1. A poller (or push subscription, whatever is authorized) watches **every** frozen account. Each returned post is
   appended to `post_captures` with `t_detect` = our receive timestamp (UTC ns, NTP-synced host) **before any parsing**.
2. Completeness: each poll records the account's full returned post list (ids + hashes), so missed posts between polls
   are detectable as ids first seen late; `t_detect` is then the late time (no back-dating).
3. Re-observation schedule for every captured post: +1 h, +24 h, at market settlement, at horizon end → `post_reobs`
   (present/absent, content hash). Differences ⇒ `EDITED` / `DELETED` events with time bounds. Position fields from the
   **first** capture are authoritative.
4. Capture health is logged (poll cadence, errors, 429s, gaps). Capture uptime feeds validity (§12).

## 5. Account-discovery and selection procedure (B)

Run once, **before freeze**, through the authorized route only, over a fixed discovery window **W_disc = 14 days [P]**.
Profit is never used to rank-select (it appears only in stratum S4, which is *sampled*, not top-k).

| stratum | definition (computed mechanically from authorized data in W_disc) | target n [P] |
|---|---|---|
| S0 owner-nominated | the 9 accounts in `CANDIDATE_DISCOVERY_NOTES.md` (fixed list; no performance filter) | 9 |
| S1 high-activity | public accounts ranked by number of single-market position posts in W_disc; seeded draw of 8 from the top 50 | 8 |
| S2 specialist | ≥ 70% [P] of position posts in one Kalshi category and ≥ 10 position posts; seeded draw of 8, at most 2 per category | 8 |
| S3 credited/tailed | accounts explicitly named as source/tailed (@-mention with tail/credit, platform repost/“copy” feature) by ≥ 2 distinct accounts in the discovery graph | up to 5 |
| S4 leaderboard | union of leaderboard lists by profit **and** by volume (all timeframes available); seeded draw of 4 from each list's top 50 | 8 |
| S5 random active | seeded uniform draw from all public accounts with ≥ 5 single-market position posts in W_disc | 10 |

* **Eligibility (all strata):** public profile at freeze; ≥ 1 position post in W_disc (S0 included regardless of count,
  flagged if 0); not an official Kalshi account. Promotional/affiliate accounts are flagged, not excluded.
* **Overlap:** an account is assigned to the first stratum (S0→S5) it qualifies for; vacancies are refilled by the
  next seeded draw within the stratum.
* **Seeded draws:** order candidates by stable account id; draw by `sha256(SEED_DISC ‖ stratum ‖ account_id)` ascending.
  `SEED_DISC` is committed (hash) before the discovery window opens.
* **Discovery graph:** explicit credit/tail edges seen in W_disc are stored (§7.4) and used for S3 and for later
  provenance analysis.
* **Freeze:** `account_manifest` = id, handle, stratum, eligibility evidence hashes, profile snapshot (displayed profit,
  volume, trade count, post count, join date, categories) with capture time. After freeze: **no additions** (even if an
  outside account starts winning), **no removals** (even if a frozen account starts losing).
* **Target total:** 30–50 accounts (≤ 48 with the targets above).

## 6. Timing classification (A) — objective, outcome-blind, computable at detection

Inputs (all available at or before `t_detect`; **settlement outcome is never an input**):
`t_post` (platform post time, exact or bounded `[t_lo, t_hi]`), `t_detect`, `t_entry`/`p_entry` (trader's displayed
position open time / average price, if the feed provides them), market state from the first snapshot S1 (status,
`open_time`, `close_time`), public price history (trades/candles) up to `t_post`.

Derived: `L = close_time − open_time` (trading window), `ttc = close_time − t_post`,
`age = t_post − t_entry`, `move = P_side(t_post) − p_entry` where `P_side(t)` = last traded price of the posted side at or
before `t` (positive = moved in the trader's favour before disclosure).

Rules, evaluated in order; first match wins [all thresholds P]:

1. **POST_RESOLUTION** — at `t_post` (or `t_hi`) the market was not tradeable: `close_time ≤ t_post`, or S1 status ∉
   {active, open} with a status-change time ≤ t_post, or the market is determined/settled.
2. **TIMING_UNKNOWN** — `t_post` bound wider than 10 min, or neither (`t_entry`) nor (`p_entry` and price history) is
   available to assess disclosure delay.
3. **RETROSPECTIVE** — `age > 60 min`, or `move ≥ 0.15` (≥ 15¢ favourable move between the trader's entry and the post).
4. **LATE_BUT_LIVE** — `ttc < max(2 min, 0.20·L)`, or `age > 10 min`, or `move ≥ 0.05`.
5. **PROSPECTIVE** — otherwise (posted within 10 min of entry, < 5¢ favourable move, ≥ 20% of the trading window left).

If only one of `t_entry`/`p_entry` exists, the rules use the available one; the missing criterion is treated as
satisfied for PROSPECTIVE only if the feed explicitly states the post was made at entry (else rule 2 applies).
Our own detection lag (`t_detect − t_post`) is **not** part of the class (it is the follower's latency, §10).

## 7. Identity, clustering and provenance (C, D)

### 7.1 IDs
* `social_post_id` — one per platform post.
* `economic_position_id` — one trader's underlying position: (account, ticker, side) from first appearance until the
  displayed size returns to 0 (or the platform's own position id if exposed). Repeated posts referencing it map to one id.
* `signal_id` — one account's actionable recommendation: the **first** position post that opens or announces an
  `economic_position_id`. Later posts on the same economic position (updates, re-shares, "still holding") attach to the
  same `signal_id` and never trigger a new fill. A re-entry after the position went to 0 is a new economic position and
  a new signal.
* `opportunity_id` (cross-account) — all signals on the same (ticker, side) whose `t_detect` lies within 60 min [P] of
  the cluster's first signal (single-linkage in time). One opportunity = one fill for the pooled "union follower".

### 7.2 Duplicate handling
Duplicate posts (same `economic_position_id`) and duplicate signals (same `opportunity_id`) are recorded with links,
never counted as independent bets or evidence.

### 7.3 Dependence components (for inference, §13)
Union-find over fills connecting any two that share: `opportunity_id`; or `event_ticker`; or (`series_ticker` and
`close_time` within 24 h) [P]. Connected components are the resampling units.

### 7.4 Signal provenance (relationship edges)
Edge types, created **only** from objective public evidence in captured posts:
`EXPLICIT_TAIL` (post names/@-mentions another account as source, or uses a platform tail/copy feature),
`REPOST` (platform repost/quote of another post), `DUPLICATE` (same account re-references own position),
`ORIGINAL` (first signal of an opportunity with no inbound edge, by time),
`UNKNOWN_RELATIONSHIP` (same ticker+side by different accounts with no explicit link). **Same side alone never implies
copying.** Edges carry the post ids and capture hashes that support them. The `@wightsurfer10` upstream question is
answered descriptively from these edges (in-degree of EXPLICIT_TAIL/REPOST, lead time of its signals vs downstream ones).

## 8. Market snapshots

On detection of any position post (all classes), immediately request, in parallel:
the public order book of each leg (S1 = first HTTP-200 parsed book with receive time ≥ `t_detect`), the market object,
the event and series objects, trades since `t_post − 15 min`. Then scheduled extra book snapshots at
`t_detect + 30 s, + 60 s, + 300 s` (sensitivity, §10). Raw bodies, HTTP status, send/receive times are stored
(`market_snapshots`). A failed request (429/timeout) is recorded and retried with bounded exponential backoff; S1 is the
first **successful** one. If no successful book within `T_snap = 60 s` [P] → `NOT_COPYABLE(NO_SNAPSHOT)`.

## 9. Follower fill algorithm (F)

For each primary signal (and each opportunity, §7.1), using book S1 only:

1. Side asks: buying YES consumes YES asks (= 1 − NO bids); buying NO consumes NO asks (= 1 − YES bids); levels
   ascending by price.
2. Stake: **Q = 10 contracts** [P], fixed for every signal (no sizing by conviction or trader size).
3. Walk levels until Q filled. `NOT_COPYABLE` (recorded, no fill) if any of:
   market not active at S1 · no ask on the side · cumulative depth < Q · fill would need a level ≥ $0.99 [P] ·
   exchange not trading · fee state unresolved (`FEE_UNRESOLVED`, counted separately).
   No partial fills.
4. Fill = per-level (price, qty); VWAP; cost = Σ price·qty + fees.
5. **The trader's displayed entry price is never used** except for the slippage diagnostic.

### 9.1 Fees
Per executed level: `fee = ceil_g( ceil_1e-6( m · 0.07 · C · P · (1 − P) ) )`, where `m` = fee multiplier in force at S1
from a time-versioned ledger built from `/series`, `/series/fee_changes`, event overrides; `g` = **$0.01 [P]**
(conservative rounding, primary) with `g = $0.0001` as a reported sensitivity. Unsupported fee type ⇒ `FEE_UNRESOLVED`.
Raw fee objects and their receive times are stored.

### 9.2 Settlement
Hold to settlement. Payout = Q × $1 if the posted side wins, else 0. Result from the public market object after
settlement (raw body stored, `settlements`). Voided/cancelled market ⇒ net 0, flagged. Not settled by the settlement
cutoff (§14) ⇒ `UNSETTLED`, excluded from P&L, counted, plus a sensitivity marking it at the last traded price.

## 10. Detection latency (G)

* **Primary latency:** `ℓ = t_S1_recv − t_detect` (no artificial delay is imposed on the primary result).
* Also reported: `t_detect − t_post` (Social delivery/capture lag), and the full chain
  `t_post → t_detect → t_S1 → fill → settlement → P&L` per signal.
* **Pre-specified secondary sensitivity:** identical fill rule applied to the first successful book with send time ≥
  `t_detect + d`, d ∈ {30 s, 60 s, 300 s}. Reported alongside primary, never replacing it.

## 11. Estimands (J) — exact definitions

Units: **pooled (primary)** = one "union follower" fill per `opportunity_id` (first detection across the manifest);
**account-level** = one fill per `signal_id` of that account. For copyable, settled, non-void fill *i*:
`c_i` = cost incl. fees, `π_i` = payout, `net_i = π_i − c_i`, `r_i = net_i / c_i`.

1. **Net follower P&L** = Σ net_i.
2. **Follower ROI (primary estimand)** = Σ net_i / Σ c_i (ratio of sums; capital-weighted).
3. **Mean net return per copied signal** = (1/n) Σ r_i.
4. **Median net return** = median(r_i).
5. **Win rate** = #{π_i > 0} / n.
6. **Maximum drawdown** = max over k of (max_{j≤k} P_j − P_k), where P_k is cumulative net P&L ordered by settlement
   time (ties by `t_detect`); reported in $ and as a fraction of Σ c_i.
7. **Prospective Disclosure Rate (B)** = #PROSPECTIVE position posts / #all captured position posts, per account;
   also on unique `economic_position_id`s and singles-only. Not a profitability measure.
8. **Copyable rate** = #copyable / #primary signals, with NOT_COPYABLE reasons tabulated.
9. **Trader-to-follower slippage** (only where `p_entry` is observable) = VWAP_follower − p_entry (¢, same side), and
   VWAP_follower − P_side(t_post); mean and median.
10. **Matched-control excess return (co-primary)** = (1/n) Σ (r_i − r̄_i^ctrl), r̄^ctrl = mean return of the K matched
    controls of fill i (§12).
11. Also reported: gross P&L, total fees, n, n copyable, wins/losses, results by account, by category, by timing class,
    by latency sensitivity; combos descriptively by leg count (2, 3–4, 5+) without executable follower ROI.

**Concentration safeguards:** account-level table always shown in full; share of pooled net P&L from the top account and
top 3 opportunities; leave-one-account-out pooled ROI; equal-account-weighted ROI as a secondary estimand.

## 12. Matched-control algorithm (H)

For each primary copyable fill (signal or opportunity) at S1 time τ with side σ, VWAP p, category c, ttc bucket, depth bucket:

1. **Candidate universe at τ:** all open, binary, non-multivariate markets from a market list refreshed ≤ 10 min [P]
   before τ.
2. **Exclusions (dependence guard):** the signal's own market; any market with the same `event_ticker`; any market in
   the same `series_ticker` with `close_time` within 24 h of the signal's; any market in a mutually-exclusive event with
   the signal's; any market posted by any manifest account within ±24 h of τ; any market already used as a control for
   a fill in the same dependence component.
3. **Strata to match:** category = c (Kalshi series category); side = σ; price bucket: control's best ask on σ within
   p ± $0.05; ttc bucket ∈ {<1 h, 1–6 h, 6–24 h, 1–7 d, 7–30 d, >30 d}; liquidity bucket of σ-side ask depth within
   5¢ of best: {Q–10Q, 10Q–100Q, >100Q} contracts.
4. **Relaxation ladder** (pre-specified, recorded as match level): L0 all strata → L1 price ± $0.10 → L2 adjacent ttc
   buckets merged → L3 liquidity dropped (control must still be copyable) → L4 category dropped. None ⇒ `NO_CONTROL`
   (fill kept in follower estimands, excluded from the excess estimand, counted).
5. **Draw:** candidates ordered by `sha256(SEED_CTRL ‖ fill_id ‖ ticker)`; take them in order, fetch each one's order
   book immediately (same τ window), apply the identical fill algorithm; the first **K = 3** [P] copyable ones are the
   controls. Non-copyable draws are recorded and skipped.
6. Controls are held to settlement, fees and settlement identical to §9.
7. **Seeds:** `SEED_DISC`, `SEED_CTRL`, `SEED_BOOT` are generated before freeze, their sha256 committed in the manifest,
   values revealed only in the frozen code (so they cannot be tuned after seeing data).

Controls must be selected live (books at τ cannot be fetched later).

## 13. Inference (K)

* **Resampling unit:** dependence components (§7.3) — they absorb repeated posts of one position, duplicate signals,
  cross-account tails of one source, same-event and same-series/date exposure.
* **Method:** nonparametric cluster bootstrap over components, B = 10,000, `SEED_BOOT`; statistics: follower ROI (ratio
  of resampled sums), mean r, mean excess vs controls; 95% percentile intervals. Account-level intervals: bootstrap over
  that account's components only.
* Pooled inference does not treat posts, or accounts' signals, as independent; account-level results are descriptive
  per account, with Holm-adjusted bootstrap one-sided p-values for "excess > 0" flagged exploratory.
* Pre-specified sensitivities: equal-account weighting; leave-one-account-out; latency sensitivities; `g = $0.0001`;
  UNSETTLED marked at last price.

## 14. Stopping rule, horizon, decision categories (L)

* **Horizon:** fixed collection window **84 days (12 weeks) [P]** from START; **settlement cutoff** = START + 84 d + 30 d.
  One evaluation, after the cutoff. No early stop for winning or losing; no interim outcome analysis (operations
  monitoring = counts, capture health, latency only).
* **Validity (else INVALID, no conclusion):** Social capture uptime ≥ 95% of the window and no capture gap > 6 h [P];
  market snapshot success ≥ 95%; code/manifest identity on every record.
* **Minimum evidence [P]:** pooled ≥ 100 dependence components with copyable settled fills; per account ≥ 30.
* **Categories** (pooled and per account, each from its own intervals), evaluated **in order**, first match wins:

| # | category | rule |
|---|---|---|
| 1 | INVALID | a validity condition above fails |
| 2 | INSUFFICIENT_EVIDENCE | below the minimum evidence |
| 3 | WARRANTS_FURTHER_PROSPECTIVE_TESTING | lower 95% bound of follower ROI > 0 **and** lower 95% bound of matched-control excess > 0 (justifies a new pre-registered replication, not a trading decision) |
| 4 | EVIDENCE_AGAINST_A_REPRODUCIBLE_FOLLOWER_EFFECT | upper 95% bound of follower ROI < 0, **or** upper 95% bound of matched-control excess < 0 |
| 5 | INSUFFICIENT_EVIDENCE | otherwise (intervals include 0; reported with their widths) |

  No target ROI is assumed; the report gives point estimates and interval widths.

## 15. Prohibited interim changes

No change to manifest, rules, thresholds, seeds, fill, fees, controls, estimands, inference or horizon after freeze;
no dropping losing posts; no account additions/removals; no reprocessing raw data under new rules into the original
version. Any change ⇒ new version `H042-vN` with its own manifest and prospective window; the original stays as frozen.

## 16. Raw-data schema (append-only gzip JSONL, one stream per type)

| stream | key fields |
|---|---|
| `account_manifest` (frozen) | account_id, handle, stratum, eligibility evidence hashes, profile snapshot, captured_utc |
| `post_captures` | capture_id, social_post_id, account_id, t_detect, t_post (raw + parsed bounds), structured position fields as returned (tickers, sides, p_entry, size, t_entry), body sha256, raw body, source endpoint, poll_id |
| `poll_log` | poll_id, account_id, t_request, t_response, status, returned post ids + hashes |
| `post_reobs` | social_post_id, t_reobs, present, body sha256, change type |
| `signals` | signal_id, economic_position_id, opportunity_id, social_post_ids, legs, combo size, timing class + inputs, qualifying flag/reason |
| `relationship_edges` | from, to, type, supporting post ids/hashes |
| `market_snapshots` | ref id, ticker, kind, http status, send/recv times, raw body |
| `fills` | fill_id, ref (signal/opportunity/control), rule version, delay d, levels, VWAP, fees + fee provenance, copyable flag/reason |
| `controls` | control set per fill: match level, candidate list hash, draw order, chosen tickers |
| `settlements` | ticker, result, settled time, raw body |
| `ops` | capture uptime, gaps, errors, 429s, latency stats (no outcomes) |

## 17. Provenance and hashing

Every record: stream sequence number, `prev_sha256` (hash chain per stream), code manifest sha256, config version,
source endpoint, raw-body sha256. Daily digest (last chain hash per stream) written to an append-only digest file and
committed. The frozen manifest hashes this spec, all code, the account manifest and seed commitments. Records are never
rewritten; later knowledge is a new record referencing the old.

## 18. Owner decisions pending before freeze
All [P] parameters; K; Q; horizon; minimum evidence; fee rounding primary; the access route and its exact capabilities
(may force amendments to §4/§6 if the authorized feed lacks exact times or structured positions — any such amendment is
made before freeze).
