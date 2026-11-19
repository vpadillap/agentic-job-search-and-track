## Context

The project runs from a clone (`scripts/jt.py` hands over to `.venv`). User
data lives in `user-data/` (or `JOBTRACKER_HOME`), gitignored; private
providers live there too. The database migrates on open (`db.migrate`, with a
backup in `user-data/backups/`). Spanish aliases are copied by `jt skills
sync`; tools of enabled providers are installed by `jt providers install`.

## Goals / Non-Goals

**Goals:** one request brings the latest version and leaves everything
working; user data never changes except through migrations and offers the
user accepted; a failure can be undone.

**Non-Goals:** automatic updates without the user asking; updating a fork's
own changes (a contributor uses git); downgrading.

## Decisions

### D1. The pull is a visible git step

`git pull --ff-only origin main` is run by the skill, not hidden inside the
CLI, so the user sees it and git's own messages. Before it, `jt update check`
must say `fast_forward: true` and `tracked_changes: []`. A diverged or dirty
clone is never forced: the skill explains and asks (keep the user's edit in a
stash and re-apply after, or stop).

### D2. `jt update check`

Runs `git fetch origin` and reports: `branch`, `current` and `remote`
commits, `behind` (count and one-line subjects), `ahead`, `fast_forward`,
`tracked_changes` (paths from `git status --porcelain`, excluding untracked
files), `new_providers` (provider files in the remote that are not in the
working tree), and `schema_from`/`schema_to`. It changes nothing in the
working tree or the database.

### D3. `jt update finish`

After the pull: reinstall (`uv sync` when `uv` is available and was used,
else `.venv` pip `install -e .`), open the database (migrates, with backup),
`skills sync <language>`, `providers install --enabled`, `doctor`. Each step
reports `ok` and what it did; the command is safe to run twice.

### D4. One-time offers

`core/offers.py`: `Offer(id, text_en, text_es, applies(conn, paths) -> bool,
apply(conn, paths) -> dict)`. Answers in a table `offers (id, answer,
answered_at)`. `jt offers list` returns pending offers that apply;
`accept` runs `apply` and records `accepted`; `decline` records `declined`.
An offer is never presented again once answered. Offers are registered by the
change that needs them (for example `group-searches-by-day`).

### D5. Restoring

The skill records the commit before the pull. On a failed `finish`, it
reports `git reset --hard <previous commit>` and the database backup path as
the way back, and asks before running either.

## Risks / Trade-offs

- [The user edited a tracked file] → Detected by `check`; nothing discarded
  without a yes; a stash keeps the edit.
- [A migration fails] → The backup taken on open restores the database; the
  skill names it.
