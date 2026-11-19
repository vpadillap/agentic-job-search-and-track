# Agent instructions

Agentic Job Search and Track (Python package and CLI: `jobtracker`) is a
clone-and-run, local-first job search assistant: an AI agent (primarily Claude
Code) searches, scores, and prepares application documents; a local web panel
shows and edits the results; every outcome feeds back into future advice.

> Status: everything is implemented: first-run setup (`/setup`, versioned
> profile, Spanish command aliases), the private workspace, database,
> `jobtracker` CLI, and privacy guard; `/job-search` (runs, import, filtering,
> scoring, salary evidence) over seven providers in `providers/` (LinkedIn,
> Indeed, Glassdoor, Greenhouse, Get on Board, Bumeran Perú, and the agentic
> web search), each switched off until the user enables it, global or local
> (`regions`), read by `jobtracker providers read …` where a reader exists,
> with missing tools installed by `jobtracker providers install`; application
> tracking; document preparation (`/prepare-documents`, `/form-answers`); the
> learning loop (`/analyze-results`); seasons (`/new-season`, export, full
> reset); the panel with its four boards (`/panel`); private providers and
> their contribution (`/add-provider`); self-update with one-time offers
> (`/update`); and plain-language requests routed to
> the skills (table below). `jobtracker context` lists which commands are
> available.

## Which mode are you in?

- **User mode**: someone cloned the repo to run their own job search. They
  invoke skills such as `/setup` or `/job-search`. Follow the skill, write only
  under `user-data/`, never modify source files.
- **Contributor mode**: someone is developing this project. Follow the
  OpenSpec workflow below and never put real personal data in the repo.

If it is unclear, ask.

## User mode: plain requests

Users may type a command or just ask, in English or Spanish. When a request
matches a row, load that skill (its "When the request is in plain words"
section says how to fill in its arguments) even if it did not load on its own.
A question that only needs an answer ("what is a cover letter?") is answered,
not turned into a task. A request outside every row: do it with `jt` if a
command covers it, otherwise say what the closest command is.

| The user asks… | Skill |
|---|---|
| to get started, set things up, change the language, resume, job needs, titles, job sites, or their own rules ("configura el proyecto") | `/setup` |
| to search for jobs, look for new postings ("busca trabajo de esta semana") | `/job-search` |
| to prepare resumes, cover letters, or everything missing for applications ("completa los documentos de la J0007") | `/prepare-documents` |
| only for answers to an application form ("responde el formulario de la J0007") | `/form-answers` |
| how they are doing, why nobody calls, what to change ("analiza mis resultados") | `/analyze-results` |
| to start over after a pause or in a new field ("empezar una nueva temporada") | `/new-season` |
| to add a job site the project does not have yet ("agrega Computrabajo como portal") | `/add-provider` |
| to open or close the panel ("abre el panel") | `/panel` |
| to update the project to the latest version ("actualiza el proyecto") | `/update` |
| to change a status, tag, or detail of an application ("pasa la J0007 a entrevista") | no skill: `jt applications …` |

## Non-negotiable rules

1. **Privacy boundary.** All personal data goes under `user-data/` (or
   `JOBTRACKER_HOME`) following `docs/workspace-layout.md` exactly: same paths,
   same names. Nothing personal goes into source, skills, providers, docs,
   specs, tests, commit messages, or PRs. Use the fictional persona in
   `tests/fixtures/` for examples. Do not bypass the pre-commit privacy guard.
2. **One write path.** Structured data changes go through the `jobtracker` CLI
   (or the panel API). Never hand-edit the database. Start every task with
   `jobtracker context`; get every private path from `jobtracker paths`.
3. **No invented facts.** A salary suggestion is the agent's analysis and
   always cites its sources: one is enough when it is a reference for the same
   company or the user's own history (offers received, salaries published in
   stored postings); a suggestion resting only on the market needs at least
   two comparable sources with links (same country, level, currency, and
   basis). A short note says what it rests on. Nothing comes from the model's
   own knowledge; otherwise record "no reliable data". The same applies to
   resumes and form answers: never claim experience the user's resume and
   profile do not support.
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
| `.claude/skills/` | User-facing skills (canonical, English names) |
| `i18n/skill-aliases/` | Templates of the Spanish command names; installed by `jobtracker skills sync`, never edited in `.claude/skills/` |
| `providers/` | One file per job site: how the agent must access and read it; `CONTRIBUTING.md` (rules for adding a site) and `change-template/` (the OpenSpec change a new-site pull request carries) |
| `CONTRIBUTING.md` | How to set up, the change workflow, and the checks before a pull request |
| `tests/skill-evals/` | Plain-language requests each skill must (and must not) load for |
| `openspec/` | Specs and change proposals (spec-driven development) |
| `design/` | UX reference for the panel (four boards: Search, Applications, Learning, Profile & agent) |
| `src/jobtracker/` | `core` (storage, rules), `cli` (agent interface), `web` (panel) |
| `scripts/check_private.py` | Privacy guard (pre-commit + CI) |
| `scripts/jt.py` | Runs the CLI from the clone before anything is installed |
| `user-data/` | Private home, gitignored, created by `/setup` |

## Contributor workflow

- Spec-driven with OpenSpec: propose a change under `openspec/changes/<name>/`
  (proposal, design, spec deltas, tasks), get it approved, implement, archive.
  Validate with `openspec validate <name> --strict`.
- One change at a time, in this order: implement with `/opsx:apply`, verify
  with `/opsx:verify`, archive with `/opsx:archive`, commit, then merge into
  `main`. Every change ends merged into `main` before the next one starts.
- Stay inside the change being applied. Do only its tasks. Do not make
  decisions that belong to another change, and do not edit other changes'
  proposals, designs, specs, or tasks. If something outside the scope seems
  necessary, stop and ask the project owner.
- Providers are out of scope everywhere except in their own change: each job
  site gets an individual study and its own change, and how it is accessed is
  decided only there.
- OpenSpec's generated skills/commands are gitignored on purpose. Install them
  locally with `openspec init --tools claude` if you want them.
- After cloning: `git config core.hooksPath .githooks` to enable the privacy
  guard, then `uv sync --extra dev` (or `pip install -e ".[dev]"` in a venv),
  then `uv run playwright install chromium` so the panel's browser tests run
  instead of being skipped. Details in `CONTRIBUTING.md`.
- Cloners who add a job site for themselves (user mode) follow
  `providers/CONTRIBUTING.md` through `/add-provider`; it may end in a pull
  request built from `providers/change-template/`.
- Before committing: `uv run ruff check .` and `uv run pytest`. Tests run
  against a temporary `JOBTRACKER_HOME`; never point them at real data.
- The CLI prints JSON (`{"ok": true, …}` or `{"ok": false, "error": …}`).
  `core` must stay standard-library only so `doctor` works on a bare Python.
- Repo content (code, docs, skills, specs) is written in English. User-facing
  panel text is localized (en/es).
