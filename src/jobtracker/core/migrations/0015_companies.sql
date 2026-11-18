-- The agentic-search provider remembers the companies it finds, per season: their
-- careers page, the titles they were found for, when they were last checked, and
-- whether the user excluded them.

CREATE TABLE companies (
    id               INTEGER PRIMARY KEY,
    season_id        INTEGER REFERENCES seasons (id),
    name             TEXT NOT NULL,
    careers_url      TEXT NOT NULL,
    url_key          TEXT NOT NULL,
    found_via        TEXT,
    titles           TEXT NOT NULL DEFAULT '[]',
    first_seen_at    TEXT NOT NULL,
    last_checked_at  TEXT NOT NULL,
    last_matches     INTEGER,
    excluded         INTEGER NOT NULL DEFAULT 0,
    excluded_reason  TEXT,
    UNIQUE (season_id, url_key)
);
CREATE INDEX companies_season ON companies (season_id, excluded);

-- Where a posting found on the open web came from (the site's host), so the panel
-- can show it next to the provider.
ALTER TABLE postings ADD COLUMN source_site TEXT;
