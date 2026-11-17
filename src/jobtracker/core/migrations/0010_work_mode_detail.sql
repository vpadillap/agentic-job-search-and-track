-- How a posting describes its work arrangement beyond remote/hybrid/onsite
-- ("2 días presencial por semana", "Summer hours: Fridays until noon"), in the
-- posting's language, and who last set the work mode: the agent at import, or
-- the user correcting it from the panel or through the agent.

ALTER TABLE postings ADD COLUMN work_mode_detail TEXT;
ALTER TABLE postings ADD COLUMN work_mode_source TEXT NOT NULL DEFAULT 'agent'
    CHECK (work_mode_source IN ('agent', 'user'));
