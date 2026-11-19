---
name: update
description: "Updates this copy of Job Tracker to the latest version from the repository and leaves everything working (packages, database, command names, job-site tools), without touching the user's data. Use when the user asks to update, upgrade, or get the latest version, or whether there is a new version, such as “update the job tracker”, “is there a new version?”, “get the latest changes” (also in Spanish: “actualiza el proyecto”, “hay una versión nueva?”, “trae los últimos cambios”). Not for updating the user's profile or resume (that is setup)."
---

# Update

Brings this clone to the latest version of the project and leaves it working.
The user's data (`user-data/`, or `JOBTRACKER_HOME`) is never changed, moved,
or deleted, except by database migrations (which back up the database first)
and by offers the user accepts.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(use `python3` if `python` is not available). It prints JSON:
`{"ok": true, ...}` or `{"ok": false, "error": {"code", "message"}}`.
Below, `jt` means `python scripts/jt.py`.

Talk to the user in the panel language (`jt context` → `language`; English
when there is no workspace yet).

## When the request is in plain words

"Update", "upgrade", "get the latest version", "is there a new version?",
"actualiza el proyecto", "trae lo último": this skill. Only asking whether
there is a new version: run step 1 and report; pull only if the user then
says yes. Updating their profile, resume, or titles is `/setup`, not this.

## 1. Check

`jt update check`. It fetches and changes nothing. Then:

- `up_to_date: true` → say it is already the latest version and stop.
- `on_main: false` → the clone is on branch `branch` (someone is developing
  here). Say so and stop; updating a development branch is done with git by
  the person working on it.
- `tracked_changes` not empty → files of the project were edited by hand.
  Name them and ask: keep the edits aside (`git stash push -- <files>`), update,
  and put them back afterwards (`git stash pop`; if git reports a conflict,
  stop and show it), or stop. Never discard them, never `git checkout --` or
  `reset` them.
- `fast_forward: false` with `ahead` > 0 → the clone has its own commits.
  Explain that it cannot be updated without merging them, and stop; never
  force, rebase, or reset.

## 2. Say what is new and ask

Summarize `new_commits` (`behind` changes) in a few plain lines, not a list
of commit ids. Mention new job sites (`new_providers`: they arrive switched
off) and a database upgrade when `schema_to` is greater than `schema_from`
(it is backed up first). Ask whether to update now.

## 3. Pull

Remember `restore` (the previous version). Run the `pull` command shown by
`check` (`git pull --ff-only origin main`) so the user sees git's own output.
If it fails, show the message and stop; nothing else has changed.

## 4. Finish

`jt update finish`. It reinstalls the packages, opens the database (upgrading
it with a backup), refreshes the command names, installs the tools of the
enabled job sites, and runs the diagnostics. It is safe to run again.

- `ok_all: true` → say the update is done and everything checks out. If new
  job sites came, offer to switch them on (`/setup`, step "job sites").
- `ok_all: false` → stop. Say which step failed (`failed_step`) and its
  detail. Try the step's own fix once when it is clear (for example a
  network failure: run `jt update finish` again). If it still fails, give the
  user the way back and ask before using it: the previous version
  (`git reset --hard <previous commit>` from `restore`) and, when the
  database step failed, the backup in `backup` (copy it over the database
  file shown by `jt paths`). Never run either without a yes.

## 5. Offers

`offers` in the result of `finish` (also `jt offers list`) are one-time
offers that came with the update, for example applying a new behavior to
earlier data. Present each one once, in its `text`, and ask. Yes: `jt offers
accept <id>` and say what it did (`result`). No: `jt offers decline <id>`. An
answered offer is never shown again.

If the user stashed edits in step 1, put them back now (`git stash pop`).
