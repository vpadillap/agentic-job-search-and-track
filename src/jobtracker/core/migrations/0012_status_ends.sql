-- Statuses are a flat list: the stage of each status is removed, and each
-- status says instead whether an application ended with it.
ALTER TABLE statuses ADD COLUMN ends INTEGER NOT NULL DEFAULT 0 CHECK (ends IN (0, 1));

UPDATE statuses SET ends = 1
 WHERE key IN ('accepted', 'rejected', 'ghosted', 'offer_declined', 'no_economic_alignment',
               'withdrawn')
    OR (key IS NULL AND stage IN ('closed_positive', 'closed_negative'));

ALTER TABLE statuses DROP COLUMN stage;
