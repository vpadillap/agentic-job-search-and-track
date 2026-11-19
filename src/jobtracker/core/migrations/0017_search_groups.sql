-- Searches of the same day are shown on one page: runs belong to a group. Each
-- existing run gets its own group, so the panel looks the same until the user
-- accepts the one-time offer to group earlier searches by day.

CREATE TABLE search_groups (
    id          INTEGER PRIMARY KEY,
    season_id   INTEGER REFERENCES seasons (id),
    started_at  TEXT NOT NULL,
    is_demo     INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1))
);

ALTER TABLE search_runs ADD COLUMN group_id INTEGER REFERENCES search_groups (id);

INSERT INTO search_groups (id, season_id, started_at, is_demo)
    SELECT id, season_id, started_at, is_demo FROM search_runs;
UPDATE search_runs SET group_id = id;

CREATE INDEX search_runs_group ON search_runs (group_id);
