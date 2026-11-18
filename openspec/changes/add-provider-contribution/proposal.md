## Why

Anyone who clones the project may need a job site we do not ship: a local
board in their country, a niche site for their field. Today the only way is
to edit `providers/` in the repository, which user mode forbids, and there
are no written rules for how a new site must be studied, tested, and shared.
The owner wants clear rules and a guided workflow for cloners: add a provider
for yourself first, prove it works, and then the agent offers to contribute
it back as a pull request. (The maintainers keep using the OpenSpec workflow
in `AGENTS.md`; this workflow is for cloners.)

## What Changes

- **Private providers.** A provider file can live in the user's private home,
  `user-data/providers/<id>.md` (under `JOBTRACKER_HOME`), following
  `docs/workspace-layout.md`. It is listed, validated, enabled, and searched
  like a repository provider, and is marked `origin: private`. A private file
  whose id is already used by a repository provider is reported invalid
  ("id already used by providers/<id>.md"). Private providers have the same
  power as the repository's: any access method, any dependencies, and their
  own **reader** (`user-data/providers/<id>.py`, the same interface as the
  repository readers and free to use `readers/common.py` for pacing, state,
  seen postings, and stop rules). `jt providers read <id>` runs a private
  reader exactly like a built-in one.
- **Rules for adding a provider** (`providers/CONTRIBUTING.md`, linked from
  `providers/README.md` and the root README):
  - Study first, with real requests, logged out: try plain HTTP, headless
    browser, visible browser, and (only if needed) the user's own browser
    through the extension; record each route and its result in a table.
  - Never pass credentials to automation; never use stealth tools or proxies;
    read-only always.
  - Global or local: `regions` as defined in `add-provider-coverage`; a local
    site with several countries is verified in each country (dated row in
    `## Countries`).
  - Proved = `jt providers validate` passes, and a real `/job-search` with at
    least one included title returns postings with complete descriptions,
    imported without errors, for each country claimed.
  - Terms-of-use risk stated in the file.
- **New skill `/add-provider`** (Spanish alias `/agregar-proveedor`), user
  mode: asks for the site, runs the study with the user, writes
  `user-data/providers/<id>.md` from the template, writes a reader with tests
  (fictional pages) when the site needs one, installs any dependency after
  asking, validates it, runs the proving search per country, records the
  study in
  `user-data/providers/<id>.study.md` (private: it may contain search
  results), and enables the provider for the user.
- **Offer a pull request** once the provider is proved: the agent asks the
  user; if they agree, it checks `gh` and the user's fork, creates a branch
  `add-provider-<id>`, copies the provider file into `providers/` (and its
  reader into `src/jobtracker/core/readers/<id>.py` with a registry entry and
  its tests into `tests/`, dependencies into `pyproject.toml` extras), writes the
  OpenSpec change `openspec/changes/add-provider-<id>/` (proposal with the
  study table, spec, tasks marked done) from a template, runs `ruff`,
  `pytest`, and the privacy guard, and opens the pull request with
  `gh pr create` using the repository's PR template. Nothing personal goes
  into the PR: the study table uses generic titles, not the user's searches
  or results. If the user declines, nothing leaves their machine.
- `.github/pull_request_template.md` with a "new provider" checklist.

## Capabilities

### New Capabilities

- `provider-contribution`: private providers, the rules a new provider must
  meet, the `/add-provider` workflow, and the pull-request offer.

### Modified Capabilities

- `provider-recipes`: providers are read from the repository and from the
  user's private home.

## Impact

- `core/providers.py` (second directory, `origin`, id clash), `core/paths.py`
  (private providers folder), `docs/workspace-layout.md`.
- Panel: a "Private" tag next to private providers (en/es).
- New skill `.claude/skills/add-provider/` and its Spanish alias template in
  `i18n/skill-aliases/es/`; `jt context` lists it.
- `providers/CONTRIBUTING.md`, `.github/pull_request_template.md`, an OpenSpec
  change template for provider PRs under `providers/`.
- Tests: private provider listed, validated, enabled, searched; id clash; the
  private folder is ignored by git and refused by the privacy guard.
