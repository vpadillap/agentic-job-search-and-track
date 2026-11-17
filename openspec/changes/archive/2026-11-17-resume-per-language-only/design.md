## Context

Follows `add-resume-languages` (same day). Owner's rule: "each resume is the
source for its own language and should be used for scoring a post for that
language". For a language without a resume: "the agent at setup asks for the
languages to be used and asks for the upload of resumes and offers to
translate if needed … if I ask the agent to search in a new language and don't
have a resume the agent asks for it or offers to translate the same way".

## Decisions

### L1. Choosing the resume for a posting

One rule, used by scoring and tailoring alike:

1. The posting's language has a current base resume → use it.
2. Otherwise → `no_resume_for_language` error naming the language. The agent
   asks the user for a resume in that language or offers to translate one.
3. Posting language unknown: if the user has exactly one base resume, use it;
   otherwise `posting_language_unknown` (the agent passes `--base <code>`
   after reading the posting).

`--base <code>` stays as an explicit override.

A base resume imported before languages were recorded (language unknown) is
used as in step 3 until the user states its language.

### L2. Translated drafts

`resume translate --from <code> --to <code> -` takes text edits like
`documents tailor` (one replacement per paragraph) and writes
`profile/resume-draft-<to>.docx`, a copy of the source resume with the same
design. The user opens it in Word, adjusts it, and confirms; then
`resume import <draft> --language <to> --translated-from <from>` stores it as
the base resume for that language (the event records that it was translated).
Nothing is used for scoring or tailoring until it is imported.

### L3. Scoring

`score set` with a base resume (`resume.kind = base`, no ref) records the
version of the resume in the posting's language. A score is stale when the
resume version it was judged against has been replaced by a newer one in the
same language.

### L4. Migration

Migration 0009 drops the main flag and its index. Version numbers stay
global.

## Risks / Trade-offs

- [A search returns postings in a language the user has no resume in] → they
  are still stored and shown; scoring them stops with the error, the agent
  asks once for the whole run instead of per posting.
