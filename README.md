# Claude Job Tracker

A clone-and-run, local-first job search assistant driven by an AI agent
(built for [Claude Code](https://claude.com/claude-code)).

- The **agent** sets everything up from a questionnaire and your resume,
  searches job sites, scores each posting against your profile, researches
  salary evidence, and drafts tailored resumes, cover letters, and form answers.
- A **local web panel** (English or Spanish) shows the latest search, tracks
  every application and its status, and lets you record what really happened.
- A **learning loop** uses your real outcomes to tune future searches, scores,
  and advice.

Your data never leaves your machine's project folder: everything personal is
stored in a gitignored `user-data/` directory.

> **Status: foundation only.** The private workspace, database, command-line
> interface, and privacy guard work. The agent skills and the panel boards are
> specified in [`openspec/changes/`](openspec/changes/) and are being built in
> order.

## Requirements

- Python 3.11+
- Claude Code (other agents can follow `AGENTS.md`, with less tooling)

## Contributing

See [`AGENTS.md`](AGENTS.md). After cloning, enable the privacy guard:

```
git config core.hooksPath .githooks
uv sync --extra dev          # or: pip install -e ".[dev]" inside a virtual environment
uv run pytest
```

Check your environment at any time, even before installing anything:

```
python scripts/jt.py doctor
```

## License

GPL-3.0. See [`LICENSE`](LICENSE).
