-- Each base resume is the source for its own language: there is no main one.

DROP INDEX base_resumes_one_main;
ALTER TABLE base_resumes DROP COLUMN is_main;

-- A base resume the agent translated and the user reviewed: the language it
-- was translated from.
ALTER TABLE base_resumes ADD COLUMN translated_from TEXT;
