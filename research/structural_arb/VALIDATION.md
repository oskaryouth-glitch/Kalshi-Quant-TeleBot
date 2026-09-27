# Operational validation (2026-09-27) — NOT a research result

Short runs to validate the collector before freezing the protocol. They are **not** the long
collection, and nothing here is a finding about the prevalence of arbitrage.

| Run | Code | Duration | Outcome |
|---|---|---|---|
| 1 | initial collector | 1 cycle | 8×429 on /events pages; statscreen 4 MB/cycle → pacing + dedup added |
| 2 | + pacing/dedup, old fee floor | 6 cycles | 0×429; stopped because the fee design changed |
| 3 | + time-versioned fee ledger | 1.5 cycles | 24×429 on burst leg re-fetches; one cycle failed on /events 429 → global cool-down, 5 req/s, burst 6 |
| **4** | final (commit d65f7d7) | **22 cycles / 30 min** | see below |

## Run 4

**Requests**

| Metric | Value |
|---|---|
| Cycles | 22, with 0 cycle errors |
| Requests | 6,612, at ≈3.7 req/s (max per cycle 3.83) |
| HTTP 429 | 11 in total: 8 on /events pages (retried and recovered); 3 on leg order books (those candidates rejected, never priced) |
| Other non-200 responses | none |
| Endpoint latency, median p50 | ≈75–90 ms (/series list ≈210 ms) |

**Cycle timing**

| Metric | Value |
|---|---|
| Cycle length | p50 81 s, max 144 s (the first cycle includes the one-time 48 s universe build) |
| Phase split, p50 | events 26 s, screen 9 s, P2/P3 43 s, audit 3 s |
| P2 leg re-fetch (metadata, books, event/series objects) | n = 655, p50 409 ms, p95 1.68 s |
| Book skew across legs | p50 228 ms, p95 1.07 s (the gate is 2 s) |
| P3 persistence re-fetch after P2 | n = 77, p50 1.22 s, p95 1.54 s |
| Candidates skipped for budget | 0 |

**Integrity and fees**

| Check | Result |
|---|---|
| P2/P3 records missing a leg snapshot | 0 |
| P3 records without a matching P2 | 0 |
| Universe and count snapshots | 22 each, one per cycle |
| FEE_UNRESOLVED | 0 (every leg had fresh event and series objects) |
| Fee ledger | 393 scheduled changes stored |
| Storage | ≈7 MB per 30 min (books 3.2, statscreen 2.2, candidates 1.3), i.e. ≈340 MB/day |

**Screen audit.** 25 book-level displayed inconsistencies were found in random families; the
summary screen had flagged 24. The one miss was a non-guaranteed R1_SHORT (STATISTICAL).

**Live fee-state check at 18:30 UTC.** The six scheduled MLB event overrides left
`/events/fee_changes` at their effective time, and appeared on the event objects (M=1 vs a
series M of 0.5). The list endpoint matched the objects in 4 of 4 events checked.

## Observations to review before freezing

(Observed over 30 minutes; not research conclusions.)

* **No `RULE_DEFINED_LOCK`.**
* The persistent candidates are cross-series pairs:
  * KXAAAGASD vs KXAAAGASW, and KXAAAGASDNJ vs KXAAAGASWNJ (R2 and R4);
  * KXSOL26500 vs KXSOLD26 (R2).

  Every gate passes except terms verification. These series are not in the verified terms
  registry, so they are capped at `CANDIDATE_TERMS_UNVERIFIED`. Settlement equivalence of
  these series needs the (UltraCode) terms review.
* **Direct vs broker rounding.** 171 lock-like P2 records had a positive direct-member edge
  at size 1 but a non-positive broker-cleared edge. Some become positive at larger sizes, so
  account rounding does change conclusions at small size.
* **Rule 5.11.** It blocked 46 P2 records, but it was never the only failing gate.
* **Statistical screen noise.** Most statscreen hits are R1 templates on events that are
  threshold ladders (not partitions), where R1 has no nominal meaning.

## Methodology audit, 2026-09-27

After the audit fixes (DESIGN.md §I), one live cycle was run:

* 0 cycle errors, 1 × 429 (retried);
* snapshot integrity complete;
* **29/29 logged records reconstructed exactly** by `sarb.reconstruct`;
* no `RULE_DEFINED_LOCK`.

The verified-terms markets dropped from 2,533 to 1,256 after INX was removed from the registry.

**Protocol status: READY_TO_FREEZE.** The long collection has NOT been started and no
infrastructure has been provisioned.
