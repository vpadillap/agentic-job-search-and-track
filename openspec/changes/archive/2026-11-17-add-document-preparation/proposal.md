## Why

Tailoring a resume, writing a cover letter, and answering form questions for
every application is the most time-consuming part of a job search and the part
where the agent adds the most. It must do it truthfully, in the posting's
language, and without altering the user's resume beyond what they allow.

## What Changes

- Add the `/prepare-documents` skill: for one, several, or all tracked
  applications that lack them, produce a tailored resume, a cover letter where
  needed, and answers to the application-form questions. With `pending` it is
  the single batch instruction after a search and tracking.
- Add the `/form-answers` skill for answers only, including regenerating an
  alternative version.
- Add document registration with a change summary and a diff against the base
  resume, and rescoring after tailoring.
- Add the pending-work queue shared by the panel and the agent.

## Non-goals

- Submitting applications or filling forms on job sites.
- Designing new resume templates; layout changes happen only with consent.
- Interview preparation material.

## Capabilities

### New Capabilities

- `document-preparation`: tailored resumes and cover letters, their rules, and
  how they are stored and shown.
- `form-answers`: proposed answers to application-form questions and their
  editing.
- `pending-work`: the queue of items waiting for the agent and the batch run
  that clears it.

### Modified Capabilities

None.

## Impact

- New: `.claude/skills/prepare-documents/`, `.claude/skills/form-answers/`,
  Spanish aliases, CLI `jobtracker documents …`, `jobtracker answers …`,
  document diff view in the panel.
- Dependency: `python-docx` for in-place DOCX editing. Tailored resumes are
  delivered as DOCX; no PDF conversion.
- Depends on `add-application-tracking` and `add-job-search`.
