## Context

Inputs: the product brief and the UX design in `design/` (four boards: Search,
Applications, Learning, Profile & agent). The design already implies several
architectural facts that this document adopts:

- The panel never runs the agent. It shows copyable commands and a "pending
  for the agent" queue derived from the data.
- The agent explains itself: score breakdown per component, salary evidence
  with sources, lessons with evidence and Apply / Ignore / Revert.
- There are *seasons* (a new search campaign with a new profile) and *profile
  versions*.
- Agent memory (rules) is visible in the panel with its origin: user, learned,
  system.

Constraints: users have Python and Claude Code, nothing else is guaranteed;
the same clone is used for development and for the maintainer's own real job
search, so private data and source must be physically separated.

## Goals / Non-Goals

**Goals:**

- Clone → `/setup` → working panel, with Python as the only prerequisite.
- Impossible-by-default to commit personal data.
- One consistent data layer shared by agent and panel, safe under concurrent
  use, with a full event history to learn from.
- Agent behavior defined in versioned repo files (skills, providers), not in
  per-machine memory.

**Non-Goals:**

- Hosted or multi-user deployment, authentication, mobile layout.
- Auto-submitting applications.
- Running the agent from the panel (possible later via headless Claude Code).

## Decisions

### D1. Single private home, physically separate from source

All personal data lives in `user-data/` at the repo root (override:
`JOBTRACKER_HOME`). Layout and naming are fixed in `docs/workspace-layout.md`.
Three layers of protection: `.gitignore`; `scripts/check_private.py` as
pre-commit hook and CI job (blocks private paths, resume/database file types,
and the user's own name/email/phone listed in `user-data/.private-terms`);
agent rules in `AGENTS.md`.

*Alternatives:* data in `~/.jobtracker` (safer from git, but users lose the
"everything in one folder" model and the agent needs out-of-project
permissions; kept as an option through `JOBTRACKER_HOME`). Per-type gitignore
patterns scattered through the tree (fragile; one missed pattern leaks).

### D2. SQLite is the source of truth; files only for documents

Structured data lives in one SQLite database (`user-data/jobtracker.db`, WAL
mode). Disk holds only what a human opens (resumes, cover letters, posting
snapshots) and raw captures; each file is registered in the database.

This deviates from the design's wording ("files read 09:12 / reload from
files"). The header indicator becomes "data updated <time>" with a light poll
of a change counter so the panel refreshes after the agent writes.

*Why:* the learning loop needs queries over history (conversion by score band,
title, channel, resume type, salary delta); the panel and the agent write
concurrently; type-ahead filter/sort over all tracked jobs is trivial with SQL
and with a few hundred rows in memory.
*Alternatives:* JSON/Markdown files as truth (agent-friendly and diffable, but
no integrity, race conditions with the panel, analytics become ad-hoc
parsing). SQLite + ORM (SQLAlchemy/SQLModel): more dependencies for little
gain at this size; we use stdlib `sqlite3`, pydantic models, and numbered SQL
migrations tracked with `PRAGMA user_version`. A backup copy is taken before
every migration.

### D3. One package, three layers; the CLI is the agent's only write path

```
src/jobtracker/
  core/   paths, db, migrations, models, services (all business rules)
  cli/    `jobtracker <noun> <verb>`; JSON output; used by skills
  web/    FastAPI app: /api/* + static frontend
```

Skills never write SQL or edit data files; they call the CLI (for example
`jobtracker postings import results.json`, `jobtracker score set J0007 …`).
The panel calls the HTTP API. Both go through the same services, so
validation (for example the salary-evidence rule) is enforced in one place.

*Alternatives:* agent calls the panel's HTTP API (fails when the panel is not
running); agent edits the DB directly (no validation, schema drift); an MCP
server (nice later, but adds a setup step and ties the tool to MCP clients; a
CLI works from any agent and from tests).

### D4. FastAPI + uvicorn, bound to 127.0.0.1

FastAPI over Flask for typed request/response models shared with the CLI and
free API docs for contributors. Server binds to loopback only, no auth. File
uploads and downloads are confined to the private home (path traversal
checks). Environment: `uv` when present, otherwise `python -m venv` + pip;
`/setup` handles both.

### D5. No-build frontend

Static ES modules served by FastAPI, with vendored Preact + htm (single small
file, no CDN, works offline), self-hosted fonts (Inter, Space Grotesk,
JetBrains Mono; OFL), and design tokens taken from `design/`. No Node, no
bundler. Filtering, sorting, and type-ahead are client-side.

*Alternatives:* React/Vite build (requires Node or committing build
artifacts); server-rendered templates + HTMX (awkward for expandable rows with
inline editing and instant filtering); vanilla JS without a view library
(doable, but state handling for the two tables becomes hand-rolled).

### D6. i18n

Panel strings in `locales/en.json` and `locales/es.json`; language chosen at
`/setup`, switchable in the header, stored in `config.toml`. Agent-generated
panel text (score notes, lesson text) is written in the panel language at the
time of writing. Resumes, cover letters, and form answers follow the language
of the job posting, independent of the panel language. Repo content and
canonical skill names are English (`/job-search`). Spanish command names are
provided as aliases (see D13), and the panel shows commands in the panel
language.

### D7. Data model (summary)

- `seasons`, `profile_versions` (job needs + target titles with state:
  included, excluded, suggested, under review).
- `search_runs`, `postings` (de-duplicated by provider + external id, then by
  normalized company + title + location), `run_results` (posting × run:
  shown, filtered-out with reason, duplicate).
- `scores` (total, per-component breakdown, weights version, resume used;
  history kept so "score at time of applying" is preserved).
- `salary_suggestions` + `salary_evidence` (source, URL, comparables, sample
  size, date).
- `applications` (tracked postings: status, applied date, asked salary,
  channel, contact, notes, next step), `tags`, `documents`, `form_questions`,
  `form_answers` (origin: agent, edited by user).
- `dismissals` (reason chosen by the user; feeds learning).
- `events`: append-only timeline of everything that happens to a posting or
  application. This is the substrate of the learning loop.
- `application_snapshots`: the facts known at the moment of applying (score
  and components, target title, channel, work mode, contract, resume kind,
  cover letter, posting age, asked-vs-suggested salary). Captured from day one
  so later predictive analysis has clean training data.
- `rules`, `providers_state`, `settings`.

### D8. Status = one extensible status mapped to a fixed stage, plus free tags

Each application has exactly one status from a user-extensible list. Every
status belongs to one fixed stage: `to_apply`, `applied`, `interview`,
`offer`, `closed_positive`, `closed_negative`. Built-ins: New, Applied,
Interview, Offer, Accepted, Rejected, Ghosted, Offer declined, No economic
alignment, Withdrawn. Creating a status inline asks only for its name and
stage (default: the stage of the current status). Free-form tags ("Referral",
"Technical 2 of 3") are separate and unlimited.

This gives the tag-like inline UX requested while keeping "hide negative
terminal statuses by default", the funnel, and analytics correct for custom
statuses.
*Alternative:* statuses as plain tags (cannot tell which custom tags are
terminal or negative; analytics break).

### D9. Scoring: agent judgement inside a fixed, versioned rubric

Components and maximum points (initial weights): target title 25, skills 35,
seniority 15, conditions 15, history 10. The agent supplies points and a short
note per component; the CLI validates against the active weights version and
stores the breakdown. The history component is computed from the user's own
outcomes, not judged. A score is recomputed (new row, old one kept) when the
resume used changes: tailored resume produced, user uploads the resume
actually sent, or the base resume is updated. Uploads from the panel enqueue a
"rescore" item in the agent's pending queue.

### D10. Salary suggestions are evidence-gated

A suggestion can only be stored with at least two evidence rows that the agent
marks comparable (same country and level, matching work mode, similar
industry/company size), each with a source URL. The service rejects anything
less, and the panel shows "no reliable data". Suggested amount is the median
of evidence, with the observed range and a confidence level derived from the
number and closeness of sources. No extrapolation across countries or levels.

### D11. Rules: one mechanism for preferences, lessons, and system rules

A `rules` table with `origin` (system, user, learned), `status` (proposed,
active, ignored, reverted), `area` (search, score, resume, salary, statuses…),
text, evidence, and an optional structured `effect` for rules the code
enforces (minimum score shown, days until ghost, salary cap over median, title
weight adjustment). System rules ship with the repo; user rules are created by
the agent when the user states a preference ("don't change my resume layout");
learned rules are proposed by `/analyze-results` and become active only when
the user clicks Apply in the panel (or tells the agent).

Every skill starts with `jobtracker context`, which returns the active profile,
active rules, pending queue, and provider state. This, not Claude Code's
private memory, is the project memory: it is portable, visible in the panel,
and auditable.

### D12. Learning loop: descriptive, then predictive, then prescriptive

The loop matures with the amount of resolved outcomes, and the panel always
shows which level is active and why:

| Level | Unlocks when | What the user gets |
|---|---|---|
| 0 Collecting | from the first application | counts and the funnel only |
| 1 Descriptive | 15+ resolved applications | rates by score band, title, channel, resume type, salary delta, with uncertainty ranges; lesson proposals |
| 2 Predictive | 40+ resolved, 8+ interviews, and the model beats the base rate in back-testing | an estimated interview probability (with a range) on every posting |
| 3 Prescriptive | level 2 holds on two consecutive analyses | ranked "apply next" list, recommended salary ask, resume emphasis, follow-up timing, suggested experiments |

All numbers come from code (`jobtracker insights`), never from the agent's
intuition: smoothed rates at level 1; a small regularized logistic model in
pure Python at level 2, validated walk-forward (train on earlier applications,
predict later ones) and automatically switched off when it stops beating the
base rate. The agent interprets the numbers in `/analyze-results` and turns
them into proposed rules and recommendations with the evidence attached.

Guardrails: one person's data is small and observational, so every statement
carries its sample size, a segment needs 5+ cases, recommendations state that
they are correlations, and the system proposes simple experiments (for example
alternating cover letter / no cover letter on similar postings) when it needs
causal evidence. Every applied rule is reversible; weight changes create a new
weights version so past scores stay comparable. Details in the
`add-learning-loop` change.

*Alternatives:* scikit-learn (heavy dependency for a model this small);
letting the agent "predict" from reading the table (not reproducible, not
auditable).

### D13. Skills (user-facing), stored in `.claude/skills/`

| Skill | Purpose |
|---|---|
| `/setup` | Dependency check, panel language, resume intake, questionnaire, target-title research and confirmation, provider selection, workspace creation |
| `/job-search [days=7]` | Search enabled providers, de-duplicate, first-pass filter with reasons, score, salary research, update panel |
| `/prepare-documents [pending \| ids=…]` | Tailored resumes, cover letters where needed, form answers; the batch command |
| `/form-answers ids=…` | Form answers only |
| `/analyze-results` | Insights and proposed lessons |
| `/new-season` | New profile, archive previous campaign; optional full reset |
| `/panel` | Start/stop the local panel |

Skills are thin procedures over the CLI and the provider files. `AGENTS.md`
makes the same instructions usable by other agents.

**Spanish aliases.** Claude Code has no alias mechanism for skills, so aliases
are thin wrapper skills that delegate to the canonical one: `/configurar`,
`/buscar-empleos`, `/preparar-documentos`, `/formulario`,
`/analizar-resultados`, `/nueva-temporada` (`/panel` is the same word). Their
templates live in `i18n/skill-aliases/es/`; `/setup` installs them into
`.claude/skills/` (gitignored there) only when the user chooses Spanish, so
English users do not get a duplicated command list. Aliases accept Spanish
arguments (`dias=7`, `pendientes`). Regardless of aliases, the README documents
every command and `/setup` ends with a guided tour.

*Alternative:* commit the Spanish wrappers for everyone (simpler, but doubles
the skill list for English users).

### D14. Providers

`providers/<id>.md` with front matter (kind: jobs/salary/both, regions, access
method, login and live-walk flags, dependencies, pacing, last verified) and a
fixed set of sections (see `providers/_template.md`). Enabled/disabled state
and last result are per user, in the database. Providers flagged `live_walk`
are skipped in unattended runs and reported in the run summary. The agent uses
the user's own browser session where a login is needed, read-only and paced.

### D15. Seasons and reset

Default `/new-season`: new season row and profile; previous applications stay
in the same database, hidden from default views; lessons are kept unless the
user asks to reset them. Full reset: move the entire home to
`user-data/archive/<date>-<label>/` and initialize a fresh one. Nothing is
deleted by the tool.

### D16. Resume tailoring format

The base resume is kept exactly as provided. If it is a DOCX, tailored versions
are produced by editing text in place (layout untouched) and exported to PDF
when a converter is available. If only a PDF exists, the agent asks for the
editable source; rebuilding the resume from extracted text counts as a heavy
layout change and requires explicit consent (stored as a user rule).

### D17. Development practice

OpenSpec for spec-driven development; `openspec/` is committed, generated
OpenSpec skills are not. Tests use a temporary `JOBTRACKER_HOME` and a
fictional persona in `tests/fixtures/`. A `jobtracker demo seed` command loads
fictional data so the panel can be developed without real data.

### Roadmap (follow-up changes, in order)

1. `add-setup-onboarding`: `/setup`, profile intake, title research.
2. `add-panel-search-tab`: panel shell, i18n, Search board.
3. `add-job-search`: `/job-search`, first providers, scoring, salary evidence.
4. `add-application-tracking`: Applications board, statuses, uploads.
5. `add-document-preparation`: resumes, cover letters, form answers, batch.
6. `add-learning-loop`: insights, rules, Learning board.
7. `add-seasons`: `/new-season`, archive, reset; Profile & agent board.

## Risks / Trade-offs

- [Job sites block automation or change markup] → provider files carry
  `last_verified`, a live-walk fallback, and explicit "what does not work";
  a failing provider is skipped and reported, never silently guessed.
- [Site terms of use] → read-only, paced, user's own session, no auto-apply,
  small volumes; documented per provider.
- [Agent bypasses the CLI and edits data] → `AGENTS.md` rule, skills only show
  CLI calls, DB is binary (harder to hand-edit than JSON).
- [Privacy guard false sense of security] → guard is a backstop; the primary
  protection is physical separation (D1). CI runs the guard on every push.
- [SQLite binary is not human-diffable] → `jobtracker export` (JSON/CSV) and
  automatic backups.
- [LLM scoring drift between runs] → fixed rubric, stored breakdowns, weights
  versioning, and the insights panel that checks whether score predicts
  outcomes.
- [Python 3.14-only syntax creeping in] → target 3.11, CI matrix 3.11–3.14.

## Migration Plan

Greenfield; nothing to migrate. Database schema changes are forward-only
numbered migrations with a backup before each run.

## Resolved Questions

1. Panel brand: "Job Radar" (en) / "Radar de Empleo" (es); package and CLI
   name `jobtracker`.
2. `design/` is committed as the UX reference, as `design/panel-ux.html`.
3. First providers: LinkedIn, Indeed, Bumeran, Computrabajo for jobs;
   Glassdoor and Indeed for salary evidence.
4. Default data location is `user-data/` inside the clone;
   `JOBTRACKER_HOME` moves it elsewhere.
