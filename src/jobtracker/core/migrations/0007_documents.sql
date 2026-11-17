-- Document preparation: what each agent document is based on, the decision
-- whether a cover letter is needed, and proposed answers to form questions.

ALTER TABLE documents ADD COLUMN language TEXT;          -- language the document is written in
ALTER TABLE documents ADD COLUMN change_summary TEXT;    -- what was changed and why
ALTER TABLE documents ADD COLUMN level TEXT
    CHECK (level IS NULL OR level IN ('light', 'medium', 'heavy'));
ALTER TABLE documents ADD COLUMN support TEXT;           -- JSON [{term, source}]: base-resume line behind each emphasized term
ALTER TABLE documents ADD COLUMN gaps TEXT;              -- JSON [text]: what the posting asks that the user lacks
ALTER TABLE documents ADD COLUMN applied_rules TEXT;     -- JSON [rule id]: rules followed when it was written

-- Whether this application needs a cover letter. NULL: not decided yet.
ALTER TABLE applications ADD COLUMN cover_letter_need TEXT
    CHECK (cover_letter_need IS NULL OR cover_letter_need IN ('required', 'not_required'));
ALTER TABLE applications ADD COLUMN cover_letter_reason TEXT;

-- Proposed answers, one current answer per form question. A user edit is never
-- overwritten: a later agent proposal becomes an alternative the user can pick.
CREATE TABLE form_answers (
    id             INTEGER PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,              -- form_questions.position of the posting
    text           TEXT NOT NULL DEFAULT '',
    origin         TEXT NOT NULL CHECK (origin IN ('agent', 'user')),
    state          TEXT NOT NULL CHECK (state IN ('current', 'alternative', 'superseded')),
    needs_user     INTEGER NOT NULL DEFAULT 0 CHECK (needs_user IN (0, 1)),
    basis          TEXT,                          -- e.g. "based on the suggested salary"
    note           TEXT,                          -- what the user must supply, when needs_user
    language       TEXT,
    applied_rules  TEXT,                          -- JSON [rule id]
    created_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX form_answers_one_current ON form_answers (application_id, position)
    WHERE state = 'current';
CREATE INDEX form_answers_application ON form_answers (application_id, position);
