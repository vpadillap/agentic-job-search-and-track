-- Learning loop: lessons proposed from results, what each rule influenced,
-- the analyses that fit and validate the prediction model, and experiments.

-- A learned rule remembers the candidate it came from and the number of cases
-- behind it, so an ignored or reverted lesson is not proposed again on the
-- same evidence.
ALTER TABLE rules ADD COLUMN candidate_key TEXT;
ALTER TABLE rules ADD COLUMN candidate_cases INTEGER;
ALTER TABLE rules ADD COLUMN applied_at TEXT;

-- Which rules were active when a score, search, suggestion, document, or
-- answer was produced.
CREATE TABLE rule_influence (
    id          INTEGER PRIMARY KEY,
    rule_id     INTEGER NOT NULL REFERENCES rules (id),
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX rule_influence_rule ON rule_influence (rule_id);
CREATE INDEX rule_influence_entity ON rule_influence (entity_type, entity_id);

-- Each fit of a model (interview chance, or fit to the user's choices): counts,
-- the model, and whether it validated. `resolved` holds the decisions for `fit`.
CREATE TABLE analyses (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL DEFAULT 'interview' CHECK (kind IN ('interview', 'fit')),
    created_at TEXT NOT NULL,
    resolved   INTEGER NOT NULL,
    interviews INTEGER NOT NULL,
    passed     INTEGER NOT NULL DEFAULT 0 CHECK (passed IN (0, 1)),
    reason     TEXT,
    validation TEXT,                      -- JSON: Brier scores, thirds, calibration
    model      TEXT                       -- JSON: coefficients, base rate, bootstrap
);

-- A simple experiment the user accepted: alternate two options of one
-- dimension on upcoming applications and compare the results.
CREATE TABLE experiments (
    id           INTEGER PRIMARY KEY,
    dimension    TEXT NOT NULL,
    option_a     TEXT NOT NULL,
    option_b     TEXT NOT NULL,
    planned      INTEGER NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('proposed', 'active', 'concluded', 'declined')),
    question     TEXT NOT NULL,
    proposed_at  TEXT NOT NULL,
    accepted_at  TEXT,
    concluded_at TEXT,
    result       TEXT                     -- JSON
);
