## Why

When the user asks whether an update is worth it, or after an update, the
agent can only read commit subjects, which are written for developers. The
owner wants every merge into `main` to (a) update the documentation it
affects and (b) add an entry to a changelog that says in plain language what
was added, changed, or fixed, so that the agent can tell the user exactly
what an update brings ("Computrabajo was added as a job site; two fixes to
the salary column") and offer what fits: turning on a new job site and
searching it now, or running today's full search including it.

## What Changes

- **`CHANGELOG.md`** at the repository root, newest first. One entry per
  change merged into `main`: date, the change's name, and short plain-
  language lines under **Added**, **Changed**, **Fixed**, written for the
  user (what they can now do or what behaves differently), not for
  developers. Machine-readable lines the agent uses: `Providers: <ids>` (new
  job or salary sites), `Offers: <ids>` (one-time offers it brings), `Action:`
  when the user must do something.
- **The rule**: every change merged into `main` adds its entry and updates
  the documentation it affects (README en/es, provider files, skills,
  `docs/`). `AGENTS.md` and `CONTRIBUTING.md` say so; the OpenSpec workflow's
  archive step includes it; a CI check fails a pull request that changes
  code, providers, or skills without touching `CHANGELOG.md`. Entries for the
  changes already merged are written once (backfill), from their proposals.
- **`jt update check`** also returns `changes`: the changelog entries in the
  remote that the local clone does not have yet, parsed (date, change, the
  lines of each kind, providers, offers, actions).
- **`/update`** uses them: "is it worth updating?" is answered with what the
  entries say, in the user's language; after an update, for each new job
  site it asks whether to turn it on (with the site's terms note, as setup
  does) and then whether to search only that site now or run today's full
  search including it; new salary sources are offered the same way, to be
  used from the next search.

## Capabilities

### New Capabilities

- `changelog`: a user-facing changelog kept with every merge, and its check.

### Modified Capabilities

- `self-update`: what is new comes from the changelog, and new job sites are
  offered after the update.

## Impact

- `CHANGELOG.md` (new, with backfill), `AGENTS.md`, `CONTRIBUTING.md`,
  `.github/workflows/ci.yml` (the check), `core/update.py` (parse entries),
  `.claude/skills/update/SKILL.md`, tests, README (en/es).
