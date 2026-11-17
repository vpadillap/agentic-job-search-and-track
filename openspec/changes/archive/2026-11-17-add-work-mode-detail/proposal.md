## Why

A posting's work mode is stored as one of three words (remote, hybrid,
onsite), but postings say much more: "hybrid, two days a week at the office",
"summer hours: Fridays until noon", "early Friday". That detail matters to the
user's decision and is lost today. Some sites (LinkedIn, for visitors) do not
even show a work-mode field, so the agent has to read it from the text, and
where the agent cannot read a posting at all, the user has to be able to fill
it in after opening the posting. `add-provider-linkedin` depends on this.

## What Changes

- Postings gain a **work-mode detail**: free text, in the posting's language,
  saying how the posting describes the arrangement, next to the existing work
  mode.
- The agent fills work mode and detail by reading the posting's title and
  complete description with its own judgment; `jt postings import` accepts the
  new field, and `/job-search` explains how to fill both. Each provider file
  may add site-specific instructions.
- A posting whose work mode is not stated is not excluded for its work mode;
  it stays with a flag.
- The panel shows the detail with the work mode: in the conditions cell of
  the Search table, and next to the work mode in the Applications table.
- The user can set or correct the work mode and its detail from either table.
  The edit is saved immediately, recorded as the user's (with the previous
  value in the history), never overwritten by a later import, and visible to
  the agent.
- `jt postings work-mode <id>` does the same from the CLI, so the agent records
  corrections the user asks for through the one write path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `job-search`: "Verbatim capture" also stores the work mode and its detail as
  read from the posting; "First-pass filter with reasons" does not exclude a
  posting for an unstated work mode.
- `search-results-board`: "Results table" shows the work-mode detail and lets
  the user edit work mode and detail in the row.
- `applications-board`: "Table of all tracked applications" shows the detail;
  "Inline editing" includes work mode and detail.

## Non-goals

- Re-filtering or re-scoring when the user corrects a work mode (the user
  already sees the posting; scoring can be redone with the existing
  commands).
- Editing other posting fields (title, company, location, contract type) by
  hand.
- Any provider file or site-specific reading rules; those belong to each
  provider's change.

## Impact

- Database: migration `0010` adds the detail and who last set the work mode
  to `postings`.
- `core/normalize.py`, `core/search.py` (import, posting output), a small
  core function for the manual edit with an event in `events`.
- CLI: new `jt postings work-mode`; `postings show` and `postings list`
  include the new fields.
- Panel API: one endpoint to set a posting's work mode; `/api/search` and
  `/api/applications` include the detail.
- Frontend: `boards/search.js`, `boards/applications.js`, a shared editor
  component, locale strings (en/es), CSS.
- Skill: `.claude/skills/job-search/SKILL.md` (posting record and filter).
- Demo data gains a few details so the panel shows them.
- Tests: core, CLI, API, browser.
