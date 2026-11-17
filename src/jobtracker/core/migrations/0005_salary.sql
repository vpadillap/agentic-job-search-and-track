-- Salary evidence, evidence-gated suggestions, and a log of research attempts.

CREATE TABLE salary_evidence (
    id               INTEGER PRIMARY KEY,
    source           TEXT NOT NULL,              -- e.g. the site name
    url              TEXT NOT NULL,
    summary          TEXT,                       -- what the report is, in a few words
    amount_min       INTEGER NOT NULL,           -- normalized to one month
    amount_max       INTEGER NOT NULL,
    currency         TEXT NOT NULL,
    basis            TEXT NOT NULL CHECK (basis IN ('gross', 'net')),
    original_period  TEXT NOT NULL CHECK (original_period IN ('month', 'year')),
    sample_size      INTEGER,
    observed_on      TEXT NOT NULL,              -- date of the report YYYY-MM-DD
    country          TEXT NOT NULL,
    level            TEXT NOT NULL,
    work_mode        TEXT,
    industry         TEXT,
    company_size     TEXT,
    from_posting     INTEGER NOT NULL DEFAULT 0 CHECK (from_posting IN (0, 1)),
    research_company TEXT NOT NULL,              -- cache key: normalized company, role, location
    research_role    TEXT NOT NULL,
    research_location TEXT NOT NULL,
    posting_id       INTEGER REFERENCES postings (id) ON DELETE SET NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX salary_evidence_key
    ON salary_evidence (research_company, research_role, research_location);

CREATE TABLE salary_suggestions (
    id         INTEGER PRIMARY KEY,
    posting_id INTEGER NOT NULL REFERENCES postings (id) ON DELETE CASCADE,
    status     TEXT NOT NULL CHECK (status IN ('suggested', 'no_data')),
    amount     INTEGER,                          -- monthly median, only when suggested
    range_min  INTEGER,
    range_max  INTEGER,
    currency   TEXT,
    basis      TEXT CHECK (basis IN ('gross', 'net')),
    confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
    criteria   TEXT,                             -- JSON comparison criteria
    checked    TEXT,                             -- JSON list of what was tried (no_data)
    created_at TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    CHECK (status = 'no_data' OR (amount IS NOT NULL AND currency IS NOT NULL))
);
CREATE UNIQUE INDEX salary_suggestions_one_current
    ON salary_suggestions (posting_id) WHERE is_current = 1;

CREATE TABLE salary_suggestion_evidence (
    suggestion_id INTEGER NOT NULL REFERENCES salary_suggestions (id) ON DELETE CASCADE,
    evidence_id   INTEGER NOT NULL REFERENCES salary_evidence (id),
    PRIMARY KEY (suggestion_id, evidence_id)
);

CREATE TABLE salary_research_log (
    id                INTEGER PRIMARY KEY,
    posting_id        INTEGER REFERENCES postings (id) ON DELETE SET NULL,
    research_company  TEXT NOT NULL,
    research_role     TEXT NOT NULL,
    research_location TEXT NOT NULL,
    outcome           TEXT NOT NULL CHECK (outcome IN ('suggested', 'no_data', 'reused')),
    checked           TEXT,                      -- JSON list of sources tried
    created_at        TEXT NOT NULL
);
CREATE INDEX salary_research_key
    ON salary_research_log (research_company, research_role, research_location);
