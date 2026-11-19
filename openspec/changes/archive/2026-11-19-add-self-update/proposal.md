## Why

Users run the project from a clone. When the project gets a fix or a new job
site, today nothing tells them how to get it, and a plain `git pull` is not
enough: the Python packages may need reinstalling, the database may need a
migration, Spanish command names may need refreshing, an enabled job site may
need a new tool, and a change may want to offer something once (for example
grouping old searches, see `group-searches-by-day`). The owner wants the agent
to update the project from the repository on request, never touch the user's
files, and leave everything working again.

## What Changes

- **New skill `/update`** (Spanish alias `/actualizar`; plain requests such as
  "update the project", "is there a new version?", "actualízate"). It:
  1. checks the clone: a git repository with the `origin` remote, on `main`
     (or says which branch it is on and asks), and no changes to tracked
     files (a user who edited a source file is asked what to do; nothing is
     discarded without their yes). `user-data/` is gitignored, so it is never
     touched;
  2. fetches and says what is new (the commits since the installed version,
     in plain words, plus new job sites, which arrive switched off);
  3. with the user's yes: backs up the database, `git pull --ff-only`,
     reinstalls the project into its `.venv`, migrates the database, refreshes
     the command names for the panel language (`jt skills sync`), installs
     what enabled job sites need (`jt providers install --enabled`), and runs
     `jt doctor` until everything passes;
  4. presents the **one-time offers** the update brought (below) and applies
     the ones the user accepts;
  5. reports what changed and that the user's data is as it was.
  If a step fails, it stops, says what failed, and how the previous version
  can be restored (the commit it came from and the database backup).
- **New CLI**: `jt update check` (current and remote version, commits behind,
  tracked files changed, whether a pull can be a fast-forward; changes
  nothing) and `jt update finish` (migrate, skills sync, providers install,
  doctor; idempotent). The pull itself stays a visible git command the skill
  runs, so the user sees it.
- **One-time offers**: a small registry in the code (`core/offers.py`) where a
  change can declare an offer: an id, a sentence for the user (en/es), a
  check of whether it applies to this user's data, and the action. `jt offers
  list` shows the pending ones; `jt offers accept <id>` / `decline <id>`
  records the answer in the database (asked once). `/update` and `/setup`
  present pending offers; nothing is applied without the user's yes.
- `README.md`: "Updating" section (and the Spanish one).

## Capabilities

### New Capabilities

- `self-update`: updating the clone from the repository without touching user
  data, and one-time offers that a change brings.

### Modified Capabilities

None.

## Impact

- New skill `.claude/skills/update/` and alias template
  `i18n/skill-aliases/es/actualizar/`; `core/skills.py` command list.
- New `core/update.py`, `core/offers.py`, a migration for the offers' answers;
  CLI `update` and `offers`.
- Tests: check on a temporary git repository (behind, ahead, diverged, dirty
  tracked file, untracked user data), finish (idempotent), offers registry
  (applies, accepted once, declined once).
