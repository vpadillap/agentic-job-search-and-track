-- Search runs, postings, and what the user decided about them.

CREATE TABLE search_runs (
    id               INTEGER PRIMARY KEY,
    season_id        INTEGER REFERENCES seasons (id),
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    status           TEXT NOT NULL CHECK (status IN ('running', 'finished')),
    posting_age_days INTEGER NOT NULL,
    titles           TEXT NOT NULL,              -- JSON list of the titles searched
    providers        TEXT NOT NULL DEFAULT '[]', -- JSON list of {id, name, status, reason}
    capture_folder   TEXT,                       -- relative to the private home
    is_demo          INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1))
);

-- One row per posting on one site. The same job on two sites is two rows: the
-- user chooses which site to use. Identity is the site's own id or the URL.
-- Fields are stored as captured; the description is verbatim.
CREATE TABLE postings (
    id               INTEGER PRIMARY KEY,
    provider         TEXT NOT NULL,
    external_id      TEXT NOT NULL,
    url              TEXT NOT NULL,
    url_key          TEXT NOT NULL UNIQUE,       -- normalized URL
    title            TEXT NOT NULL,
    company          TEXT NOT NULL,
    location         TEXT,
    country          TEXT,                       -- ISO 3166-1 alpha-2
    work_mode        TEXT CHECK (work_mode IN ('remote', 'hybrid', 'onsite')),
    contract_type    TEXT CHECK (contract_type IN ('full-time', 'part-time', 'contractor')),
    seniority        TEXT,
    posted_at        TEXT,                       -- calendar date YYYY-MM-DD
    description      TEXT NOT NULL,
    published_salary TEXT,                       -- JSON, only when the posting states it
    language         TEXT,
    flags            TEXT NOT NULL DEFAULT '[]', -- JSON list of doubts shown to the user
    match_key        TEXT NOT NULL,              -- normalized company | title; only for the
                                                 -- "possible duplicate" hint, never merged
    first_run_id     INTEGER REFERENCES search_runs (id),
    captured_at      TEXT NOT NULL,
    is_demo          INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    UNIQUE (provider, external_id)
);
CREATE INDEX postings_match ON postings (match_key);

-- What each run found: one row per sighting.
CREATE TABLE run_results (
    id            INTEGER PRIMARY KEY,
    run_id        INTEGER NOT NULL REFERENCES search_runs (id) ON DELETE CASCADE,
    posting_id    INTEGER NOT NULL REFERENCES postings (id) ON DELETE CASCADE,
    provider      TEXT NOT NULL,
    outcome       TEXT NOT NULL CHECK (outcome IN ('new', 'filtered', 'duplicate', 'seen')),
    reason        TEXT,                          -- filter reason code, or why it was already seen
    reason_detail TEXT,
    created_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX run_results_one_first_sighting
    ON run_results (run_id, posting_id) WHERE outcome IN ('new', 'filtered', 'seen');
CREATE INDEX run_results_run ON run_results (run_id, outcome);

CREATE TABLE form_questions (
    id         INTEGER PRIMARY KEY,
    posting_id INTEGER NOT NULL REFERENCES postings (id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    text       TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'text',
    options    TEXT,                             -- JSON list for choice questions
    required   INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0, 1)),
    UNIQUE (posting_id, position)
);

-- A dismissed posting is never proposed again; the reason feeds learning.
CREATE TABLE dismissals (
    id         INTEGER PRIMARY KEY,
    posting_id INTEGER NOT NULL UNIQUE REFERENCES postings (id) ON DELETE CASCADE,
    reason     TEXT NOT NULL CHECK (reason IN ('industry', 'low_salary', 'location', 'stack',
                                               'other')),
    note       TEXT,
    created_at TEXT NOT NULL
);

-- Minimal tracked-application record; statuses, tags, and details arrive with
-- application tracking.
CREATE TABLE applications (
    id         INTEGER PRIMARY KEY,
    job_id     TEXT NOT NULL UNIQUE,             -- J0007; never reused
    posting_id INTEGER NOT NULL UNIQUE REFERENCES postings (id),
    status     TEXT NOT NULL,                    -- 'new' or 'applied' for now
    applied_on TEXT,                             -- calendar date YYYY-MM-DD
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
