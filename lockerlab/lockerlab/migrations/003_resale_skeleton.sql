-- Schema v3: resale module SKELETON (Phase 7+). Tables only; no workflow uses
-- them yet and nothing in lockerlab can buy, bid, list or message anyone.
-- Everything is event-shaped and append-only: current state (an item's
-- location, a listing's price) is the latest event, so history is never lost.
-- Money recorded here is REALIZED (receipts), unlike everything upstream.

CREATE TABLE real_acquisitions (
    id                      INTEGER PRIMARY KEY,
    auction_id              INTEGER NOT NULL UNIQUE REFERENCES auctions(id),
    recorded_at             TEXT NOT NULL,
    pre_registered_decision_id INTEGER REFERENCES paper_decisions(id),
    winning_bid_cents       INTEGER NOT NULL CHECK (winning_bid_cents >= 0),
    premium_cents           INTEGER NOT NULL CHECK (premium_cents >= 0),
    tax_cents               INTEGER NOT NULL CHECK (tax_cents >= 0),
    deposit_cents           INTEGER NOT NULL DEFAULT 0 CHECK (deposit_cents >= 0),
    receipt_raw_capture_id  INTEGER REFERENCES raw_captures(id),
    note                    TEXT
) STRICT;

CREATE TABLE items (
    id                  INTEGER PRIMARY KEY,
    acquisition_id      INTEGER NOT NULL REFERENCES real_acquisitions(id),
    recorded_at         TEXT NOT NULL,
    description         TEXT NOT NULL,
    category            TEXT,
    brand               TEXT,
    model               TEXT,
    condition           TEXT,
    grade               TEXT CHECK (grade IN ('A', 'B', 'C', 'D')),
    footprint_cuft      REAL,
    sensitive_review    INTEGER NOT NULL DEFAULT 1 CHECK (sensitive_review IN (0, 1)),
    estimated_value_cents INTEGER,
    estimate_model_version_id INTEGER REFERENCES model_versions(id)
) STRICT;

CREATE TABLE item_events (
    id              INTEGER PRIMARY KEY,
    item_id         INTEGER NOT NULL REFERENCES items(id),
    recorded_at     TEXT NOT NULL,
    event           TEXT NOT NULL CHECK (event IN
                      ('stored', 'moved', 'cleared_sensitive_review', 'returned_to_facility',
                       'bundled', 'regraded', 'note')),
    detail_json     TEXT NOT NULL
) STRICT;

-- Originals are never modified. A derived photo names its original and the
-- exact transforms applied; transforms that change apparent condition are banned.
CREATE TABLE item_photos (
    id                  INTEGER PRIMARY KEY,
    item_id             INTEGER NOT NULL REFERENCES items(id),
    raw_capture_id      INTEGER NOT NULL REFERENCES raw_captures(id),
    derived_from_id     INTEGER REFERENCES item_photos(id),
    transforms_json     TEXT,
    recorded_at         TEXT NOT NULL,
    CHECK ((derived_from_id IS NULL) = (transforms_json IS NULL))
) STRICT;

CREATE TABLE listings (
    id              INTEGER PRIMARY KEY,
    item_id         INTEGER NOT NULL REFERENCES items(id),
    platform        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    ask_cents       INTEGER NOT NULL CHECK (ask_cents >= 0),
    quick_sale_cents INTEGER,
    floor_cents     INTEGER,
    external_url    TEXT               -- filled in by a human after posting by hand
) STRICT;

CREATE TABLE listing_events (
    id              INTEGER PRIMARY KEY,
    listing_id      INTEGER NOT NULL REFERENCES listings(id),
    recorded_at     TEXT NOT NULL,
    event           TEXT NOT NULL CHECK (event IN
                      ('price_change', 'inquiry', 'offer', 'no_show', 'relisted', 'ended', 'views')),
    amount_cents    INTEGER,
    detail_json     TEXT NOT NULL
) STRICT;

CREATE TABLE sales (
    id              INTEGER PRIMARY KEY,
    item_id         INTEGER NOT NULL REFERENCES items(id),
    listing_id      INTEGER REFERENCES listings(id),
    sold_at         TEXT NOT NULL,
    recorded_at     TEXT NOT NULL,
    platform        TEXT NOT NULL,
    price_cents     INTEGER NOT NULL CHECK (price_cents >= 0),
    fees_cents      INTEGER NOT NULL DEFAULT 0 CHECK (fees_cents >= 0),
    shipping_cents  INTEGER NOT NULL DEFAULT 0 CHECK (shipping_cents >= 0),
    sales_tax_remitted_cents INTEGER NOT NULL DEFAULT 0,
    selling_minutes REAL,
    CHECK (sold_at <= recorded_at)
) STRICT;

CREATE TABLE disposal_events (
    id              INTEGER PRIMARY KEY,
    acquisition_id  INTEGER NOT NULL REFERENCES real_acquisitions(id),
    recorded_at     TEXT NOT NULL,
    pathway         TEXT NOT NULL CHECK (pathway IN
                      ('A_negligible', 'B_household', 'C_donate_recycle', 'D_small_paid',
                       'E_dump_run', 'F_special_items', 'G_junk_hauler')),
    facility        TEXT,
    weight_lbs      REAL,
    fee_cents       INTEGER NOT NULL DEFAULT 0 CHECK (fee_cents >= 0),
    receipt_raw_capture_id INTEGER REFERENCES raw_captures(id),
    labor_minutes   REAL
) STRICT;

CREATE TABLE donation_events (
    id              INTEGER PRIMARY KEY,
    acquisition_id  INTEGER NOT NULL REFERENCES real_acquisitions(id),
    recorded_at     TEXT NOT NULL,
    organization    TEXT NOT NULL,
    description     TEXT NOT NULL,
    est_cuft        REAL,
    receipt_raw_capture_id INTEGER REFERENCES raw_captures(id)
) STRICT;
