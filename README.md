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

> **Status: early scaffolding.** The architecture is under review in
> [`openspec/changes/define-foundation-architecture/`](openspec/changes/define-foundation-architecture/design.md).
> Nothing is runnable yet.

## Requirements

- Python 3.11+
- Claude Code (other agents can follow `AGENTS.md`, with less tooling)

## Contributing

See [`AGENTS.md`](AGENTS.md). After cloning, enable the privacy guard:

```
git config core.hooksPath .githooks
```

## License

GPL-3.0. See [`LICENSE`](LICENSE).
