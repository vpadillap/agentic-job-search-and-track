## Why

The panel is how the user sees and acts on what the agent finds. Building the
shell and the Search board first, against demo data, fixes the frontend
foundations (layout, i18n, refresh, table behaviors) that every other board
reuses.

## What Changes

- Add the panel shell from `design/panel-ux.html`: header with brand, active
  profile, pending-for-agent indicator, data freshness, language toggle, and
  the four tabs (Search, Applications, Learning, Profile & agent; the last
  three as placeholders until their changes land).
- Add the Search board: last-run summary, filters, type-ahead search, sorting,
  results table, expandable row (original description, score breakdown, salary
  suggestion with evidence), and row actions (Track, Track and mark applied,
  Dismiss with reason), including bulk actions.
- Add the read/write API for postings and run results, and a demo seed with
  fictional data.

## Non-goals

- Producing search results (see `add-job-search`); this change renders stored
  data and the demo seed.
- The Applications board itself: tracking actions here only create the tracked
  record.
- Mobile layout.

## Capabilities

### New Capabilities

- `panel-shell`: the local web panel frame: tabs, language, data freshness,
  copyable agent commands, local-only access.
- `search-results-board`: viewing, filtering, and acting on the postings of the
  latest search.

### Modified Capabilities

None.

## Impact

- New: `src/jobtracker/web/static/` (ES modules, vendored Preact + htm, fonts,
  design tokens), `locales/en.json`, `locales/es.json`, API routes under
  `/api`, postings/run tables (migration), `jobtracker demo seed`.
- Depends on `define-foundation-architecture`. Works without
  `add-setup-onboarding` when demo data is seeded.
