# structural_arb: proposed freeze package (NOT FROZEN, NOT STARTED)

- **Status:** PROPOSAL.
  - Nothing in `research/structural_arb/` was changed to produce it.
  - No collection is running.
  - No infrastructure is provisioned.
- **Prepared:** 2026-09-29.
- **Separation:** H022/H038/H039 are untouched. M6 is untouched (manifest `5dcb3af7…` still verifies).
- **Blocker, see D1:** as the code stands, **0 markets are terms-verified**, so the frozen protocol could not produce a `RULE_DEFINED_LOCK`. Fixing that needs a registry change, which is the owner's decision. It has not been made.

## 1. Exact identity that would be frozen

| item | value |
|---|---|
| git commit | `0ae71707b59b983864078257ed84caea2861e52e`. structural_arb content is unchanged since `25267df` (terms patch `3f3f44a` plus relabel ledger) |
| `CONFIG_VERSION` | `2026-09-29.6-amendment-aware-terms` |
| code/doc manifest | `456eafb5a669d5d96043284fab9ae574817a2c012cff6dc45506fbfa3db90582` |
| manifest definition | sha256 of the 66 lines `sha256  path` (`sha256sum` output, sorted by path) for every git-tracked file under `research/structural_arb/` except `data/` and `relabels/`. The list is in `STRUCTURAL_FREEZE_HASHES.txt` |
| regenerate | `cd research/structural_arb && sha256sum $(git ls-files \| grep -v '^data/\|^relabels/') \| sort -k2 \| sha256sum` |
| test suite at this version | `python -m pytest -q tests` → **945 passed** (2026-09-29) |
| relabel ledger (historical, not an input) | `relabels/2026-09-29_terms_v2_relabel.jsonl` (409 demote-only records) |

If D1 is resolved by editing `sarb/terms.py`, then a new CONFIG_VERSION, commit and manifest replace the three identifiers above. That package then needs its own review before the freeze.

## 2. Configuration (`sarb/config.py`, as frozen)

| parameter | value | parameter | value |
|---|---|---|---|
| MAX_REQUESTS_PER_SECOND | 5 | MAX_REQUEST_BURST | 6 |
| CYCLE_TARGET_S | 60 | MAX_PHASE2_CANDIDATES_PER_CYCLE | 40 |
| AUDIT_FAMILIES_PER_CYCLE | 2 | AUDIT_MAX_MARKETS_PER_FAMILY | 30 |
| SERIES_REFRESH_S | 21600 | TERMS_REFRESH_S | 3600 |
| MAX_FILINGS_LISTING_AGE_S | 7200 | AMENDMENT_PENDING_S | 1382400 (16 d) |
| FEE_CHANGES_REFRESH_S | 300 | EVENTS_PAGE_MIN_INTERVAL_S | 0.25 |
| STATSCREEN_REWRITE_S | 1800 | OBSERVATION_REUSE_S | 10 |
| MAX_LEG_SKEW_NS | 2e9 (2 s) | MAX_SNAPSHOT_AGE_NS | 5e9 (5 s) |
| PERSISTENCE_REFETCH_DELAY_S | 1.0 | SIZE_GRID | (1, 10, 100) |
| TAKER_COEF / MAKER_COEF | 0.07 / 0.0175 | fee rounding units | 0.01 default, 0.0001 alternative |

Gates that live in code rather than config:
- Rule 5.11 band ±$0.20 at the executed size;
- market-active freshness ≤ 120 s;
- exchange-status freshness ≤ 30 s.

## 3. Protocol (already defined; would be frozen as is)

- **Collection:** `research/structural_arb/DESIGN.md` §H.
  - Refresh cadences.
  - Discovery and summary screen (R1/R3 templates, `screen_pairs`, MECNET top-3).
  - P2 books for ≤ 40 flagged candidates per cycle.
  - P3 independent re-fetch after 1 s.
  - AUDIT of 2 random families per cycle (screen false-negative rate).
  - Streams: `candidates`, `rule511`, `books`, `statscreen`, `counts`, `ops`, `universe`, fee ledger.
  - Unwind metric; report.
- **Labels and gates:** DESIGN §C and §I.1/I.2. `RULE_DEFINED_LOCK` needs every gate:
  - verified terms, including an OK filing-record check;
  - checker agreement;
  - fresh books;
  - full depth at size C;
  - fee state resolved;
  - edge > 0 under every fee scenario;
  - Rule 5.11 at the size;
  - skew/age/activity/exchange freshness;
  - P3 persistence;
  - metadata/terms match, including a live terms re-hash at P3.
- **Reconstruction:** DESIGN §I.3. `python -m sarb.reconstruct <data_dir>` re-derives every record from the recorded streams.
- **Report:** `python -m sarb.report <data_dir>`.
- **Invocation:** `python -m sarb.collector --duration-s <S> --data-dir <DIR>`, public unauthenticated GETs only. The CLI has no absolute end time and no approval gate (see D5).

## 4. Inclusion and exclusion rules (as coded)

**Included in discovery:**
- every open event from `/events`;
- only active binary $1 markets become legs;
- families come from parsed strike semantics (numeric ladders; MECNET categorical events);
- anything unparseable is rejected and never templated.

**Can reach `RULE_DEFINED_LOCK`:** only series whose `contract_terms_url` is in `REGISTRY`, whose hash matches, and whose filing-record status is `OK` at the snapshot.

**Capped at `CANDIDATE_TERMS_UNVERIFIED`:**
- every other series;
- **GLOBALTEMPERATURE / all weather:** `TERMS_SUPERSEDED`, left excluded as instructed (D7);
- **INX:** removed from the registry;
- **AAA gas, Solana/CRYPTO.pdf:** `TERMS_EQUIVALENCE_UNRESOLVED`, or a per-strike no-data rule the payoff model cannot represent.

**Never qualify:** combos (multivariate events).

**Rejected per snapshot:** see the REJECTED row of DESIGN §C.

## 5. Decisions needed from the owner before the freeze

### D1. BLOCKER: BTC/ETH `contract_terms` objects changed on 2026-09-29. Stop-and-show; nothing was changed.

**Observed:** during the post-patch live validation, `filings.status()` returns `TERMS_FILING_CHANGED` for BTC and ETH. The result is **0 verified markets out of 117,933**, so no record can reach `RULE_DEFINED_LOCK`.

**Cause:** in the regulatory bucket, two objects were replaced with no new regulatory filing posted:

| object | reviewed | now (LastModified 2026-09-29) |
|---|---|---|
| `contract_terms/BTC.pdf` | 24,445 B, sha `e7d85736…` | 20:38:36Z, 38,090 B, sha `7bba1b81…` |
| `contract_terms/ETH.pdf` | 24,347 B, sha `ae079241…` | 20:38:52Z, 37,895 B, sha `74bae3f5…` |

- The CDN URL the registry is keyed on (`assets.kalshi.com/contract_terms/*.pdf`) **still serves the reviewed PDFs**, so the P3 live re-hash passes for now. It will fail once the CDN refreshes.
- **Text diff, one sentence per template:**
  - old: "Position Limit: … $1,000,000 per strike, per Member";
  - new: "Position Accountability Level: … $25,000 per strike, per Member".
- Expiration, source agency, no-data (ALL_NO), payout criterion and settlement wording are otherwise identical.
- On my reading this does not change settlement semantics. Accepting it is still a change to the verified registry.

**Options:**
- **(a) Accept.** Re-review the new PDFs.
  - Update the `contract_terms/*.pdf` entries in `_BTC_FILINGS`/`_ETH_FILINGS` (LastModified, size).
  - Decide whether to re-key the entry sha to the new PDF now or when the CDN serves it. Both hashes cannot be accepted silently; one option is to register both hashes explicitly with a note.
  - Bump CONFIG_VERSION, re-hash, and re-validate.
- **(b) Freeze as is.** BTC/ETH stay fail-closed, the experiment can only yield `CANDIDATE_TERMS_UNVERIFIED` and below, and the lock null cannot be rejected. I would not recommend spending a collection on this.
- **(c) Defer the freeze** until Kalshi posts a filing or the CDN converges, then re-review.

**Related (D1b).** The BTC/ETH `reviewed` text still reads "PROPOSED 2026-09-29 … REQUIRES independent reviewer sign-off".
- The reviewer approved the Amendment 2 re-key, but that string has not been updated to record the sign-off.
- Recommendation: record the sign-off (who and when) in the same registry edit as D1(a).
- It is text only; the code does not gate on it.

### D2. Collection duration: not pre-specified anywhere

- Recommendation: **28 days** of wall clock from START, including a full monthly crypto expiry cycle and 4 weekly cycles.
- Downtime is recorded and not extended.
- The run is **invalid** if cumulative downtime exceeds 3 days, or any single gap exceeds 24 h.

### D3. Evaluation schedule and decision rule: not pre-specified

Recommendation:
- **One formal evaluation**, at the end of collection only.
- **Primary result:**
  - the null ("no rule-defined lock exists at displayed prices") is rejected iff there is ≥ 1 `RULE_DEFINED_LOCK` record;
  - that record must be exactly reconstructable by `sarb.reconstruct`;
  - its terms must have been verified (filing status `OK`) at the snapshot.
- **Also reported:**
  - count, size and edge distribution of locks;
  - the `GUARANTEED_STRUCTURAL_NOT_EXECUTABLE` gate-failure breakdown;
  - screen false-negative rate (AUDIT);
  - Rule 5.11 statistics (never used to loosen the gate).
- **During collection:** ops-only monitoring of request rate, 429s, errors, disk and integrity. No status counts are read before the end.
- **Invalid-run rule:** as in D2, plus a sustained 429 rate > 1% of requests over any 24 h.

### D4. Host and request rate

- The config allows 5 req/s. Validation runs saw 2.1–3.7 req/s.
- If it runs on the `kalshi-collector` host, it would share one public IP with M6 (2 req/s) and H038/H039.
- Recommendation: **a separate host/IP.** Any change to MAX_REQUESTS_PER_SECOND is a config change and needs new validation. I have not made one.

### D5. Deployment package: none exists yet

Recommendation: an M6-style isolated unit, which is new operational files, not protocol changes:
- own user, directory and syslog id;
- resource caps;
- an `APPROVED` file equal to the manifest, checked in `ExecStartPre`;
- a manifest-verifying install;
- `--duration-s` computed from the approved end time;
- `Restart=on-failure`. Each restart continues into the same data dir, and the fee ledger reloads from `sarb_fee_ledger.jsonl`.

These files would be added to the manifest before the freeze.

### D6. Storage

- Measured footprint is 0.33–1.1 GB/day, so 9–32 GB over 28 days.
- Proposed preflight: **≥ 3 × 32 GB ≈ 100 GB free** on the data filesystem, or a smaller duration.

### D7. Weather (GLOBALTEMPERATURE)

Already fail-closed (`TERMS_SUPERSEDED`); left excluded as instructed. No action or delay.

### D8. Target-host operational validation

- A ≥ 30-minute validation on the target host, with a mid-way restart, then delete the data and keep only a sha256 list.
- It checks:
  - manifest verify;
  - no order/credential code;
  - 429s and cycle errors;
  - gzip integrity;
  - reconstruct of all P2/P3 records;
  - `filings.status` for each registry entry.

## 6. What happens at FREEZE and START

1. The owner decides D1–D6 and D8.
2. The implementing decisions (D1 registry edit, D5 deploy files) get a new CONFIG_VERSION, commit and manifest. The suite is re-run and results returned.
3. FREEZE: the manifest, D2/D3 rules and deployment procedure are recorded in a `PREREG` file alongside this proposal.
4. Host preflight, then install (disabled), then D8 validation. The report goes to the owner.
5. START: only on the owner's explicit approval, via the `APPROVED` file.
