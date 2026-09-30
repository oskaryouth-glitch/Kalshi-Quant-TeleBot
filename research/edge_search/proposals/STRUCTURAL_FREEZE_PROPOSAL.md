# structural_arb: proposed freeze package (NOT FROZEN, NOT STARTED)

- **Status:** PROPOSAL, revision 2 (2026-09-29). It uses the owner's provisional choices for D2–D8.
- **Blocked by D1.**
  - 0 markets are terms-verified.
  - The existing verification protocol does **not** permit accepting the replaced BTC/ETH terms PDFs without a posted filing whose text backs them (`D1_BTC_ETH_TERMS_EVIDENCE.md`).
  - Per the owner's instruction, nothing is frozen or started while 0 markets are verified.
- **Unchanged:**
  - `research/structural_arb/`: same experiment manifest, 945/945 tests pass.
  - M6: manifest `5dcb3af7…` verifies, 61/61 tests pass.
  - H022/H038/H039 were not touched.

## 1. Identity that would be frozen

| item | value |
|---|---|
| experiment manifest (binding) | `456eafb5a669d5d96043284fab9ae574817a2c012cff6dc45506fbfa3db90582`: 66 git-tracked files of `research/structural_arb/`, excluding `data/` and `relabels/`. The list is in `STRUCTURAL_FREEZE_HASHES.txt` |
| deploy manifest (binding) | `af28161ec3471289b2287b9b642b9e498776ed81a78f8a8ae06374495c6e2f24`: the 12 git-tracked files of `proposals/structural_deploy/`, listed in `STRUCTURAL_DEPLOY_HASHES.txt` |
| manifest definition | `git ls-files` → `sha256sum` → `LC_ALL=C sort -k2` → `sha256sum`, as in `structural_deploy/verify_manifest.sh` |
| `CONFIG_VERSION` | `2026-09-29.6-amendment-aware-terms` |
| commit | Any commit whose trees hash to both manifests; it is designated at FREEZE. `structural_arb/` content is unchanged since `25267df`. The collector records the checked-out commit in every record's provenance, and evaluation requires that exact commit |

**What would change these identifiers:**
- Resolving D1 (a new registry entry keyed to a future BTC/ETH filing) changes `sarb/terms.py`. That means a new CONFIG_VERSION, a new experiment manifest, a re-run of the suite, and your review.
- Any change to the deploy files changes the deploy manifest.

## 2. Configuration and protocol (unchanged, as coded)

- **Configuration:** `sarb/config.py`, as tabulated in revision 1.
  - Rates: 5 req/s, burst 6.
  - Cycle target: 60 s.
  - P2 cap: 40 candidates per cycle.
  - AUDIT: 2 families, ≤ 30 markets each.
  - Persistence re-fetch after 1 s.
  - Freshness: skew ≤ 2 s, age ≤ 5 s.
  - `SIZE_GRID` (1, 10, 100).
  - Fee coefficients: taker 0.07, maker 0.0175.
  - Filing listing ≤ 2 h old.
  - Amendment pending period: 16 days.
- **Protocol:** DESIGN.md §H (collection), §C and §I (labels, gates and the only path to `RULE_DEFINED_LOCK`), §I.3 (reconstruction).
- **Inclusion and exclusion:** as in revision 1.
  - Only registry-verified series with filing status `OK` can reach `RULE_DEFINED_LOCK`.
  - **Weather/GLOBALTEMPERATURE stays excluded (D7)** as `TERMS_SUPERSEDED`.
  - INX is removed.
  - AAA gas and CRYPTO.pdf stay unresolved.
  - Combos never qualify.

## 3. Provisional choices adopted (D2–D8)

| | choice | implemented by |
|---|---|---|
| D2 | 28-day collection: END_UTC = START_UTC + exactly 28 × 24 h. Downtime is not made up | `start.sh`, `run.sh`, `sarb_ops.read_window` |
| D3 | one formal evaluation at END_UTC + 24 h, with the criteria in §4; no interim peeking; operational-health monitoring only | `sarb_ops.evaluate` (refuses earlier), `sarb_ops.health` (ops and universe streams only; other streams raise `PermissionError`) |
| D4 | dedicated host and public IP, separate from M6 and H038/H039; request limit **unchanged** | `preflight.sh` G7 |
| D5 | isolated deployment modelled on M6: approval-file gate, timed stop, manifest re-verification on every start | `structural_deploy/` (outside the experiment tree) |
| D6 | ≥ 100 GB free at START | `preflight.sh` G1 and `start.sh` |
| D7 | GLOBALTEMPERATURE/weather excluded | registry, unchanged |
| D8 | ≥ 30-minute validation on the target host, with a mid-way restart; data deleted afterwards | `validate.sh` (refuses < 30) |

**Measured footprint** (tooling smoke test, 2 cycles; the data was deleted):
- about 13 KB/s, so ~31 GB over 28 days;
- the 100 GB START requirement is about a 3× margin;
- 2.2 req/s mean against the unchanged 5 req/s cap;
- 1 × 429 in 661 requests.

## 4. Exact pre-specified evaluation criteria (proposed; implemented in `sarb_ops.evaluate`; 31 tests, synthetic plus end-to-end fixtures)

### 4.1 Definitions

- **Window W** = [START_UTC, END_UTC]. Records logged after END_UTC are excluded and counted.
- **Qualifying lock (QL):** a `candidates` record meeting **all** of:
  1. `status == RULE_DEFINED_LOCK` and `phase == P3`. Only a P3 re-fetch can pass the persistence gate.
  2. `logged_utc_ns` is in W.
  3. Code identity: provenance `git_sha` = the frozen commit, `dirty == False`, and `config_version` = the frozen CONFIG_VERSION.
  4. Every leg recorded `terms_status == TERMS_VERIFIED` **and** `terms_filing_status == OK` at the snapshot.
  5. `sarb.reconstruct` re-derives the record exactly from the recorded streams (status, edges by size, max size, the 5.11 size, all gates). Every source response the replay uses was recorded with HTTP 200, and a replay exception disqualifies the record (added 2026-09-30 with option B; it can only exclude records).
  6. The demote-only `sarb.terms_retro` check against the bucket listing at evaluation time leaves it standing.
  7. It is not demoted by the **late-filing review**: a human reads every BTC/ETH regulatory object posted after the record's filing set. If that filing's effective date (or, if none is stated, its filing date + 10 business days) is at or before the snapshot, the record is demoted. This is demote-only, and the review file is required even if it demotes nothing.
- **Verified exposure E:** total time in W during which the latest `universe` snapshot showed ≥ 1 terms-verified market. Stretches across a gap > 300 s do not count.
- **Downtime:** every gap longer than 300 s between consecutive `ops` records, including START → first record and last record → END.

### 4.2 Validity conditions

| id | condition |
|---|---|
| V1 | total downtime ≤ 72 h **and** longest single gap ≤ 24 h |
| V2 | in every rolling 24 h window, 429 responses / requests ≤ 1% |
| V3 | every candidate record in W carries the frozen CONFIG_VERSION, and every one with provenance (P2/P3) carries the frozen commit with `dirty == False` |
| V4 | ≤ 1% of P2/P3 records lack their leg market/orderbook snapshots, or are P3 without a P2 |
| V5 | cycle errors ≤ 5% of cycles |

### 4.3 Verdict (evaluated in this order; exactly one applies)

| verdict | rule | meaning |
|---|---|---|
| **INVALID** | V3 fails | The run is not the frozen experiment. No conclusion either way |
| **SUCCESS** (null rejected) | ≥ 1 QL | At least one rule-defined lock existed at displayed, executable prices after fees, depth, Rule 5.11, timing and persistence, under verified terms. It is exactly reconstructable. It is **not** a profitability or tradability claim: the residual risks (6.3(c)/7.1/7.2/5.11, non-atomic execution) are unchanged. Existence does not need coverage, so V1/V2/V4/V5 and E do not block it; they are reported |
| **FAILURE** (null not rejected) | 0 QL **and** V1, V2, V4, V5 all hold **and** E ≥ 21 days | No rule-defined lock was observed in 28 days of adequate, verified collection |
| **INSUFFICIENT_EVIDENCE** | otherwise: 0 QL, with a validity failure or E < 21 days | Absence cannot be claimed. With D1 unresolved, E = 0, so a run started now would certainly end here |

### 4.4 Timing and reporting

- Evaluation opens at END_UTC + 24 h and runs **once**.
- The verdict is computed first. Afterwards the evaluator attaches a descriptive report that cannot change the verdict:
  - `sarb.report` statuses by phase;
  - gate-failure breakdown of `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE`;
  - AUDIT screen misses;
  - P2 budget skips;
  - Rule 5.11 statistics, which are never used to loosen the gate;
  - per-QL relationship, size and edges;
  - the number of distinct QL keys (relationship × legs).
- `CANDIDATE_TERMS_UNVERIFIED` counts are **not** evidence for SUCCESS.
- No re-run, extension or re-analysis with different rules. A second collection would need a new pre-registration.

### 4.5 During collection

- Health output only: ops, universe and disk.
- No config, rate or code change.
- Operator actions are limited to crash or reboot restarts, freeing unrelated disk, or stopping for host harm (recorded as downtime).

## 5. Decisions and what is needed next

1. **D1, blocking.** No action is possible under the current protocol. Wait for Kalshi to post a BTC/ETH amendment that backs the new text, or for the served copies to revert. Then do a human re-review and write a new registry entry for your sign-off; the 16-day pending rule applies.
   - Alternatively, you may explicitly decide to **change the verification standard**. I have not proposed or made such a change.
2. **Approve or amend the parameters I introduced to make D2/D3/D6/D8 executable.** None comes from performance data.
   - SUCCESS threshold ≥ 1 QL.
   - FAILURE exposure ≥ 21 days.
   - V1: 72 h total downtime, 24 h single gap, 300 s gap definition.
   - V2: 1%.
   - V4: 1%.
   - V5: 5%.
   - Evaluation at END + 24 h.
   - The late-filing review rule (4.1 item 7).
   - Host resource caps (3 GB RAM, 1 CPU) and preflight G2 (≥ 4 GB available).
   - The host-separation check (public IP via `checkip.amazonaws.com`, plus unit and directory checks).
3. **Review the deployment package** (`structural_deploy/`, deploy manifest in `STRUCTURAL_DEPLOY_HASHES.txt`).
4. **Provide a dedicated host.** Then have the operator run preflight, install, and the ≥ 30-minute validation, and return both reports.
5. **FREEZE.** Only after 1–4: designate the commit, record both manifests in a PREREG file, then give final START approval via `start.sh`.
