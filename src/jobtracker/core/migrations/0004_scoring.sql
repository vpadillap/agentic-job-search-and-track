-- Alignment scores: versioned component maximums and a history per posting.

CREATE TABLE score_weights (
    version    INTEGER PRIMARY KEY,
    weights    TEXT NOT NULL,                    -- JSON {component: maximum points}
    note       TEXT,
    created_at TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1))
);
CREATE UNIQUE INDEX score_weights_one_active ON score_weights (is_active) WHERE is_active = 1;
INSERT INTO score_weights (version, weights, note, created_at, is_active)
VALUES (1, '{"title": 25, "skills": 35, "seniority": 15, "conditions": 15, "history": 10}',
        'initial weights', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), 1);

CREATE TABLE scores (
    id              INTEGER PRIMARY KEY,
    posting_id      INTEGER NOT NULL REFERENCES postings (id) ON DELETE CASCADE,
    weights_version INTEGER NOT NULL REFERENCES score_weights (version),
    total           INTEGER NOT NULL CHECK (total BETWEEN 0 AND 100),
    components      TEXT NOT NULL,               -- JSON list of {component, points, max, note, ...}
    resume_kind     TEXT NOT NULL CHECK (resume_kind IN ('base', 'tailored', 'sent')),
    resume_ref      TEXT,                        -- base resume version or document file name
    run_id          INTEGER REFERENCES search_runs (id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    is_current      INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1))
);
CREATE UNIQUE INDEX scores_one_current ON scores (posting_id) WHERE is_current = 1;
CREATE INDEX scores_posting ON scores (posting_id);
