## Why

Tailored resumes are written in each posting's language. Today there is only one
base resume, so whenever a posting is in another language the agent translates
the whole resume before tailoring it, and translation is where wording drifts
most (job titles, gendered forms, section names). Many people already have
their resume in two languages, translated by hand, and prefer that version.

## What Changes

- The user can give the agent a base resume per language (for example English
  and Spanish), at setup or any time later, by saying which language it is in.
  Any language works without code changes.
- When tailoring, the agent starts from the base resume in the posting's
  language. Only when there is none does it translate from the main base resume,
  as it does today.
- One base resume is the main one: the one used for scoring and as the source
  for translation. The first one imported is the main one until the user
  chooses another.
- Each tailored resume records which base resume it came from, and the
  comparison view compares against that one.
- Existing workspaces keep working: their current base resume becomes the main
  one, and the agent asks the user once which language it is in.

## Non-goals

- Translating base resumes for the user or keeping two language versions in
  sync. Each language version is the user's own file.
- Choosing the panel language from the resume.
- Cover letters and form answers keep following the posting's language as
  today; they are written fresh and need no base.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `profile`: base resumes per language, a main base resume, language of the
  existing base resume.
- `document-preparation`: tailoring starts from the base resume in the
  posting's language when one exists.

## Impact

- Migration: language and main flag on base resumes; the base resume a
  tailored resume came from.
- CLI: `jobtracker resume import <file> --language <code>`, `resume list`,
  `resume main <code>`, `resume language <code>` (sets the language of a base
  resume imported before this change); `documents tailor` picks the base by
  the posting's language (`--base <code>` to override).
- Skills: `/setup` resume step asks for other language versions; the tailoring
  guide's language section uses the matching base resume first.
- Panel: the proposed-resume card says which base resume it came from.
- `docs/workspace-layout.md`: base resume file names include the language.
