## Context

`add-setup-onboarding` stores one current base resume (`base_resumes`, with a
version history). `add-document-preparation` tailors from it and, when the
posting is in another language, translates it.

## Goals / Non-Goals

**Goals:** the user's own translations are used whenever they exist; adding a
language is just importing a file; nothing else in the workflow changes.

**Non-Goals:** managing translations, syncing versions across languages.

## Decisions

### R1. One current base resume per language

`base_resumes` gains `language` (ISO 639-1 code, as the user states it) and
`is_main`. There is at most one current base resume per language, each with
its own version history. Exactly one current base resume is the main one.

Files: `profile/resume-base-<lang>.<ext>` and `profile/resume-base-<lang>.md`
(extracted text); earlier versions `resume-base-<lang>-v<N>.<ext>`, where `<N>`
is the global base-resume version number (shared by all languages). Files of a
base resume imported before this change keep their names.

*Alternative:* language variants attached to the main resume as children
(more structure, no benefit: each version is just a file the user owns).

### R2. Main base resume

The main base resume is what scoring is judged against and the source for
translation when no base exists in a posting's language. The first base resume
imported is the main one; `resume main <code>` changes it. Replacing the main
base resume with a new version triggers rescoring as today; importing or
replacing a non-main language version does not (same content, different
language).

### R3. Choosing the base for a tailored resume

`documents tailor` looks up the posting's language and uses the current base
resume in that language; if there is none, it uses the main one and the result
says `translate: true` so the agent knows it must translate (existing guide).
`--base <code>` overrides the choice. Each document records the base resume it
came from (`base_resume_id`), and `documents diff` compares against that one.

### R4. Existing workspaces

The migration marks the existing current base resume as main with no language.
`jobtracker context` reports it as `language: null`, and the setup and
prepare-documents skills ask the user once and run `resume language <code>`.
Until then tailoring treats it as the main resume of unknown language, exactly
as today.

## Risks / Trade-offs

- [The user's language versions differ in content (one updated, the other
  not)] → the context lists each base resume with its import date; the
  tailoring guide tells the agent to mention when the version it uses is older
  than the main one.
- [Wrong language code given] → the agent confirms the language after reading
  the extracted text, as it already confirms the summary.

## Migration Plan

Forward-only migration: add the columns, set the existing current base resume
as main. No files are renamed.
