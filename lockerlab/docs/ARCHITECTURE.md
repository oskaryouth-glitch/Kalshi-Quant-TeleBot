# Architecture

## 1. Choices and why

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11, stdlib-heavy (only PyYAML + tzdata at runtime) | Cheap, auditable, runs on any laptop |
| Storage | **SQLite** (one file, WAL, STRICT tables) | Zero cost. It enforces the integrity rules we need (CHECK constraints, append-only triggers, foreign keys) and backs up with a file copy. Move to Postgres only if several writers ever need it |
| Raw evidence | Content-addressed files `data/raw/<sha[:2]>/<sha>`, read-only, re-hashed on read | Originals can't be silently replaced |
| Interface | CLI (`lockerlab …`) now; FastAPI + a simple web UI later | The spec says no dashboard before reliable data. A CLI is enough to accumulate evidence |
| Background jobs | None yet (manual capture). Later: cron / systemd timer or GitHub Actions for **authorized** collectors only | Keep infrastructure at $0 |
| AI (Phase 2+) | Vision/LLM API called per auction photo, with structured JSON output validated against a schema | Pay per use; no GPU |
| Config | YAML with `{value, status, source}` leaves; git history = audit trail | Every number shows whether it's VERIFIED, SOURCED, UNVERIFIED or a GUESS |

**Estimated running cost today: $0.** Phase 2 adds vision-API cost per image
(price it before starting; batch and cache so each image is analyzed once per
model version).

## 2. Data flow

```
browser (you) ──CSV──► capture.import_csv ──► raw_captures (+ file in raw store)
                                          └─► auctions (identity) + auction_observations (snapshots)
saved photos ────────► capture.import_photos ─► raw_captures + images
authorized feed ─────► collectors.PoliteClient (gate: sources.yaml) ─► same tables   [none authorized yet]

pit.snapshot_as_of(t) ─► strategy (pure fn) ─► paper.decide ─► paper_decisions (+ model_versions)
outcome observations ─────────────────────────► paper.settle_all ─► paper_settlements
reports.* (every figure labelled OBSERVED / INFERRED / ESTIMATED / SIMULATED / REALIZED)
```

## 3. Integrity mechanisms

1. **Append-only tables.** Triggers abort UPDATE/DELETE on all evidence
   tables. Corrections are new observations; history is never lost.
2. **Two timestamps.** `observed_at` ≤ `recorded_at`, enforced by CHECK. All
   timestamps are fixed-width UTC strings, so string order equals time order.
3. **Raw before parsed.** The exact file you captured is stored and hashed.
   Each observation keeps `raw_fields_json` (the exact strings) and
   `field_meta_json` (label + confidence per field), plus `parser_version`.
4. **Model versions.** Code hash + config hash identify a model. Decisions
   reference the version that made them and embed their full inputs, so any
   decision can be re-derived (`paper.reevaluate`).
5. **Migrations are immutable.** Editing an applied migration is detected by
   hash and refused.
6. **Import is all-or-nothing.** A file with one bad row writes nothing and
   lists every error.
7. **Privacy by construction.** Columns for occupant/tenant names are refused.
   `data/` is git-ignored, so photos and raw pages never leave your machine
   unless you copy them.

## 4. Schema (v1, implemented)

See `lockerlab/migrations/001_init.sql` for the exact DDL.

| Table | Purpose |
|---|---|
| `sources` | Registered auction sources (compliance status lives in config/sources.yaml) |
| `raw_captures` | One row per captured artifact: file hash, path, method, who, when |
| `auctions` | Identity only: (source, external_id), market |
| `auction_observations` | Snapshot of what the page showed: status, size, bids, fees, deadlines, description, final price (sold only) |
| `bid_events` | Bid history if visible (schema only; no import path yet. Bidder aliases must be stored only as salted hashes) |
| `images` | Auction photos, linked to raw evidence |
| `model_versions` | Code + config identity of every model that produced a stored number |
| `paper_decisions` | What we would have done, when, on what information, and why |
| `paper_settlements` | Decision vs observed outcome under a versioned rule |

## 5. Schema (planned, added as new migrations when each phase starts)

| Phase | Tables |
|---|---|
| 2 Image analysis | `image_analyses` (image, model_version, raw model output JSON, cost), `detections` (image, bbox, category, brand?, model?, age, condition, qty, **confidence**, container_type, evidence text) |
| 3 Valuation | `comps` (item query, source, url, **SOLD/ASKING**, price, condition, date, captured_at), `valuations` (detection or item, model_version, low/expected/high/quick-sale, days-to-sell, channel, comp ids used), `hidden_content_priors` (container type → value distribution, versioned) |
| 4 Underwriting | Already in `paper_decisions.outputs_json`; will get a typed `underwriting_runs` table once AI strategies exist |
| 7 Resale OS | `acquisitions` (auction, PAPER→REAL switch event, real price paid, receipts), `items` (A/B/C/D class, storage location, condition), `item_photos` (original + derived, with `derived_from` and transform list), `labor_log` (task, minutes), `disposal_log` (receipt, weight, fee) |
| 8 Listings | `listings` (item/bundle, platform, title, description, price history as append-only `price_changes`), `listing_events` (views, inquiries, offers), `sales` (**REALIZED**: price, fees, platform, date), `bundles` |

Derived photos (Phase 13 of the spec) will always reference their original by
hash. Allowed transforms (crop, white balance, background, straighten) are
recorded per image, and damage-altering edits are disallowed by policy.
