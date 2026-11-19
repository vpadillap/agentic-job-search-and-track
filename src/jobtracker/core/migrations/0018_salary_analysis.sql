-- Salary research becomes the agent's analysis: company profiles to compare
-- companies, the scope of each piece of evidence (the same company or the market),
-- what was checked per key and source, and the suggestion's note and inputs.

CREATE TABLE company_profiles (
    company_key  TEXT PRIMARY KEY,               -- normalized company name
    name         TEXT NOT NULL,
    industry     TEXT,                           -- NULL means unknown
    size_band    TEXT,                           -- e.g. "1,001-5,000 employees"
    kind         TEXT,                           -- bank, consultancy, startup, ...
    source       TEXT NOT NULL,                  -- 'posting' or the source's name
    source_url   TEXT,
    updated_at   TEXT NOT NULL
);

ALTER TABLE salary_evidence ADD COLUMN scope TEXT NOT NULL DEFAULT 'market'
    CHECK (scope IN ('company', 'market'));
ALTER TABLE salary_evidence ADD COLUMN role_family TEXT;

-- What a source gave for a key, found or not, so it is not searched again soon.
CREATE TABLE salary_checks (
    id          INTEGER PRIMARY KEY,
    scope       TEXT NOT NULL CHECK (scope IN ('company', 'market')),
    key         TEXT NOT NULL,                   -- JSON of the key's fields
    source      TEXT NOT NULL,
    found       INTEGER NOT NULL CHECK (found IN (0, 1)),
    detail      TEXT,
    posting_id  INTEGER REFERENCES postings (id) ON DELETE SET NULL,
    checked_at  TEXT NOT NULL
);
CREATE INDEX salary_checks_key ON salary_checks (scope, key);

ALTER TABLE salary_suggestions ADD COLUMN note TEXT;
ALTER TABLE salary_suggestions ADD COLUMN inputs TEXT;     -- JSON list with weights
ALTER TABLE salary_suggestions ADD COLUMN set_aside TEXT;  -- JSON list with reasons
ALTER TABLE salary_suggestions ADD COLUMN counts TEXT;     -- JSON {company, history, market}
