## Why

`add-resume-languages` made one base resume the "main" one: used for scoring
every posting and as the source for translation. The project owner rejected
that: each resume is the source for its own language. A Spanish posting is
scored and tailored against the Spanish resume, an English posting against the
English one, and no resume ranks above the others.

## What Changes

- **BREAKING** Remove the main base resume (`resume main`, the `main` flag, and
  the context's single `base_resume`).
- A posting is scored against the user's base resume in the posting's
  language, and tailored from it.
- At setup the agent asks which languages the user will apply in and gets a
  resume for each: uploaded by the user, or translated by the agent from one of
  the user's resumes as a draft the user reviews in Word before it is kept.
- When a posting is in a language the user has no resume in, scoring and
  tailoring stop with a clear error, and the agent asks the user for a resume
  in that language or offers to translate one the same way. Nothing is
  translated silently.
- Replacing the resume of a language makes the scores of postings in that
  language stale (and only those).

## Non-goals

- Keeping language versions in sync.
- Cover letters and form answers: unchanged, written fresh in the posting's
  language.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `profile`: no main resume; languages to apply in; translated drafts.
- `document-preparation`: tailoring only from the resume in the posting's
  language.

## Impact

- Migration 0009: drop the main flag.
- CLI: remove `resume main`; add `resume translate` (draft from an existing
  resume, for the user to review); `resume import --translated-from`.
  `documents tailor` and `score set` pick the resume by posting language.
- Context: `base_resumes` only.
- Skills: `/setup` (languages to apply in, upload or translate), job search
  and scoring guide (score against the posting-language resume; ask when
  missing), prepare-documents and tailoring guide (no silent translation).
