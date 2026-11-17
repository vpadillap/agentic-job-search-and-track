## Why

A person who clones the repo needs one command that takes them from nothing to
a personalized, working installation, and that leaves them knowing how to use
it. This is also where the profile that drives every later feature is created.

## What Changes

- Add the `/setup` skill: environment check and guided installation, panel
  language choice (English or Spanish) as the first question, resume intake,
  job-needs questionnaire, target-title research with user confirmation,
  provider selection, workspace creation, and a closing guided tour.
- Add the versioned profile (job needs and target titles) and its CLI commands.
- Add Spanish command aliases, installed only for users who choose Spanish.
- Write the full README (English, with a Spanish section) documenting every
  command, the privacy model, and troubleshooting.

## Non-goals

- Searching for jobs or scoring them (see `add-job-search`).
- Any panel UI beyond confirming it starts.
- Editing the profile from the panel; the profile is changed by talking to the
  agent.

## Capabilities

### New Capabilities

- `setup-onboarding`: the first-run flow from dependency check to guided tour.
- `profile`: the versioned description of who the user is and what they want
  (job needs, target titles and their states, base resume).
- `skill-localization`: Spanish alias commands and localized command display.

### Modified Capabilities

None.

## Impact

- New: `.claude/skills/setup/`, `i18n/skill-aliases/es/`, profile tables
  (migration), `jobtracker profile …`, `jobtracker resume …`,
  `jobtracker skills sync`, `README.md`.
- Optional dependencies installed on demand: a PDF/DOCX text extractor
  (`pypdf`, `python-docx`), browser tooling required by selected providers.
- Depends on `define-foundation-architecture`.
