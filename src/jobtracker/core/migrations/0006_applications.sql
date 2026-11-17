-- Application tracking: statuses mapped to fixed stages, tags, the user's
-- application details, and the register of each application's documents.

CREATE TABLE statuses (
    id         INTEGER PRIMARY KEY,
    key        TEXT UNIQUE,                    -- stable id of built-in statuses; NULL for custom
    name_en    TEXT NOT NULL,                  -- custom statuses: the name as typed, in both
    name_es    TEXT NOT NULL,
    stage      TEXT NOT NULL CHECK (stage IN ('to_apply', 'applied', 'interview', 'offer',
                                              'closed_positive', 'closed_negative')),
    is_builtin INTEGER NOT NULL DEFAULT 0 CHECK (is_builtin IN (0, 1)),
    is_retired INTEGER NOT NULL DEFAULT 0 CHECK (is_retired IN (0, 1)),
    position   INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX statuses_custom_name ON statuses (lower(name_en)) WHERE is_builtin = 0;

INSERT INTO statuses (key, name_en, name_es, stage, is_builtin, position, created_at) VALUES
    ('new', 'New', 'Nuevo', 'to_apply', 1, 10, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('applied', 'Applied', 'Postulado', 'applied', 1, 20, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('interview', 'Interview', 'Entrevista', 'interview', 1, 30,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('offer', 'Offer', 'Oferta', 'offer', 1, 40, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('accepted', 'Accepted', 'Aceptada', 'closed_positive', 1, 50,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('rejected', 'Rejected', 'Rechazado', 'closed_negative', 1, 60,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('ghosted', 'Ghosted', 'Ghost', 'closed_negative', 1, 61,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('offer_declined', 'Offer declined', 'Oferta rechazada', 'closed_negative', 1, 62,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('no_economic_alignment', 'No economic alignment', 'Sin alineación económica',
     'closed_negative', 1, 63, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ('withdrawn', 'Withdrawn', 'Me retiré', 'closed_negative', 1, 64,
     strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

-- The minimal record from the Search board becomes the full application.
CREATE TABLE applications_full (
    id                    INTEGER PRIMARY KEY,
    job_id                TEXT NOT NULL UNIQUE,
    posting_id            INTEGER NOT NULL UNIQUE REFERENCES postings (id),
    status_id             INTEGER NOT NULL REFERENCES statuses (id),
    applied_on            TEXT,                -- calendar date YYYY-MM-DD
    asked_salary_amount   INTEGER,             -- per month
    asked_salary_currency TEXT,
    asked_salary_basis    TEXT CHECK (asked_salary_basis IN ('gross', 'net')),
    channel               TEXT,
    contact               TEXT,
    notes                 TEXT,
    next_step_on          TEXT,                -- date set by the user (interviews, offers)
    next_step_note        TEXT,                -- the user's own next step, overrides the derived one
    status_changed_at     TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
INSERT INTO applications_full (id, job_id, posting_id, status_id, applied_on,
                               status_changed_at, created_at, updated_at)
SELECT a.id, a.job_id, a.posting_id,
       (SELECT s.id FROM statuses s WHERE s.key = CASE a.status WHEN 'applied' THEN 'applied'
                                                               ELSE 'new' END),
       a.applied_on, a.updated_at, a.created_at, a.updated_at
FROM applications a;
DROP TABLE applications;
ALTER TABLE applications_full RENAME TO applications;
CREATE INDEX applications_status ON applications (status_id);

CREATE TABLE application_tags (
    application_id INTEGER NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    tag            TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (application_id, tag COLLATE NOCASE)
);

-- Every file a human opens for an application, registered with its version.
CREATE TABLE documents (
    id             INTEGER PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    kind           TEXT NOT NULL CHECK (kind IN ('posting', 'resume_proposed', 'resume_sent',
                                                 'cover_letter')),
    file_name      TEXT NOT NULL,              -- relative to the application folder
    version        INTEGER NOT NULL,
    origin         TEXT NOT NULL CHECK (origin IN ('agent', 'user')),
    original_name  TEXT,                       -- name of the file the user uploaded
    size_bytes     INTEGER,
    created_at     TEXT NOT NULL,
    is_current     INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    UNIQUE (application_id, file_name)
);
CREATE INDEX documents_application ON documents (application_id, kind);
