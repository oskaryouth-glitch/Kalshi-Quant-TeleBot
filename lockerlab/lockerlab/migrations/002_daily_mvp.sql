-- lockerlab: foreign_keys_off
-- Schema v2: daily-use MVP (screenshot/URL capture, quick decisions, results,
-- assumption sets, source-policy log, readiness evidence).
--
-- raw_captures is rebuilt (SQLite cannot alter a CHECK constraint) with the
-- documented copy-and-swap procedure. Every existing row is copied unchanged;
-- db.py re-creates its append-only triggers and runs foreign_key_check.

CREATE TABLE raw_captures_v2 (
    id              INTEGER PRIMARY KEY,
    source_key      TEXT NOT NULL REFERENCES sources(source_key),
    source_url      TEXT,
    capture_method  TEXT NOT NULL CHECK (capture_method IN
                      ('manual_csv', 'manual_yaml', 'manual_photo', 'saved_page',
                       'authorized_api', 'fixture',
                       'screenshot', 'review_form', 'result_form', 'decision_form')),
    recorded_at     TEXT NOT NULL,
    content_sha256  TEXT NOT NULL,
    content_path    TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    byte_size       INTEGER NOT NULL,
    captured_by     TEXT,
    notes           TEXT
) STRICT;

INSERT INTO raw_captures_v2 SELECT * FROM raw_captures;
DROP TABLE raw_captures;
ALTER TABLE raw_captures_v2 RENAME TO raw_captures;

-- A capture in progress: the URL and files the user supplied. Confirming it
-- creates an auction_observation (linked by intake_confirmations).
CREATE TABLE intakes (
    id                  INTEGER PRIMARY KEY,
    created_at          TEXT NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('listing', 'result')),
    url                 TEXT,
    source_key          TEXT REFERENCES sources(source_key),
    external_id         TEXT,
    url_evidence        TEXT NOT NULL,
    market_key          TEXT NOT NULL,
    screenshot_policy   TEXT NOT NULL CHECK (screenshot_policy IN ('allowed', 'manual_only')),
    auction_id          INTEGER REFERENCES auctions(id)
) STRICT;

CREATE TABLE intake_files (
    intake_id       INTEGER NOT NULL REFERENCES intakes(id),
    raw_capture_id  INTEGER NOT NULL REFERENCES raw_captures(id),
    role            TEXT NOT NULL CHECK (role IN ('screenshot', 'auction_photo')),
    position        INTEGER NOT NULL,
    PRIMARY KEY (intake_id, raw_capture_id)
) STRICT;

-- One run of an extractor over an intake's screenshots. A proposal only; it
-- becomes evidence for an observation only when the user confirms.
CREATE TABLE extractions (
    id              INTEGER PRIMARY KEY,
    intake_id       INTEGER NOT NULL REFERENCES intakes(id),
    created_at      TEXT NOT NULL,
    extractor       TEXT NOT NULL,       -- e.g. claude:claude-opus-5-5
    prompt_version  TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'error', 'refused', 'skipped')),
    raw_output      TEXT,                -- exactly what the model returned
    fields_json     TEXT NOT NULL,       -- normalized: field -> {value, confidence, evidence, status}
    error           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER
) STRICT;

CREATE TABLE intake_confirmations (
    intake_id       INTEGER PRIMARY KEY REFERENCES intakes(id),
    observation_id  INTEGER NOT NULL UNIQUE REFERENCES auction_observations(id),
    extraction_id   INTEGER REFERENCES extractions(id),
    confirmed_at    TEXT NOT NULL
) STRICT;

-- Per-source capture policy changes (who enabled screenshots, when, why).
-- The latest event overrides the config default.
CREATE TABLE source_policy_events (
    id                  INTEGER PRIMARY KEY,
    source_key          TEXT NOT NULL REFERENCES sources(source_key),
    recorded_at         TEXT NOT NULL,
    screenshot_policy   TEXT NOT NULL CHECK (screenshot_policy IN ('allowed', 'manual_only')),
    basis               TEXT NOT NULL CHECK (basis IN ('written_permission', 'api_agreement',
                          'terms_reviewed_no_restriction', 'revoked', 'other')),
    note                TEXT NOT NULL
) STRICT;

-- Assumption overrides from the assumptions panel. Each row is the complete
-- override set in force from created_at on; decisions store the effective
-- config they used, so a new set never changes an old decision.
CREATE TABLE assumption_sets (
    id              INTEGER PRIMARY KEY,
    created_at      TEXT NOT NULL,
    overrides_json  TEXT NOT NULL,   -- {"path.to.leaf": {"value", "status", "source"}}
    note            TEXT
) STRICT;

-- Timed selling experiment: your own items, so selling minutes stop being a guess.
CREATE TABLE selling_time_log (
    id                  INTEGER PRIMARY KEY,
    recorded_at         TEXT NOT NULL,
    item                TEXT NOT NULL,
    platform            TEXT NOT NULL,
    listing_minutes     REAL NOT NULL CHECK (listing_minutes >= 0),
    selling_minutes     REAL NOT NULL CHECK (selling_minutes >= 0),
    sold                INTEGER NOT NULL CHECK (sold IN (0, 1)),
    price_cents         INTEGER CHECK (price_cents IS NULL OR price_cents >= 0),
    note                TEXT
) STRICT;

-- First-hand attestations for the readiness page (e.g. "friend's SUV
-- available on 48h notice", "called Woodmen Dump").
CREATE TABLE readiness_checks (
    id              INTEGER PRIMARY KEY,
    recorded_at     TEXT NOT NULL,
    check_key       TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('done', 'not_done')),
    note            TEXT NOT NULL
) STRICT;
