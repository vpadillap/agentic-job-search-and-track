-- One-time offers: a change may offer existing users something once (for example,
-- applying a new behavior to their earlier data). The answer is kept so an answered
-- offer is never presented again.

CREATE TABLE offers (
    id           TEXT PRIMARY KEY,
    answer       TEXT NOT NULL CHECK (answer IN ('accepted', 'declined')),
    answered_at  TEXT NOT NULL,
    result       TEXT
);
