## Context

Implements D2, D4, D5, D6 of `define-foundation-architecture`. The visual
reference is board 1 of `design/panel-ux.html`; colors, type, spacing, and
copy are taken from it.

## Goals / Non-Goals

**Goals:** a faithful, fast implementation of the Search board; reusable table,
filter, and expandable-row components for later boards.

**Non-Goals:** search execution; responsive layouts below desktop width.

## Decisions

### P1. Frontend structure

```
web/static/
  index.html
  app.js            router (hash-based tabs), global store, i18n loader
  api.js            fetch wrappers
  components/       Header, Tabs, CommandChip, DataTable, FilterBar, ScorePill, ...
  boards/search.js
  vendor/preact-htm.js
  fonts/            Inter, Space Grotesk, JetBrains Mono (woff2, OFL)
  tokens.css        colors/spacing from the design
```

Hash routing keeps the server a plain static host plus `/api`.
*Alternative:* one HTML page per tab (duplicated shell, full reloads).

### P2. Data loading: load once, filter in memory

Each board loads its full dataset in one request and filters/sorts on the
client; type-ahead is instant and works offline. Datasets are small (tens of
results per run, hundreds of applications).
*Alternative:* server-side filtering per keystroke (more API surface, slower).

### P3. Freshness without websockets

The panel polls `/api/changes` (a counter bumped by every write from CLI or
API) every few seconds while visible and reloads the active board when it
changes, unless the user is mid-edit, in which case it shows a "new data"
prompt. The header shows the time of the last change and a manual reload.
*Alternative:* websockets or server-sent events (more moving parts for a
single-user tool).

### P4. Postings model (introduced here, filled by `add-job-search`)

`search_runs` (started, posting age, titles used, per-provider counts and
skips), `postings` (provider, external id, URL, title, company, location, work
mode, contract type, posted date, verbatim description, published salary,
form-question count, flags), `run_results` (posting × run, outcome: new,
filtered with reason, duplicate, already seen). The Search board shows the
latest run by default and can open earlier runs.

### P5. Row actions and feedback capture

Track and Track-and-mark-applied create the application record (the second
also sets status Applied and today's date). Dismiss requires a reason from
quick options (industry, low salary, location, stack, other with text);
dismissed postings leave the default view and the reason is stored as learning
input. All actions are undoable from a toast for a few seconds.

### P6. Default filter comes from rules

The default minimum score shown is read from active rules (initially none), so
the learning loop can raise it later. The footer always states how many rows
are hidden and why.

### P7. i18n

All static strings come from locale files; switching language re-renders
without reload and persists. Dates, numbers, and currency use the browser's
`Intl` with the panel locale. Agent-written text is shown as stored.

### P8. Safety

Posting descriptions are rendered as text, never as HTML. External links open
in a new tab with `noopener`. The server binds to loopback and rejects requests
whose `Host` header is not a loopback name (DNS-rebinding protection).

## Risks / Trade-offs

- [Vendored library goes stale] → single pinned file with its version and
  license recorded; updating is a one-file change.
- [Polling while the agent writes many rows] → counter is bumped once per CLI
  command, not per row.
- [Design drift] → tokens file is the only place colors and sizes are defined.
