## Why

The repo is empty apart from a UX design. Before any feature is built we need
the load-bearing decisions fixed: where private data lives so it can never be
merged, how the agent and the panel share data safely, and what stack lets
anyone clone and run with only Python installed. Every later change (setup,
search, tracking, documents, learning) depends on these.

## What Changes

- Establish the private workspace: a single gitignored home (`user-data/`,
  overridable with `JOBTRACKER_HOME`) with a fixed layout and naming contract,
  plus a privacy guard (pre-commit + CI) that blocks private data from commits.
- Establish the `jobtracker` Python package with three layers: core (SQLite
  store + domain services), CLI (the agent's only write path, JSON in/out), and
  web (FastAPI panel API + static frontend). This change delivers the package
  skeleton, schema migrations, and the first CLI commands (`doctor`, `init`,
  `context`, `paths`).
- Fix the architecture decisions for the rest of the product in `design.md`
  (data model, scoring, salary evidence, statuses, rules/learning loop, skills,
  providers, i18n, seasons) and the roadmap of follow-up changes.
- Add agent instructions (`AGENTS.md`, `CLAUDE.md`), the provider file
  template, and OpenSpec project context.

## Non-goals

- No user-facing skills (`/setup`, `/job-search`, …), no panel UI, no provider
  recipes, no scoring or document generation. Each is a follow-up change listed
  in `design.md`.
- No hosted/multi-user mode, no authentication, no auto-applying to jobs.
- No committing of OpenSpec's generated agent skills.

## Capabilities

### New Capabilities

- `user-workspace`: the private home directory, its layout and naming
  contract, initialization, and the privacy guard that keeps personal data out
  of the repository.
- `agent-data-interface`: the `jobtracker` CLI contract through which agents
  read and write structured data (machine-readable output, validation,
  environment diagnostics, schema migrations, agent context bundle).

### Modified Capabilities

None.

## Impact

- New: `pyproject.toml`, `src/jobtracker/` (core, cli, web placeholders),
  `tests/`, `tests/fixtures/` (fictional persona), CI workflow.
- Already added as scaffolding with this proposal: `.gitignore`,
  `scripts/check_private.py`, `.githooks/pre-commit`,
  `docs/workspace-layout.md`, `AGENTS.md`, `CLAUDE.md`, `providers/README.md`,
  `providers/_template.md`, `openspec/config.yaml`.
- Runtime dependencies introduced: `fastapi`, `uvicorn`, `pydantic`,
  `python-multipart` (uploads). Everything else is standard library.
- Contributors must run `git config core.hooksPath .githooks` once per clone.
