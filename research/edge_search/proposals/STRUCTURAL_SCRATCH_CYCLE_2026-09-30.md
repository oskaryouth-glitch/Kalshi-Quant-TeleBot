# structural_arb: post-terms-fix live scratch cycle, 2026-09-30

- **Status:** operational check only. The long collection is **not** started, and nothing is frozen.
- The data was written to a session scratch directory, **deleted** after checking, and never committed. `structural_scratch_cycle_2026-09-30_files.sha256` lists its files.
- `research/structural_arb/` is unchanged: `VALIDATION.md` is inside the frozen manifest, so the result is recorded here instead.
- H038/H039 and M6 were not touched.

| item | value |
|---|---|
| run | `python -m sarb.collector --duration-s 60 --data-dir <scratch>`: one cycle, 2026-09-30 15:21:29Z to 15:24:24Z |
| code | commit `170ee13`, `dirty=False` on every P2 record; CONFIG_VERSION `2026-09-29.6-amendment-aware-terms`; experiment manifest `456eafb5…` verified; suite 945/945 |
| cycle | 174.4 s, 338 requests (1.94 req/s against the 5 req/s cap), **0 cycle errors** |
| 429s | **9 (2.7%)**: `/events` 4, `/markets/{t}` 2, orderbook 2, `/series/{s}` 1; each triggered a limiter cooldown (9 cooldowns), and the 429 responses were recorded as observed. Earlier runs saw 0–1 per 330–660 requests |
| universe | 12,644 events; 120,271 markets; 6,598 families |
| terms | **0 terms-verified markets**. BTC and ETH are `TERMS_FILING_CHANGED`; GLOBALTEMPERATURE is `TERMS_SUPERSEDED`. No new BTC/ETH filing is posted (D1 unchanged) |
| integrity | 7 gzip streams read completely; 0 P2/P3 records missing leg snapshots |
| records | 38 P2 records, 0 P3; `RULE_DEFINED_LOCK` records: 0 (impossible with 0 verified markets) |
| reconstruction (`sarb.reconstruct`, per record) | **35/38 exact**, 2 mismatch (`MISSING_SNAPSHOT`), **1 crash** (`KeyError: 'ticker'`) |

## Anomaly: `sarb.reconstruct` cannot replay rate-limited P2 groups

- All 3 non-exact records are in groups where a leg snapshot was rate-limited (HTTP 429).
- **The live collector handled every such record fail-closed.**
  - 5 records sat in groups with a non-200 snapshot: 4 became `REJECTED` and 1 `FEE_UNRESOLVED`.
  - None reached a lock-like status.
- The frozen reconstruction tool treats a recorded non-200 response in two ways:
  - **as absent** (orderbook/market) → `MISSING_SNAPSHOT` mismatch;
  - **as a body** (series): `reconstruct.py` then passes the 429 error body `{"error": …}` to `FeeLedger.observe_series` → `KeyError` → the tool **crashes**.

**Consequences:**
- **Lock path (evaluation criterion 4.1-5): no effect.** A `RULE_DEFINED_LOCK` requires HTTP-200 books (else `REJECTED`) and a resolved fee state (else `FEE_UNRESOLVED`), so a lock can never come from such a group.
- **Proposed D8 validation: blocks it.** `validate.sh` / `sarb_ops.validate` reconstructs *all* P2/P3 records and aborts on the crash. At the 429 rate seen today, a ≥ 30-minute validation would almost surely hit one.

**Nothing was changed.** The options are for the owner:
- **(A) Fix the frozen tool.** `sarb/reconstruct.py` would replay non-200 snapshots exactly as the collector observed them, and never raise. This changes the experiment manifest and CONFIG_VERSION, and needs review.
- **(B) Leave the frozen experiment untouched and amend only the unfrozen deploy proposal.**
  - `sarb_ops.validate` would isolate per-record exceptions.
  - Its pass criterion would become:
    - every P2/P3 record whose group snapshots are all HTTP 200 reconstructs exactly;
    - every record with a non-200 snapshot has a fail-closed live status (`REJECTED`/`FEE_UNRESOLVED`);
    - crashes are counted and reported.
  - This changes only the deploy manifest `c440969d…`.
  - Recommended, because the lock path is unaffected.
