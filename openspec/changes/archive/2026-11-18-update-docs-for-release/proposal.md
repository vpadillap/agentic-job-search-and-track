## Why

The project is about to be left open on GitHub for contributions. The
documentation lags behind the code: the README still lists seasons and
`/panel` as planned, names three job sites, has no section for contributors
or for adding job sites, and does not describe asking in plain words. The
owner also renamed the project's title in the README (to "Agentic Job Search
and Track"), which the rest of the docs should follow. This change is the
last one: it runs after every other change in this batch is merged.

## What Changes

- **README (English and Spanish sections):** the new title; an accurate
  status table; every job site with global/local coverage and access; the
  commands and the plain-language way of asking; how to add your own job site
  (`/add-provider`) and contribute it; a "Contributing" section pointing to
  `CONTRIBUTING.md`.
- **New `CONTRIBUTING.md`** at the root: contributor setup (hooks, `uv sync
  --extra dev`, Playwright Chromium for browser tests), the OpenSpec workflow,
  the privacy rules, how to add a provider (link to
  `providers/CONTRIBUTING.md`), checks before a PR.
- **`AGENTS.md`:** status paragraph updated to what exists; repository map
  includes the new files; the contributor setup mentions Chromium (closes the
  first `docs/backlog.md` item).
- **`docs/workspace-layout.md`, `providers/README.md`, `design/`**: checked
  against the code and corrected where they differ.
- **`docs/backlog.md`:** items that this batch resolved are removed.
- Every command and path written in the docs is checked against the code
  (`jt context`, skill names, file paths).

## Capabilities

### New Capabilities

- `project-documentation`: what the public documentation must cover and keep
  accurate.

### Modified Capabilities

None.

## Impact

- `README.md`, `CONTRIBUTING.md` (new), `AGENTS.md`, `docs/`, `providers/README.md`.
- No code changes. A test checks that every slash command named in the README
  exists as a skill.
