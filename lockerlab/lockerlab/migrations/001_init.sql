-- lockerlab schema v1: sources, raw captures, auction observations, images,
-- bid events, model versions, paper decisions and paper settlements.
--
-- Invariants (enforced here, not just by convention):
--   * Evidence tables are append-only: UPDATE/DELETE abort (triggers are
--     generated in db.py for every table listed in APPEND_ONLY_TABLES).
--   * Timestamps are fixed-width UTC strings, so string order == time order.
--   * Nothing can be observed after it was recorded (observed_at <= recorded_at).
--   * A FORWARD paper decision is recorded at the moment it is made and before
--     the auction's known end time.

CREATE TABLE sources (
    source_key  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    base_url    TEXT,
    created_at  TEXT NOT NULL
) STRICT;

-- One row per captured artifact: a CSV/YAML manual capture file, a saved
-- page, an API response, or a photo. The bytes live in the content-addressed
-- raw store (data/raw/<sha[:2]>/<sha>) and are never modified.
CREATE TABLE raw_captures (
    id              INTEGER PRIMARY KEY,
    source_key      TEXT NOT NULL REFERENCES sources(source_key),
    source_url      TEXT,
    capture_method  TEXT NOT NULL CHECK (capture_method IN
                      ('manual_csv', 'manual_yaml', 'manual_photo', 'saved_page',
                       'authorized_api', 'fixture')),
    recorded_at     TEXT NOT NULL,
    content_sha256  TEXT NOT NULL,
    content_path    TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    byte_size       INTEGER NOT NULL,
    captured_by     TEXT,
    notes           TEXT
) STRICT;

-- Identity only. Everything that can change lives in auction_observations.
CREATE TABLE auctions (
    id                  INTEGER PRIMARY KEY,
    source_key          TEXT NOT NULL REFERENCES sources(source_key),
    external_id         TEXT NOT NULL,
    market_key          TEXT NOT NULL,
    first_recorded_at   TEXT NOT NULL,
    UNIQUE (source_key, external_id)
) STRICT;

-- A snapshot of what the auction page showed at observed_at. A closed auction
-- is just another observation with status sold / cancelled / unsold.
CREATE TABLE auction_observations (
    id                      INTEGER PRIMARY KEY,
    auction_id              INTEGER NOT NULL REFERENCES auctions(id),
    raw_capture_id          INTEGER NOT NULL REFERENCES raw_captures(id),
    observed_at             TEXT NOT NULL,
    recorded_at             TEXT NOT NULL,
    parser_version          TEXT NOT NULL,
    status                  TEXT NOT NULL CHECK (status IN
                              ('scheduled', 'active', 'closed', 'sold',
                               'cancelled', 'unsold', 'unknown')),
    url                     TEXT,
    facility_name           TEXT,
    facility_operator       TEXT,
    address                 TEXT,
    city                    TEXT,
    state                   TEXT,
    postal_code             TEXT,
    distance_miles          REAL,
    unit_label              TEXT,
    width_ft                REAL,
    length_ft               REAL,
    height_ft               REAL,
    size_bucket             TEXT,
    current_bid_cents       INTEGER,
    opening_bid_cents       INTEGER,
    bid_count               INTEGER,
    starts_at               TEXT,
    ends_at                 TEXT,
    buyer_premium_rate      REAL,
    buyer_premium_min_cents INTEGER,
    purchase_deposit_rate   REAL,
    cleaning_deposit_cents  INTEGER,
    sales_tax_rate          REAL,
    cleanout_hours          REAL,
    payment_methods         TEXT,
    photo_count             INTEGER,
    description             TEXT,
    facility_rules          TEXT,
    access_constraints      TEXT,
    final_price_cents       INTEGER,
    raw_fields_json         TEXT NOT NULL,  -- exact source strings, pre-parse
    field_meta_json         TEXT NOT NULL,  -- per field: label + confidence
    CHECK (observed_at <= recorded_at),
    CHECK (final_price_cents IS NULL OR status = 'sold'),
    CHECK (status <> 'sold' OR final_price_cents IS NOT NULL)
) STRICT;

CREATE INDEX ix_obs_auction_time ON auction_observations (auction_id, observed_at);

CREATE TABLE bid_events (
    id              INTEGER PRIMARY KEY,
    auction_id      INTEGER NOT NULL REFERENCES auctions(id),
    raw_capture_id  INTEGER NOT NULL REFERENCES raw_captures(id),
    observed_at     TEXT NOT NULL,
    recorded_at     TEXT NOT NULL,
    bid_placed_at   TEXT,
    amount_cents    INTEGER NOT NULL,
    bidder_hash     TEXT,  -- salted hash of the public alias; never the alias
    CHECK (observed_at <= recorded_at),
    CHECK (bid_placed_at IS NULL OR bid_placed_at <= observed_at)
) STRICT;

CREATE TABLE images (
    id              INTEGER PRIMARY KEY,
    auction_id      INTEGER NOT NULL REFERENCES auctions(id),
    raw_capture_id  INTEGER NOT NULL REFERENCES raw_captures(id),
    observed_at     TEXT NOT NULL,
    recorded_at     TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    original_name   TEXT,
    original_url    TEXT,
    position        INTEGER,
    CHECK (observed_at <= recorded_at),
    UNIQUE (auction_id, sha256)
) STRICT;

-- Any code/config that produces a number stored downstream is versioned here.
-- code_sha256 is a hash of the model's source files, so an edited model with a
-- forgotten version bump still gets a distinct row.
CREATE TABLE model_versions (
    id            INTEGER PRIMARY KEY,
    model_key     TEXT NOT NULL,
    version       TEXT NOT NULL,
    code_sha256   TEXT NOT NULL,
    config_json   TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE (model_key, version, code_sha256, config_sha256)
) STRICT;

CREATE TABLE paper_decisions (
    id                      INTEGER PRIMARY KEY,
    auction_id              INTEGER NOT NULL REFERENCES auctions(id),
    strategy_key            TEXT NOT NULL,
    mode                    TEXT NOT NULL CHECK (mode IN ('FORWARD', 'BACKTEST')),
    decided_at              TEXT NOT NULL,  -- information cutoff
    recorded_at             TEXT NOT NULL,  -- wall clock when written
    model_version_id        INTEGER NOT NULL REFERENCES model_versions(id),
    basis_observation_id    INTEGER NOT NULL REFERENCES auction_observations(id),
    known_ends_at           TEXT,
    current_bid_cents       INTEGER,
    decision                TEXT NOT NULL CHECK (decision IN ('PAPER_BID', 'WATCH', 'PASS')),
    max_bid_cents           INTEGER,
    paper_bid_cents         INTEGER,
    confidence              REAL,
    inputs_json             TEXT NOT NULL,
    inputs_sha256           TEXT NOT NULL,
    outputs_json            TEXT NOT NULL,
    reasons_json            TEXT NOT NULL,
    CHECK (decided_at <= recorded_at),
    -- forward decisions cannot be backdated ...
    CHECK (mode <> 'FORWARD' OR decided_at = recorded_at),
    -- ... and must be made before the auction ends
    CHECK (known_ends_at IS NULL OR decided_at < known_ends_at),
    CHECK (decision <> 'PAPER_BID' OR paper_bid_cents IS NOT NULL)
) STRICT;

CREATE INDEX ix_decisions_auction ON paper_decisions (auction_id, strategy_key, decided_at);

-- Settlement of a decision against the observed outcome, under a named,
-- versioned settlement rule. Re-settling under a new rule adds a row.
-- Decisions whose auction has no observed outcome are simply not settled;
-- reports count them as missing outcomes rather than dropping them silently.
CREATE TABLE paper_settlements (
    id                              INTEGER PRIMARY KEY,
    decision_id                     INTEGER NOT NULL REFERENCES paper_decisions(id),
    rule_version                    TEXT NOT NULL,
    settled_at                      TEXT NOT NULL,
    outcome_observation_id          INTEGER NOT NULL REFERENCES auction_observations(id),
    result                          TEXT NOT NULL CHECK (result IN
                                      ('WON', 'LOST', 'VOID', 'NOT_BID')),
    final_price_cents               INTEGER,
    increment_cents                 INTEGER,
    acq_price_conservative_cents    INTEGER,
    acq_price_neutral_cents         INTEGER,
    details_json                    TEXT NOT NULL,
    UNIQUE (decision_id, rule_version)
) STRICT;
