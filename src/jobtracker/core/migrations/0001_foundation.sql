-- Foundation schema: everything later changes build on.

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Single-row counter bumped by every write; the panel polls it to refresh.
CREATE TABLE change_log (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    counter    INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT INTO change_log (id, counter, updated_at)
VALUES (1, 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

CREATE TABLE seasons (
    id         INTEGER PRIMARY KEY,
    number     INTEGER NOT NULL UNIQUE,
    label      TEXT,
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    is_active  INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1))
);
CREATE UNIQUE INDEX seasons_one_active ON seasons (is_active) WHERE is_active = 1;

CREATE TABLE profile_versions (
    id         INTEGER PRIMARY KEY,
    season_id  INTEGER NOT NULL REFERENCES seasons (id),
    version    INTEGER NOT NULL,
    data       TEXT NOT NULL,              -- JSON: job needs, titles, base resume
    created_at TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    UNIQUE (season_id, version)
);
CREATE UNIQUE INDEX profile_one_active ON profile_versions (is_active) WHERE is_active = 1;

-- One list for system rules, user preferences, and learned lessons.
CREATE TABLE rules (
    id         INTEGER PRIMARY KEY,
    key        TEXT UNIQUE,                -- stable id for system rules
    origin     TEXT NOT NULL CHECK (origin IN ('system', 'user', 'learned')),
    status     TEXT NOT NULL CHECK (status IN ('proposed', 'active', 'ignored', 'reverted')),
    area       TEXT NOT NULL,
    text       TEXT NOT NULL,
    evidence   TEXT,
    effect     TEXT,                       -- JSON, for rules the code enforces
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX rules_status ON rules (status);

CREATE TABLE providers_state (
    provider_id TEXT PRIMARY KEY,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    last_status TEXT,
    last_error  TEXT,
    last_run_at TEXT,
    updated_at  TEXT NOT NULL
);

-- Append-only timeline; the substrate of the learning loop.
CREATE TABLE events (
    id          INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    kind        TEXT NOT NULL,
    data        TEXT,                      -- JSON
    created_at  TEXT NOT NULL
);
CREATE INDEX events_entity ON events (entity_type, entity_id);

-- Facts known at the moment of applying; training data for prediction.
CREATE TABLE application_snapshots (
    id             INTEGER PRIMARY KEY,
    application_id TEXT NOT NULL UNIQUE,
    captured_at    TEXT NOT NULL,
    data           TEXT NOT NULL           -- JSON
);
