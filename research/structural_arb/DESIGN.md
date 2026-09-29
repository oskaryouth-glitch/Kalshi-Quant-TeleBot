# Structural Pricing Inconsistency Scanner: Design, Derivations and Audit

Status (2026-09-27): the mathematical model, fee mathematics, semantics layer and evaluator are
**derived, adversarially tested and verified against official Kalshi sources**. Routine
collector work and forward collection remain (§H).

The null hypothesis is that no executable structural arbitrage exists. Negative results are
first-class outputs.

## 0. Isolation (H022 / H038)

* H022 and H038 are not in this repository, and nothing here references them.
* All code, data and sources for this project live under `research/structural_arb/`, and no
  file outside it is modified.
* The HTTP client can only issue unauthenticated GETs to an allowlist of public paths. It
  never reads credentials. `tests/test_client.py` enforces this statically and at runtime.
* No orders are ever placed.

## A. Official evidence

Every item below is backed by a file in `sources/`, with hashes in `sources/SOURCES.md`.

| # | Fact the maths depends on | Source |
|---|---|---|
| A1 | Binary settlement: YES iff the Expiration Value is in the Payout Criterion, else NO | Rulebook v1.29, "Market Outcome" definition and Rule 6.3(a) |
| A2 | **Discretionary settlement** when outcomes can't be determined: last traded price or an Outcome Review Committee "fair allocation" | Rulebook 6.3(c), 7.1 |
| A3 | Kalshi may change the source agency, underlying or expiration | Rulebook 7.2 |
| A4 | Trades may be cancelled or adjusted if executed outside ±$0.20 of fair value (the No Cancellation Range) | Rulebook 5.11(c) |
| A5 | `result ∈ {yes, no, scalar}`. **Scalar results really occur**: 4 live golf markets settled at $0.05, $0.11, $0.22 and $0.45 (a withdrawal before tee-off) | API get-market schema; live data |
| A6 | `mutually_exclusive = true` ⇔ MECNET ⇔ "at most one market in this event can resolve to 'yes'" | API get-event schema |
| A7 | Crypto terms (BTC and ETH, identical): "between" is **inclusive**; **"If no data is available … the market resolves to No"** (an ALL_NO state); the underlying is the average of 60 index prints, with no rounding stated | contract_terms/BTC.pdf, ETH.pdf (text contained in the controlling filings "BTC/ETH Amendment 2 for posting.pdf", 2025-04-28) |
| A8 | INX terms: "between" inclusive; no data → most recent value; "before" variants are path-dependent | contract_terms/INX.pdf |
| A9 | Temperature terms: above `>`, below `<`, at least `≥`, between inclusive; "full precision reported"; no data → **Exchange-determined "last fair price"**. **SUPERSEDED (2026-09-29):** amendments filed 2026-08-17 (The Weather Company first Source Agency) and 2026-09-02 (Exchange-specified reports; material-error expiration delay) were never reflected in the served PDF. Not verified until re-reviewed | contract_terms/GLOBALTEMPERATURE.pdf (= 2025-12-12 certification); edge_search/TERMS_AUDIT.md |
| A10 | Combos: YES pays the **product of component payouts, floored to the cent**; NO pays 1 − YES | contract_terms/FOOTBALLSTATS.pdf |
| A11 | `floor_strike` / `cap_strike` are the "minimum/maximum expiration value that leads to YES", but live data shows they are an *encoding* that can disagree with the rules text (§B.2) | API schema; live data |
| A12 | Order book: bids only; YES ask = 1 − best NO bid; levels sorted ascending; dollar strings (≤ 4 dp) and fixed-point counts (≥ 0.01) | docs Orderbook Responses; Fixed-Point |
| A13 | The multi-market order-book endpoint and WebSockets **require authentication**. The public REST book has **no server timestamp or sequence number**, and responses are served via CloudFront | docs; response headers |
| A14 | Taker fee: `M × 0.07 × C × P(1−P)`. Fee rounding: `ceil_6dp`, then balance alignment to **$0.0001 (direct)** or **$0.01 (non-direct)**, with a per-order accumulator. No settlement fee | Fee Schedule PDF 2026-07-07; docs Fee Rounding |
| A15 | M and fee type change over time per series and per **event** (e.g. MLB events switch to M=1 at first pitch). The PDF multiplier table is out of date (63 later changes) | API `/series/fee_changes`, `/events/fee_changes` |
| A16 | Combo (`KXMVE*`) markets: 5 of the 60 highest-volume ones show any book level. The `/markets` summary reports `no_bid_dollars = 1.0000` on 1,933 empty books, a **sentinel** that would imply a $0 YES ask | live data |

## B. Formal model

### B.1 State space

Consider a portfolio of taker buys, each in a distinct market. It is scored against explicit
settlement states. In each state, every market has a worst-case truth `(sure_yes, maybe_yes)`.
A YES position pays iff `sure_yes`; a NO position pays iff `¬maybe_yes`. The locked payoff is
`L = min over states of Σ payoffs`.

* **Numeric family** (one underlying X). States are the atoms of all breakpoints: every
  breakpoint, every open gap between consecutive breakpoints, and both tails. An **ALL_NO**
  state is added when the terms say no data → No (A7), or when the terms are unverified
  (conservative). X is **real-valued**, because no verified terms prove a reporting precision
  (A7, A9). This makes bucket gaps real outcome states: for example (72499.99, 72500) in BTC,
  and (65, 66) in NYC temperature.
* **Categorical MECNET event.** Exactly one listed market wins, or a NONE state.
  Exhaustiveness is never provable, and markets can be added later.
* **Combo.** All 2^k component outcomes, with the combo = AND of the legs' sides (A10).
* **Discretionary states (A2, A5).** These are *not* in L. Every Kalshi market can settle at
  an Exchange-chosen value, so **no Kalshi portfolio is strictly riskless.** This is reported as
  a residual risk, together with `one_leg_discretionary_worst` (the worst payoff if any one leg
  goes scalar at an adversarial value, typically 0 or L−1).

### B.2 Strike-to-interval mapping (the semantic envelope)

For each numeric market, the scanner collects every plausible YES-set reading:
* the field reading, from `strike_type`, `floor_strike` and `cap_strike`;
* the text reading(s), parsed from `rules_primary`: `above/below/at least/at or below/N+/between/…`,
  including `$`, `K`, `billion` and units.

"between" has one reading if its inclusivity is verified, otherwise all four endpoint variants.
From these readings:

    inner = ∩ readings   (YES surely pays)        outer = ∪ readings   (YES possibly pays)

**Theorem (conservativeness).** Each market appears once and payoffs are additive, so for any
consistent choice of true readings the payoff in every state is ≥ the envelope payoff. Hence
L_envelope ≤ L_true.

This is tested by exhaustively enumerating concrete readings (`test_envelope_is_never_more_optimistic…`).

Markets are **rejected** when they have:
* no comparator, or two different comparators;
* "exactly" (rounding rules differ by series);
* text and fields in opposite directions;
* text and field values that aren't plausibly the same number (e.g. POPVOTEMOV's negative
  field strikes vs positive text).

Live, 61,289 of 62,612 numeric markets map. Examples of the encoding gaps the envelope absorbs:
* `KXINXU`: fields `≥ 7550` vs text "above 7549.9999";
* `KXNFLCAREERRSHYDS`: fields `> 13999.5` vs text "at least 14,000";
* vote share: text "44% to 100%, inclusive" vs fields `≥ 44`.

A consequence, verified in `test_identical_markets_with_encoding_uncertainty_are_not_a_lock`:
even an exact duplicate pair **cannot** be certified when the envelope is not tight, because
there is a state where neither leg surely pays.

**Families** (one underlying) share all of:
* contract-terms URL;
* rules text with the comparator clause removed;
* `rules_secondary`, `custom_strike`, `latest_expiration_time` and settlement sources;
* units.

**Path-dependent** wording ("ever", "any", "during", "through", "before/by <month>") splits
families by direction. "Ever above K" is a max statistic and "ever below K" a min statistic, so
they do *not* share an X. Treating them as one would create a false "at most one YES". Between
markets on path statistics are rejected.

Live, BTC+BTCD and ETH+ETHD merge across series (same terms PDF, identical template), as do
NHL season-goal thresholds across events. KXRONI shows two distinct events with identical
rules: a potential R4 duplicate, whose terms are unverified.

### B.3 Relationship derivations

Notation: `a_s(m)` is the executable ask for side s, from walking the book; `b(m)` is the best
YES bid. Every identity below is checked in tests against the brute-force checker.

**R1 (mutually exclusive and exhaustive buckets).** Take an event with markets m₁…mₙ.
* Long, YES on all: L = min over states of #{i : X ∈ inner_i}. L = 1 iff the inner sets cover
  ℝ and there is no ALL_NO state. **Crypto fails** (A7 ALL_NO, plus the .01 gaps), and so does
  **temperature** (integer gaps are real, A9).
* Short, NO on all: L = n − max coverage by outer sets. L = n−1 when the outers are disjoint.
  ALL_NO only raises the payoff to n.
* **Dominance.** For disjoint markets, NO on any k of them locks k−1. The edge
  `Σᵢ(b_i − 1) + 1 − fees` falls with every extra leg, since b_i < 1. So the best R1-short
  portfolio is **the pair with the two highest YES bids** (`R1_EXCLUSIVE_PAIR`); the full basket
  is dominated.
* Categorical MECNET events use only A6 (at most one YES). Long is never locked (NONE state).

**R2 (nesting / monotonicity).** If outer(S) ⊆ inner(B), then YES_B + NO_S pays
1[B] + 1 − 1[S] ≥ 1 in every X state, and 0 + 1 = 1 under ALL_NO. Hence L = 1, and at top of
book `edge = b(S) − a_yes(B) − fees`. This covers nested thresholds in either direction, and
`>` vs `≥` at equal strikes. The atoms include the boundary point.

**R4 (duplicates / complements).** A duplicate is R2 holding in both directions. A cover pair
(YES_a + YES_b with inner_a ∪ inner_b = ℝ, no ALL_NO) has L = 1. A disjoint NO pair is the
R1_EXCLUSIVE_PAIR. Cross-series duplicates need the same terms PDF and template, and are
otherwise never compared.

**R3 (ranges vs threshold).** Take a threshold T and pairwise-disjoint buckets S from one event.
* (A) YES on all of S + NO_T: L = 1 iff outer(T) ⊆ ∪ inner(S).
* (B) YES_T + NO on all of S: L = |S| iff ∪ outer(S) ⊆ inner(T).

A misaligned T (splitting a bucket) keeps A but breaks B. This is tested. Overlapping sets can
lock more than nominal; the evaluator screens on max(nominal, L).

**R5 (combos).**
* Upper: the position on component j + NO_combo has L = 1.
* Lower: YES_combo + the opposite side of every leg has L = 1 (the Fréchet bound).
* Under **scalar** component settlement, with values v ∈ [0,1] and combo = floor_cent(Π v′):
  * upper = v′_j + 1 − floor(Π v′) ≥ 1, because Π v′ ≤ v′_j;
  * lower = floor(Π v′) + Σ(1 − v′_i) ≥ 1 − $0.01, because Π v′ + Σ(1 − v′_i) ≥ 1 by induction.
* So R5 is the only relationship that is robust to discretionary component settlement (up to
  one cent). **But combos show essentially no displayed depth (A16) and trade by authenticated
  RFQ.** R5 is therefore untestable under this project's constraints. That is itself a finding.

## C. Labels and gates

`RULE_DEFINED_LOCK` (renamed from `ARBITRAGE` on 2026-09-27 at the owner's request) means:
positive locked payoff across every settlement state that the verified contract rules require
the model to enumerate, with Kalshi's discretionary-settlement and cancellation risks shown
separately on every record. It is **not** a claim of riskless arbitrage.

The **Rule 5.11 gate** (every leg within ±$0.20 of the last traded price) is a hard
qualification gate. Records it blocks are also written to a separate `rule511` stream, with
`only_rule_5_11_and_or_persistence_failed`, and still get the persistence re-fetch. This
measures what the gate removes; the results must **not** be used to loosen it.

Every candidate whose top-of-book prices violate its relationship (`max(nominal, L) − Σ asks > 0`)
is logged. Consistent observations and missing-ask observations are counted in aggregate.

| Status | Meaning |
|---|---|
| `RULE_DEFINED_LOCK` | L ≥ 1 in every settlement state the verified contract rules require the model to enumerate; verified terms (for every family, categorical MECNET included); all gates pass; edge > 0 under **every** fee scenario at some integer size; persistence confirmed on an independent re-fetch |
| `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE` | lock holds, some execution gate fails (fees/depth/5.11/persistence) |
| `CANDIDATE_TERMS_UNVERIFIED` | lock holds under the conservative model; series terms not yet reviewed |
| `STATISTICAL` | displayed prices violate the naive relationship but L < nominal (gap, ALL_NO, uncertainty) |
| `REJECTED` | book unavailable, CDN cache hit, crossed/locked book, stale metadata, inactive market or halted exchange, leg skew > 2 s, age > 5 s, fee unresolvable, or a checker/template disagreement |

The residual risks below are **attached to every record**:
* Rule 6.3(c) and 7.1 discretionary settlement;
* Rule 7.2 contract modification;
* Rule 5.11 cancellation;
* non-atomic multi-leg execution;
* non-simultaneous REST books.

The Rule 5.11 gate uses the last traded price as a proxy for fair value, requires every leg to
be within $0.20 of it, and fails when no last price exists.

## D. Fees (proofs in `sarb/fees.py`, tests in `tests/test_fees.py`)

* The documented per-order algorithm is implemented exactly. It reproduces:
  * the docs' worked example, to $0.000001;
  * **all 42 cells** of the PDF table at $0.01 precision.

  (The PDF's text says "centicent" but its table is the cent-precision case. The docs resolve
  this by member class.)
* **Bounds when the fill split is unknown.** Displayed levels aggregate resting orders, and
  fills are at least `min_fill_unit` contracts: 1 if every consumed level shows an integer
  quantity, else 0.01.
  * (B1) Σ model ≤ Σ trade_fee < Σ model + n·1e-6.
  * (B2) If every fill's revenue is on the balance grid g, then Σ tf ≤ net < Σ tf + g.
    Proof: the rebate cap never binds, so the accumulator stays below g.
  * (B3) Otherwise, net < Σ tf + n·g.
  * Checked on 4,800 random fragmentations, plus a 100-fill adversarial case.
* **Scenarios**, all reported for every candidate, and all using the multiplier **in force at
  the snapshot**:
  * `direct_expected`: g = $0.0001, one fill per level. This is the owner's account.
  * `direct_bound`: g = $0.0001, worst-case fragmentation.
  * `nondirect_conservative`: g = $0.01, worst-case fragmentation. This is the binding
    scenario for `RULE_DEFINED_LOCK`.

  Fee waivers are ignored (conservative). `flat` and `margin_*` fee types are unresolved.

### D.1 Time-versioned fee ledger (`sarb/fee_ledger.py`, replaces the "max observed multiplier" floor)

**Audit of the replaced design (2026-09-27).** The previous floor, "M ≥ the largest override
ever observed in the series", and the conservative `max(API M, PDF taker M)` **could produce a
wrong current fee in both directions**:
* **Understatement:** an event override already in force before the collector first saw it
  never appears in `/events/fee_changes` (future-only), so the series value was used.
* **Overstatement:** pre-game MLB events at true M=0.5 were charged the in-game maximum of 1;
  decreases and cleared overrides were ignored; the out-of-date PDF table raised
  KXMLBGAME to 1.

Both were removed. No maximum, floor or historical substitution remains.

**Official facts used:**
* F1 `/series/fee_changes?show_historical=true` returns *all* previous and upcoming series
  changes.
* F2 The Series object equals the latest change in that history (checked live on 5 series).
* F3 Event objects carry `fee_type_override` / `fee_multiplier_override`, which "when present,
  take precedence over the series-level fee" (omitempty, so absent means no override).
* F4 `/events/fee_changes` lists only future event changes and has no history parameter. The
  WebSocket `event_fee_update` requires authentication.

**Resolution at snapshot time t:**
1. Every P2/P3/AUDIT leg gets a fresh `GET /events/{e}` and `GET /series/{s}` after its books,
   so the event state is *observed* at most 30 s before t. Any recorded scheduled change
   between the observation and t is applied.
2. If no override is in force, the series layer is the latest of the complete history and the
   fresh series observation, with consistency checks.
3. The result is **`FEE_UNRESOLVED`** (a separate status, with the reason logged, e.g.
   `EVENT_OBSERVATION_STALE`) when:
   * the event or series was not observed, or the observation is stale;
   * the schedule and the observed object disagree;
   * t is within 60 s of a known scheduled change (the API's switch instant is undocumented);
   * the fee type is not modelled.
4. **Persistence.** Append-only JSONL holding the scheduled changes plus state-change points of
   observations. Freshness is in memory only, so after a restart nothing resolves until
   re-observed.
5. **Tests** (`tests/test_fee_ledger.py`) cover:
   * fee increases and decreases;
   * a temporary override, then expiry and reversion;
   * multiple changes, with the latest winning and no leakage across events;
   * an override in force before it was first seen;
   * downtime across an effective timestamp, for both event and series changes;
   * conflicts, the boundary guard and unsupported types;
   * restart from persisted history.

## E. Timing and execution audit

1. **No simultaneity evidence.** Without authentication there are no WebSockets, no batch
   books, and no server timestamps or sequence numbers. The only defensible bound is local:
   `skew = max(recv) − min(sent)` over *the candidate's legs*, on the monotonic clock (wall
   clock can step).
2. **Live finding.** Sweeping a 160-market family at 8 req/s takes about 20 s. A single sweep
   therefore cannot meet the gates. The **collector must be two-phase**:
   * (i) screening sweep;
   * (ii) for every candidate with raw > 0, re-fetch only its legs back to back, together with
     `GET /markets/{t}` for status and last price, and evaluate those fresh books;
   * (iii) after `PERSISTENCE_REFETCH_DELAY_S`, re-fetch and re-evaluate. Persistence = still
     `RULE_DEFINED_LOCK`-eligible.
3. **CDN.** The `x-cache` header is recorded, and hits are rejected. None were observed in
   probes.
4. **Crossed or locked books** (yes_bid + no_bid ≥ 1) are impossible on a live matching
   engine, so they are rejected as stale or inconsistent.
5. **Depth.** Every leg is walked to size C, and C must fill completely. The scanner reports
   edges on the frozen grid {1, 10, 100}, and the **largest integer C** (≤ 5000) positive under
   all scenarios. Edge is not monotone in C, because of rounding.
6. **Partial fills / leg risk.** Legs are separate orders. A "locked" label is conditional on
   all legs filling at the displayed prices. The per-leg abandon (round-trip) loss is **not yet
   computed** (§H).
7. **Summary-field trap (A16).** Prices come only from `/orderbook` levels. Prices ≥ 1 or ≤ 0
   are rejected at parse time.
8. **Look-ahead.** Only metadata and rules fetched before evaluation are used. Terms are
   hash-checked at snapshot time. Outcomes are never used.

## F. Unresolved (not assumed)

* The meaning of `fee_multiplier` for taker vs maker. The docs say "applied to the fee
  calculations"; the conservative scenario also takes the max with the PDF taker column.
* Fair-price coherence across markets in discretionary settlement. No evidence either way, so
  it is excluded from L and reported as residual risk.
* Reporting precision of any underlying. Treated as real-valued, so integer-only arbitrages
  (e.g. temperature R1) are classed as STATISTICAL.
* Terms for all series outside the registry (BTC, ETH, INX, GLOBALTEMPERATURE). These are
  capped at `CANDIDATE_TERMS_UNVERIFIED`.
* Fractional resting orders. When a level shows a fractional quantity, the fee bound
  automatically switches to 0.01-contract fills.

## G. Verification evidence

* 489 unit/property tests.
* A one-off stress run: 3,000 random families, 3,000 partition/gap/R3 cases, 800 envelope
  enumerations, and 300 × 200 scalar combo draws. **No counterexample was found.**
* Live smoke (2026-09-27 17:10 UTC): BTC+BTCD, ETH+ETHD and KXHIGHNY-26SEP28. 246 markets were
  all parsed, all terms hash-verified, and all fees resolved. **Zero displayed structural
  inconsistencies.** Every relationship was price-consistent or lacked an ask. This is one
  snapshot, not a conclusion.

## H. Collector protocol (implemented; to be frozen before the long collection)

`sarb/collector.py`, parameters in `sarb/config.py`:

1. **Refresh.**
   * `/series` list: one call, every 6 h.
   * Registry terms PDFs, SHA-256: every 1 h.
   * `/series/fee_changes` (full history) and `/events/fee_changes` (future only): every 5 min,
     into the **time-versioned fee ledger** (§D.1). Event objects are observed on every
     `/events` page, and fresh `/events/{e}` and `/series/{s}` objects are fetched for every
     evaluated leg.
2. **Discovery and screen.** `/events` pages are paced at ≤ 4 req/s; validation run 1 saw
   429s only here. The universe is rebuilt incrementally: specs are cached by rules/strike
   fingerprint, families by membership. The screen uses summary quotes only:
   * R1/R3 templates;
   * **pairs via `screen_pairs`** (not enumerated: 600-market crypto families would give
     180k pairs; equivalence with full enumeration is proven by a property test);
   * MECNET categorical top-3 pairs (R1 dominance).
3. **P2**, for each flagged candidate, in order of summary raw, capped at 40 per cycle
   (skipped candidates are counted):
   * the independent checker (the evaluator rejects unchecked templates);
   * `GET /markets/{t}` for each leg;
   * the legs' order books back-to-back;
   * evaluation.
4. **P3.** Persistence-eligible records are re-fetched after 1 s and re-evaluated with
   `persistence_confirmed=True`.
5. **AUDIT.** Two random families (≤ 30 markets) per cycle are evaluated from books,
   regardless of the screen. `summary_missed` counts measure the screen's false-negative rate.
6. **Streams** (`data/`, gzip JSONL):
   * `candidates`;
   * `rule511`;
   * `books` (every market and order-book response, with timings and CDN headers);
   * `statscreen` (summary-price statistical hits, deduplicated to one per key per 30 min;
     counts are kept every cycle);
   * `counts`, `ops`, `universe`;
   * `sarb_fee_ledger.json`.
7. **Unwind metric** (`evaluator.unwind_analysis`). For each leg: the conservative buy cost
   minus the conservative proceeds from selling straight back into the displayed bids (0 if
   there are none). The worst partial outcome is the sum of positive losses minus the smallest.
8. **Report.** `python -m sarb.report data/<dir>` gives:
   * statuses by phase;
   * gate failures of lock-like records;
   * direct-vs-broker edge signs;
   * unwind and size distributions;
   * 5.11 statistics;
   * ops (request rate, 429s, latencies, P2 re-fetch, skew, P3 delay);
   * integrity (every P2/P3 leg has market and book snapshots; every P3 has a P2).

## I. Final methodology audit (2026-09-27) — protocol status: **READY_TO_FREEZE**

### I.1 Every path to `RULE_DEFINED_LOCK` (sarb/evaluator.py) requires ALL of

| Requirement | Enforced by |
|---|---|
| Verified binding settlement semantics | `_terms_ok`: `terms_verified` for **every** family, including categorical MECNET (the former MECNET exemption was removed in this audit); combos never qualify; since 2026-09-29 `terms_verified` also requires an OK **filing-record** check (`sarb/filings.py`: complete fresh bucket listing equal to the reviewed filing set, controlling filing re-hashed, not inside the Reg. 40.6 waiting period) and no contradiction between the live market rules and the entry's `rules_required`/`rules_forbidden`; registry entries need a hash match at build, a documented `common_determination`, and a supported `no_data` |
| Independent checker agreement over every modelled permitted state | gate `no_checker_bug` (checker must have run, and `fast == checker`); gate `locked_guaranteed` (relationship class GUARANTEED, L ≥ 1) |
| Fresh executable order books | book integrity (HTTP 200, parsed, no CDN hit, not crossed or locked); gates `skew_ok` (≤ 2 s) and `age_ok` (≤ 5 s) |
| Depth for the modelled quantity | every leg walked to size C, and C must fill completely |
| Fee state resolved at the snapshot | gate `fees_resolved`; otherwise status `FEE_UNRESOLVED` (time-versioned ledger) |
| Positive economics under the required scenario | edge > 0 under **all** fee scenarios (the binding one is non-direct $0.01, worst-case fills) |
| Rule 5.11 | **at the same size** as the positive edge, every consumed level is within ±$0.20 of the last-trade proxy (fixed in this audit; previously only top of book was checked) |
| Timing / skew | `skew_ok`, `age_ok`, `market_active_fresh` (≤ 120 s), `exchange_status_fresh` (≤ 30 s, added in this audit) |
| Persistence | `persistence_confirmed`: only P3 re-fetches pass `True`, and only after a persistence-eligible P2 |
| No metadata / terms contradiction | gate `metadata_matches_template` (added in this audit). The fresh market body must match the fingerprint the template was built from; the event must still belong to the same series (and, for MECNET, still be mutually exclusive); the series must carry the same `contract_terms_url`; at P3 the terms PDF is re-hashed live and must still equal the registered hash |

### I.2 Nothing can fall through

* The status precedence is
  `FEE_UNRESOLVED` → `REJECTED` (data gates) → `STATISTICAL` → `CANDIDATE_TERMS_UNVERIFIED` →
  `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE`. `RULE_DEFINED_LOCK` is reached only when the list of
  failing gates is empty.
* Rate-limited or missing books are REJECTED before any price is used.
* Unsupported semantics never become templates.
* `tests/test_evaluator.py::test_no_disqualifier_falls_through_to_lock` applies 23 disqualifiers
  singly and in all 253 pairs to a scenario that is otherwise a lock: none yields
  `RULE_DEFINED_LOCK`.
* `test_rule_5_11_applies_at_the_executed_size_not_only_top_of_book` would have produced a
  false lock under the pre-audit logic.

### I.3 Reconstruction

`python -m sarb.reconstruct <data_dir>` re-derives any record from the recorded streams only:
* raw order books, market, event, series and exchange bodies with send/receive timings;
* the fee-ledger file (changes filtered by first-seen time, so no look-ahead);
* the record's provenance (semantic readings, envelopes, template hash, terms URL and hash,
  checker result, git SHA and config version).

It then re-runs semantics, the checker, fee resolution and every gate. The live audit cycle
reconstructed **29 of 29** records exactly. That run found and fixed one gap: objects reused
across candidates were not copied into each candidate's group. Tampered snapshots are detected
(test). The only input that cannot be reproduced later is the live P3 terms re-hash; its
recorded outcome is used.

### I.4 Terms registry after the audit

* Verified: **BTC.pdf, ETH.pdf** (re-keyed on 2026-09-29 to their controlling "Amendment 2" filings;
  pending independent sign-off), each with its documented common-determination basis.
* **GLOBALTEMPERATURE.pdf: SUPERSEDED (2026-09-29).** The served PDF was never updated for the
  2026-08-17 and 2026-09-02 amendments, which the live markets already follow. The entry stays pinned
  to what was reviewed, so `sarb/filings.py` reports `TERMS_SUPERSEDED` and every weather family is
  capped at `CANDIDATE_TERMS_UNVERIFIED` until a human re-review against Amendment 2 decides whether
  the material-error expiration delay still permits a common determination (edge_search/TERMS_AUDIT.md §4).
* Amendment-aware verification (`sarb/filings.py`, `scripts/terms_retro_report.py`): code can only demote.
  Recorded lock-like candidates are re-evaluated demote-only by `sarb/terms_retro.py`; on the 2026-09-27
  validation data it demotes the 47 weather R1_SHORT records (TERMS_SUPERSEDED_AT_SNAPSHOT) and the 362
  pre-audit MECNET R1_EXCLUSIVE_PAIR records (TERMS_NOT_VERIFIED_AT_SNAPSHOT).
* **INX.pdf removed.** Its expiration time "at least one minute after `<time>`", with revisions
  after expiration ignored and Kalshi as Source Agency, does not force a common determination
  instant: the same divergence channel as AAA gas.
* **Not registrable until the payoff model supports per-market No states:** CRYPTO-family terms
  whose no-data rule is per strike or per market. For example `CRYPTO.pdf`: "affected strikes
  resolve to No". The model currently has only a common ALL_NO state. Registering such terms
  would make the checker assume every leg resolves No together, when the terms allow one leg to
  resolve No alone (which breaks R2/R3/R1-long locks). `VerifiedTerms` refuses any `no_data`
  outside {ALL_NO, LAST_VALUE, DISCRETIONARY}, and requires a documented common-determination
  basis.
* AAA gas (AAAGAS.pdf) and Solana (CRYPTO.pdf) stay `TERMS_EQUIVALENCE_UNRESOLVED`
  (sources/equivalence_review/REVIEW.md).

### I.5 Remaining methodological weaknesses (known, documented, not lock-producing by themselves)

1. **Discretionary settlement, contract modification, trade cancellation and non-atomic
   execution** (Rulebook 6.3(c)/7.1/7.2/5.11) are residual by definition. They are listed on
   every record, and never modelled as lock-breaking states.
2. **The Rule 5.11 fair value is a proxy** (last traded price). Kalshi may use other
   information, so the gate can pass while the true band differs.
3. **Persistence is a single re-fetch about 1.2 s later.** Displayed depth can still vanish
   before execution.
4. **REST books are not simultaneous** (skew ≤ 2 s). Server timestamps and sequence numbers
   need authentication, which is out of scope.
5. **Terms verification is a human review of PDFs.** Hash pinning prevents silent drift, but
   not a misreading. The registry is small (3 PDFs) and each fact is cited.
6. **The text parser.** Anything unparseable is rejected. But if both the text and the fields
   were wrong in the same way, the envelope could not detect it.
7. **The fee-ledger boundary guard assumes the API reflects scheduled changes within ±60 s.**
8. **The fee bound assumes resting orders are integer-sized** unless a fractional level is
   displayed; if one is, the bound widens automatically.
