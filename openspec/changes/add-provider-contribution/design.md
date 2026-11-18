## Context

`core/providers.py` reads one directory (`providers/`, or
`JOBTRACKER_PROVIDERS_DIR` in tests). Per-user state (enabled, last result)
is keyed by provider id in the database. User mode forbids editing source
files, so a cloner cannot add a site today without breaking that rule.

## Goals / Non-Goals

**Goals:** a cloner can add, prove, and use a site without touching the
repository, and can contribute it back with one confirmation.

**Non-Goals:** private readers (Python code in the user's home is not
executed); automatic pull requests without the user's consent; changing how
maintainers add providers.

## Decisions

### D1. Two sources of provider files

`list_providers()` reads `providers/` (origin `repo`) and then
`<home>/providers/` (origin `private`). Same validation for both. A private
id equal to a repo id is invalid with a clear message; the repo file wins.
`JOBTRACKER_PROVIDERS_DIR` still replaces the repo directory only.

### D2. Private providers have no reader

`jt providers read <id>` refuses a private provider ("private providers are
followed step by step; they have no reader"). Allowed `access` values are
unchanged; the file must describe steps the agent can follow with its own
tools.

### D3. Proof is recorded privately

`<home>/providers/<id>.study.md` holds the study table and the proving
run ids per country. It is never copied into a PR as is: the PR's study table
is rewritten by the agent with generic search terms and counts only.

### D4. Pull request flow

The skill offers the PR only when D3 shows a successful proving run for each
country claimed and validation passes. Steps: confirm with the user; check
`gh auth status`; fork if needed (`gh repo fork --remote`); branch
`add-provider-<id>` from up-to-date `main`; copy the file to `providers/`;
write `openspec/changes/add-provider-<id>/` from
`providers/change-template/`; run `ruff check .`, `pytest`, and
`scripts/check_private.py`; commit; push to the fork; `gh pr create` with the
template filled. Any failing step stops and is reported; nothing is forced.

### D5. Paths

`docs/workspace-layout.md` gains `providers/` under the private home. The
folder is under `user-data/`, so it is already ignored by git and refused by
the privacy guard.

## Risks / Trade-offs

- [A private provider breaks a run] → It is validated like any provider and
  starts switched off; a failure is recorded per provider and never fails
  the run.
- [Personal data leaking into a PR] → D3 rewrite plus the privacy guard on
  commit.
- [Contributors without OpenSpec installed] → The change folder is written
  from plain Markdown templates; `openspec validate` runs in CI.
