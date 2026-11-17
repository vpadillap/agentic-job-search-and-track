-- Base resume history. The profile itself is versioned JSON in profile_versions.

CREATE TABLE base_resumes (
    id            INTEGER PRIMARY KEY,
    version       INTEGER NOT NULL UNIQUE,
    file_name     TEXT NOT NULL,           -- relative to the profile folder
    text_name     TEXT NOT NULL,           -- extracted text, relative to the profile folder
    original_name TEXT NOT NULL,           -- name of the file the user provided
    characters    INTEGER NOT NULL,
    text_source   TEXT NOT NULL CHECK (text_source IN ('extracted', 'provided')),
    imported_at   TEXT NOT NULL,
    is_current    INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1))
);
CREATE UNIQUE INDEX base_resumes_one_current ON base_resumes (is_current) WHERE is_current = 1;
