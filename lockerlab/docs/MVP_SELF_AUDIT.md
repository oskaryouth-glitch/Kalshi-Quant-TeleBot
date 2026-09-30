# Daily-use MVP: what was built, self-audit, open issues

## Built

| Area | Where | Notes |
|---|---|---|
| Local desk app | `lockerlab serve`, `lockerlab/web/` | FastAPI + server-rendered pages, 127.0.0.1 only. Every write goes through the same audited functions as the CLI |
| URL + screenshot capture | `intake.py`, `platforms.py`, `extract.py` | URL parsed locally (never fetched). Screenshots stored/read only where the source's policy allows. Model transcribes; deterministic code parses. Per field: value, text, confidence, evidence, status (found / not visible / invalid / ambiguous / inferred) |
| Capture policy | `platforms.capture_policy`, Sources page, `lockerlab source-policy` | Config default + append-only policy events with basis and note. StorageTreasures/Lockerfox manual-only (terms); unreviewed sources manual-only |
| Quick underwriter | `quick.py` (`quick_v1`) | 5 inputs + tags → same cost model and max-bid solver as before |
| Opportunity score | `quick.opportunity_score` | 9 named components with point values and reasons; attention only (tested: never changes max bid) |
| Decisions | `paper.decide(..., choice=)` | PAPER BID / WATCH / PASS recorded with snapshot, estimate, max bid, model recommendation, model version. Pass tags required. Paper bid ≤ max bid and > current bid + increment. `triage_v1` = pass/watch without estimate |
| Results | `intake.record_result`, `settlement_summary` | Sold / cancelled / no bids / unknown → observation → `settle_v1`; shows would-have-won, simulated prices, margin, ESTIMATED profit |
| Dataset health | `desk.health` | Counters + 100-closed-small-unit checkpoint bar |
| Calibration | `desk.calibration` | Max bid ÷ price and estimate ÷ price by tag, messy/organized, size, visible value, confidence; rank correlation; pass reasons; missed deals; gated at n < 10 |
| Filters | `desk.Filters` | Default 5x5 + 5x10; bid, time, disposal, fits SUV, category, min cash, ROI, confidence |
| Assumptions panel | `assumptions.py` | 31 editable values; append-only override sets; status incl. "Your assumption"; future decisions only; retrospective table |
| Readiness | `desk.readiness` | 11 evidence items, first-hand checks, timed-selling log, unresolved assumptions, source status. Never says buy |
| Resale skeleton | `migrations/003_resale_skeleton.sql`, `resale.py` | Append-only event tables; no workflow; no posting method exists |
| Schema v2/v3 | `migrations/002`, `003` | `raw_captures` rebuilt by copy-and-swap to add capture types (tested: v1 rows preserved, triggers restored, FKs intact) |

Tests: 259 (was 166). New: extraction parsing and time zones (including DST),
client wrapper (refusal, truncation, bad JSON), URL parsing, policy gating
(even if the UI is bypassed), provenance labels, duplicates (same ID, same
file, cross-listing, URL-hash IDs), results/settlement (sold before end
refused, cancelled early = VOID, unknown stays unsettled), decision guards,
look-ahead with late captures, assumption changes leaving old decisions
byte-identical, desk sections/filters/health, calibration gating, readiness
wording, web end-to-end, and the v1 → v3 migration.

## Self-audit: issues found and fixed during the build

1. The heavy disposal profile had half the mattresses and sofas the audit
   specified for a 5x10 (a config error; caught by a test).
2. An untouched, URL-prefilled auction ID was labelled "user entered" (now
   URL_DERIVED).
3. The desk showed economic profit *at the max bid*, which is ≈ $0 by
   construction because the $/h rule solves for it. Cards and the
   calculator now show figures at the current bid, with the max-bid case
   alongside.
4. The opportunity score treated a valid $0 max bid as "no bid".
5. Your age (19) removes Home Depot rentals. Rental-scenario grids were
   regenerated (−$35 to −$37 per locker); the audit has a dated addendum.

## Known limitations and methodology risks (not fixed; your call)

| # | Issue | Why it matters | Suggested handling |
|---|---|---|---|
| 1 | **The fast path is off for most local inventory.** StorageTreasures and Lockerfox terms restrict extraction/copying | Manual typing is ~40–60 s per auction, not < 30 s. No stored photos means Phase-2 AI image analysis can't run on StorageTreasures data | Send the permission emails. Review Bid13/iBid/StorageAuctions terms yourself and record the result |
| 2 | **Anchoring.** You see the current bid while estimating | Estimates drift toward bids; calibration's "estimate ÷ price" and rank correlation look better than reality | Estimate before looking at the bid where you can; treat those two metrics with suspicion. A blind-estimate mode is possible later |
| 3 | **Selection bias.** Only auctions you capture exist in the data | Market prices skew toward what caught your eye | Capture every small unit in the listing order, not just interesting ones |
| 4 | Settlement happens once per rule | A later contradicting result (won, then tenant paid) won't re-settle | `settle_v2` with "won then cancelled" (recommended next) |
| 5 | `observed_at` = when you started the capture, not when the screenshot was taken | Conservative for look-ahead (data looks later, never earlier) | None needed |
| 6 | Extraction runs while you wait (10–40 s) | Slower capture where it's allowed | Background job later if it matters |
| 7 | No login or CSRF protection on the desk | Fine on 127.0.0.1; unsafe on a shared network | `serve --host` warns; keep it local |
| 8 | Quick-estimate volume mapping (disposal level → trash/donate share) and score thresholds are guesses | They shape max bids and ordering | Visible in config; replace with real-unit data |
| 9 | The $25/h hurdle binds almost everywhere | Max bids will be low and paper wins rare. That's a finding about selling labor, not a bug | Your setting. Run your timed-selling experiment before changing it |

## Blocked by platform permissions

| Blocked | Needs |
|---|---|
| Screenshot reading and stored photos for StorageTreasures, Lockerfox | Written permission |
| Same for Bid13, iBid4Storage, StorageAuctions.com | You reading their terms (or permission), recorded on Sources |
| Any automated discovery or bid-history snapshots | Written permission or API access (none granted) |
| Historical sale prices (backtesting) | Facility cooperation or platform data access |
| AI image analysis of StorageTreasures listings (Phase 2) | StorageTreasures permission |
