## Context

`jt update check` already fetches and lists new commits and provider files
from `origin/main`; `/update` pulls and finishes. There is no changelog.

## Goals / Non-Goals

**Goals:** a changelog the user could read and the agent can parse; kept by
rule and by CI; used by `/update` to inform and offer.

**Non-Goals:** release numbers; translating the changelog (the agent speaks
the user's language).

## Decisions

### D1. Format

```
## 2026-11-19 · add-provider-computrabajo

Added
- Computrabajo is a job site in Peru, Mexico, Colombia, Chile, Argentina, and Ecuador.

Fixed
- …

Providers: computrabajo
Offers: none
Action: none
```

The heading's change name is the key. "Added/Changed/Fixed" blocks are
optional; the three last lines are always present.

### D2. New entries

`check` reads `git show origin/main:CHANGELOG.md` and the local file and
returns the entries whose change name is not in the local file, newest first.

### D3. CI check

On pull requests: if `git diff --name-only origin/main...HEAD` touches
`src/`, `providers/`, `.claude/skills/`, or `i18n/` and not `CHANGELOG.md`,
fail with a clear message. Pushes to `main` are not checked (merges come
from checked branches).

### D4. Offers after an update

The skill, after `finish`: for each id in the new entries' `Providers` that
is a job site serving the user's country (global or local with that country),
ask to turn it on (terms note from its file); then ask: search only it now
(`/job-search` limited to that provider) or run today's full search
including it. A salary source is turned on the same way and used from the
next search.

## Risks / Trade-offs

- [Forgetting the docs] → The rule is in the archive step and in review; CI
  enforces only the changelog.
