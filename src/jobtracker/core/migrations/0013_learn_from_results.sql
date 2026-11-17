-- Learning works from results: the salary the company offered, and no separate
-- copy of the facts at application time (they are derived from the history and
-- the stored versions of scores and salary suggestions).
ALTER TABLE applications ADD COLUMN offered_salary_amount INTEGER;      -- per month
ALTER TABLE applications ADD COLUMN offered_salary_currency TEXT;
ALTER TABLE applications ADD COLUMN offered_salary_basis TEXT
    CHECK (offered_salary_basis IN ('gross', 'net'));

-- The moment each application first got an applied date becomes an event in its
-- history, with the date of applying and the score version current then.
INSERT INTO events (entity_type, entity_id, kind, data, created_at)
SELECT 'application', application_id, 'applied',
       json_object('on', json_extract(data, '$.applied_on'),
                   'score_id', json_extract(data, '$.score_id')), captured_at
  FROM application_snapshots;

DROP TABLE application_snapshots;
