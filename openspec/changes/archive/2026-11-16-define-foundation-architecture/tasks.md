## 1. Repository scaffolding

- [x] 1.1 Add `.gitignore` covering the private home, local tooling, and OpenSpec generated skills
- [x] 1.2 Add `docs/workspace-layout.md` (storage and naming contract)
- [x] 1.3 Add `AGENTS.md` and `CLAUDE.md` with agent rules and repository map
- [x] 1.4 Add `providers/README.md` and `providers/_template.md`
- [x] 1.5 Add OpenSpec project context in `openspec/config.yaml`
- [x] 1.6 Keep `design/` as the committed UX reference, renamed to `design/panel-ux.html`

## 2. Privacy guard

- [x] 2.1 Implement `scripts/check_private.py` (private paths, blocked extensions, private terms)
- [x] 2.2 Add `.githooks/pre-commit` and document `git config core.hooksPath .githooks`
- [x] 2.3 Add CI workflow running `check_private.py --all` on every push and pull request
- [x] 2.4 Add tests for the guard covering each scenario in the `user-workspace` spec

## 3. Package skeleton

- [x] 3.1 Create `pyproject.toml` (Python >= 3.11, `jobtracker` console script, runtime and dev dependencies, ruff and pytest config)
- [x] 3.2 Create `src/jobtracker/` with `core`, `cli`, and `web` packages
- [x] 3.3 Add the fictional persona fixtures under `tests/fixtures/`
- [x] 3.4 Add CI test matrix for Python 3.11 to 3.14 on Windows, macOS, and Linux

## 4. Workspace (core)

- [x] 4.1 Implement path resolution (`JOBTRACKER_HOME`, well-known paths, job folder and slug naming)
- [x] 4.2 Implement idempotent workspace initialization and `config.toml` read/write
- [x] 4.3 Implement versioned document naming (never overwrite)
- [x] 4.4 Implement full reset as move-to-archive
- [x] 4.5 Tests for every `user-workspace` scenario

## 5. Database (core)

- [x] 5.1 Implement connection handling (WAL, foreign keys, busy timeout)
- [x] 5.2 Implement numbered SQL migrations with `PRAGMA user_version`, pre-migration backup, and newer-schema refusal
- [x] 5.3 Write migration 0001: settings, seasons, profile versions, rules, provider state, events, application snapshots, change counter
- [x] 5.4 Seed system rules (salary evidence, document language, no auto-apply, resume layout consent)
- [x] 5.5 Tests for migrations, backup, and concurrent read/write

## 6. CLI

- [x] 6.1 Implement the CLI entry point with JSON output, stderr diagnostics, and error codes
- [x] 6.2 Implement `jobtracker doctor`
- [x] 6.3 Implement `jobtracker init` and `jobtracker paths`
- [x] 6.4 Implement `jobtracker context`
- [x] 6.5 Tests for every `agent-data-interface` scenario

## 7. Web placeholder

- [x] 7.1 Add a minimal FastAPI app bound to 127.0.0.1 with a health endpoint and the change-counter endpoint
- [x] 7.2 Add `jobtracker panel` to start the server
- [x] 7.3 Test that a CLI write is visible through the API while the server runs
