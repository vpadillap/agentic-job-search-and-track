## Context

`postings.work_mode` is `remote | hybrid | onsite | NULL` (`0003_postings.sql`),
normalized from site wording by `normalize.work_mode` and written only by
`jt postings import`, which never updates an existing posting. The Search
table shows work mode in its conditions cell (`boards/search.js`), the
Applications table under the company (`boards/applications.js`). There is no
way to edit a posting field after import. Changes to applications are recorded
in `events` and shown as the application's history (`applications.history`).

## Goals / Non-Goals

**Goals:** keep the three-value work mode (filters, salary comparability, and
scoring use it) and add the human detail beside it; let the user correct both;
never lose a user's correction.

**Non-Goals:** see proposal.md.

## Decisions

### W1. Two columns: detail text and who set it
Migration `0010_work_mode_detail.sql` adds to `postings`:
- `work_mode_detail TEXT` (max 200 characters, trimmed, empty → NULL);
- `work_mode_source TEXT NOT NULL DEFAULT 'agent' CHECK (… IN ('agent','user'))`.

The enum stays as it is. A detail without a mode is allowed (a posting can say
"Fridays until noon in summer" without saying where); a mode without a detail
is the common case.

Alternatives: replace the enum with free text (breaks the work-mode filter,
the first-pass filter, and salary comparability); a separate table of posting
corrections (more machinery for two fields).

### W2. Import carries the detail; a user's value is never overwritten
`jt postings import` accepts `work_mode_detail` (string or null) and stores it
on new postings with `work_mode_source = 'agent'`. Import already never updates
an existing posting, so a user's correction survives later searches by
construction; a test pins this.

### W3. One edit function, two entry points
`search.set_work_mode(conn, posting_id, mode, detail, *, source)` validates
(mode through `normalize.work_mode`, or null; detail as in W1), updates both
columns and `work_mode_source`, bumps the change counter, and records an event
`entity_type = 'posting'`, `kind = 'work_mode'`, `data = {from: {mode,
detail, source}, to: {mode, detail}, source}`. Entry points:
- panel: `POST /api/postings/{id}/work-mode` with `{work_mode, detail}`,
  always `source = 'user'`;
- CLI: `jt postings work-mode <id> --mode hybrid|remote|onsite|none --detail
  "…"`, also `source = 'user'`: the agent uses it only to record what the user
  told it.

`applications.history` also returns these posting events for a tracked
posting, so the correction appears in the application's history.

### W4. Where the agent sees it
`postings show`, `postings list`, the Search board payload, and the
application payload include `work_mode_detail` and `work_mode_source`. Nothing
else in `context` changes. The learning loop (not built yet) can tell an
agent reading from a user correction by `work_mode_source` and the events.

### W5. Panel: one shared editor
A small component used by both boards: the work-mode chip (mode label,
then the detail in a lighter weight) is a button; activating it opens a
popover with a mode choice (Remote, Hybrid, On-site, Not stated) and a
one-line detail input, saved on "Save" (Enter) and cancelled with Escape,
following the existing menu pattern of the Applications board. A user-set
value shows a small "edited" mark with a tooltip. In the Search table the
detail appears inside the conditions cell; in the Applications table it
follows the mode under the company. Long details are truncated with an
ellipsis and shown whole in the tooltip and the row detail. New strings in
`locales/en.json` and `locales/es.json`.

### W6. Skill text
`job-search/SKILL.md`, posting record table:
- `work_mode`: decided by reading the title and the complete description, not
  by keyword matching; null when not stated;
- `work_mode_detail`: how the posting describes the arrangement when it says
  more than the mode, in the posting's language and close to its words;
  null otherwise.

First-pass filter: a posting with no stated work mode is not excluded for
work mode; it gets the flag "work mode not stated" (in the panel language).
Provider files can add site-specific guidance.

## Risks / Trade-offs

- [The agent writes a detail that the posting does not support] → the skill
  asks for the posting's own words; the user sees and can correct it, and
  the correction is recorded.
- [A user correction is lost if a posting is re-imported as a new row] →
  identity is the site's id or URL, so the same posting is never re-created.
- [Popover in a dense table] → same pattern as the existing status menu, which
  is already tested.

## Migration Plan

`0010` is additive (two nullable/defaulted columns); the existing backup runs
before it. Existing postings get `work_mode_source = 'agent'` and no detail.
Rollback: the columns are ignored by older code paths only after a code
revert plus a restore from the pre-migration backup (forward-only migrations).
