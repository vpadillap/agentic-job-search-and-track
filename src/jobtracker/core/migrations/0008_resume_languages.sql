-- Base resumes per language: one current base resume per language, one of them
-- the main one (scoring, and the source for translation).

DROP INDEX base_resumes_one_current;
ALTER TABLE base_resumes ADD COLUMN language TEXT;      -- ISO 639-1 code; NULL: not stated yet
ALTER TABLE base_resumes ADD COLUMN is_main INTEGER NOT NULL DEFAULT 0
    CHECK (is_main IN (0, 1));
UPDATE base_resumes SET is_main = 1 WHERE is_current = 1;
CREATE UNIQUE INDEX base_resumes_one_current_per_language
    ON base_resumes (COALESCE(language, '')) WHERE is_current = 1;
CREATE UNIQUE INDEX base_resumes_one_main ON base_resumes (is_main) WHERE is_main = 1;

-- The base resume a tailored resume was made from.
ALTER TABLE documents ADD COLUMN base_resume_id INTEGER REFERENCES base_resumes (id);
