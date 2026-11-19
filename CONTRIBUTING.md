# Contributing

Thank you for helping. This project is a local-first job search assistant run
by an AI agent; most of it is Python (`src/jobtracker/`), Markdown skills the
agent follows (`.claude/skills/`), and one file per job site (`providers/`).

- **Adding a job site?** Run `/add-provider` in Claude Code and read
  [`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md): it builds the site
  privately, proves it, and opens the pull request for you.
- **Anything else?** Read on.

## Set up

```
git clone <this repository>
cd agentic-job-search-and-track
git config core.hooksPath .githooks          # the privacy guard runs before every commit
uv sync --extra dev                          # or: pip install -e ".[dev]" in a virtual environment
uv run playwright install chromium           # browser for the panel tests
```

Without Chromium, `tests/test_browser*.py` (the panel tests) are skipped, and
the summary only shows them as skipped: install it so they run, as CI does.

The job-site readers that use a browser (Bumeran, Indeed, Glassdoor) run on
Scrapling at use time; their tests use fake browsers and need nothing extra.
To try a reader for real, `python scripts/jt.py providers install <id>`
installs what it needs into the environment and checks that its browser
starts (reinstalling the browser when it does not).

On Windows, `jt` keeps those browsers in `%USERPROFILE%\.cache\ms-playwright`
(it sets `PLAYWRIGHT_BROWSERS_PATH` unless you set it yourself). Playwright's
default, `%LOCALAPPDATA%\ms-playwright`, is redirected when the agent runs
inside a packaged app such as the Claude desktop app, and the full Chromium
that Scrapling starts then fails with `spawn UNKNOWN`. Install reader
browsers through `jt providers install`, not with `playwright install`
directly, so they land in that folder.

## The rules that never bend

These are in [`AGENTS.md`](AGENTS.md); in short:

1. **Privacy.** No real personal data anywhere in the repository: code, tests,
   skills, providers, specs, docs, commit messages, or pull requests. Use the
   fictional persona in `tests/fixtures/`. Personal data lives in `user-data/`
   (gitignored); the pre-commit guard and CI refuse commits that break this.
   Never bypass the guard.
2. **One write path.** Structured data changes only through the `jobtracker`
   CLI or the panel API.
3. **No invented facts** in salaries, resumes, or form answers.
4. **The agent never applies, submits, or sends anything** on the user's
   behalf, and never puts a user's account at risk.
5. **`core` stays standard-library only**, so `jt doctor` runs on a bare
   Python. Optional tools (Scrapling, Playwright) are imported only where
   they are used.

## How a change is made

Development is spec-driven with [OpenSpec](https://github.com/Fission-AI/OpenSpec)
(`npm install -g @fission-ai/openspec`; optionally `openspec init --tools
claude` for its Claude Code commands, which are gitignored).

1. **Propose** under `openspec/changes/<name>/`: `proposal.md` (why and what),
   `design.md` (decisions), `specs/<capability>/spec.md` (requirements with
   scenarios, as deltas), `tasks.md`. Validate with
   `openspec validate <name> --strict`.
2. **Get it approved** by a maintainer before implementing (open an issue or a
   draft pull request with the proposal).
3. **Implement** only that change's tasks, with tests.
4. **Verify** that the code matches the change, **archive** it
   (`openspec archive <name>`), and open the pull request.

A job site gets its own change, after a study of the site with real requests
(see [`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md)).

## Before you open a pull request

```
uv run ruff check .
uv run pytest
python scripts/check_private.py --all
openspec validate <change> --strict
```

Tests run against a temporary `JOBTRACKER_HOME`; never point them at real
data. CI runs ruff, the tests on Ubuntu and Windows (Python 3.11 and 3.14),
and the privacy guard on every pull request.

The pull request template has a checklist; for a new job site it also asks
for the study and the proving runs.

## Style

- Repository content (code, docs, skills, specs, commit messages) is written in
  English. Text the user sees in the panel is localized (`src/jobtracker/web/
  static/locales/en.json` and `es.json`); Spanish command names live in
  `i18n/skill-aliases/es/`.
- The CLI prints JSON: `{"ok": true, …}` or `{"ok": false, "error": …}`.
- Plain, concrete writing in docs and skills: say what happens, not how good
  it is.
