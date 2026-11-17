-- Seasons become manageable: each application belongs to the season it was
-- tracked in (or was carried into), and a closed season keeps what it used.

ALTER TABLE applications ADD COLUMN season_id INTEGER REFERENCES seasons (id);
UPDATE applications
   SET season_id = COALESCE((SELECT id FROM seasons WHERE is_active = 1),
                            (SELECT MAX(id) FROM seasons));
CREATE INDEX applications_season ON applications (season_id);

-- JSON written when the season closes: its last profile version and the base
-- resumes that were current, so an earlier season keeps its own resume.
ALTER TABLE seasons ADD COLUMN closing TEXT;
