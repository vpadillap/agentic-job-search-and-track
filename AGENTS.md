# Agent instructions

Claude Job Tracker is a clone-and-run, local-first job search assistant: an AI
agent (primarily Claude Code) searches, scores, and prepares application
documents; a local web panel shows and edits the results; every outcome feeds
back into future advice.

> Status: early scaffolding. The architecture is proposed in
> `openspec/changes/define-foundation-architecture/`. Until that change is
> applied, the `jobtracker` package, the panel, and the user-facing skills do
> not exist yet.

## Which mode are you in?

- **User mode**: someone cloned the repo to run their own job search. They
  invoke skills such as `/setup` or `/job-search`. Follow the skill, write only
  under `user-data/`, never modify source files.
- **Contributor mode**: someone is developing this project. Follow the
  OpenSpec workflow below and never put real personal data in the repo.

If it is unclear, ask.

## Non-negotiable rules

1. **Privacy boundary.** All personal data goes under `user-data/` (or
   `JOBTRACKER_HOME`) following `docs/workspace-layout.md` exactly: same paths,
   same names. Nothing personal goes into source, skills, providers, docs,
   specs, tests, commit messages, or PRs. Use the fictional persona in
   `tests/fixtures/` for examples. Do not bypass the pre-commit privacy guard.
2. **One write path.** Structured data changes go through the `jobtracker` CLI
   (or the panel API). Never hand-edit the database.
3. **No invented facts.** Salary suggestions require at least two comparable
   sources with links (same country, level, work mode, and similar
   industry/company size). Otherwise record "no reliable data". The same
   applies to resumes and form answers: never claim experience the user's
   resume and profile do not support.
4. **Consent for heavy changes.** Do not change a resume's layout or structure
   without the user's explicit consent; content edits only by default.
5. **The agent never submits applications.** It prepares; the user applies.
6. **Respect active rules.** Before any search, scoring, or document work, load
   the active rules (user preferences and approved lessons) and follow them.
7. **Provider files are binding.** For each job site, follow
   `providers/<name>.md` (access method, pacing, what not to do).
8. **Language.** The panel language (en/es) is a UI setting. Documents and form
   answers are written in the language of each job posting.

## Repository map

| Path | Purpose |
|---|---|
| `docs/workspace-layout.md` | Storage contract: where/how private data is stored and named |
| `providers/` | One file per job site: how the agent must access and read it |
| `openspec/` | Specs and change proposals (spec-driven development) |
| `design/` | UX reference for the panel (four boards: Search, Applications, Learning, Profile & agent) |
| `scripts/check_private.py` | Privacy guard (pre-commit + CI) |
| `user-data/` | Private home, gitignored, created by `/setup` |

## Contributor workflow

- Spec-driven with OpenSpec: propose a change under `openspec/changes/<name>/`
  (proposal, design, spec deltas, tasks), get it approved, implement, archive.
  Validate with `openspec validate <name> --strict`.
- OpenSpec's generated skills/commands are gitignored on purpose. Install them
  locally with `openspec init --tools claude` if you want them.
- After cloning: `git config core.hooksPath .githooks` to enable the privacy
  guard.
- Repo content (code, docs, skills, specs) is written in English. User-facing
  panel text is localized (en/es).
