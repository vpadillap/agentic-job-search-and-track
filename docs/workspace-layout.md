# Workspace layout: where everything is stored and how it is named

This is the storage contract. Every skill, the CLI, and the panel follow it.
The agent running `/setup` MUST create exactly this structure and nothing else.

## The one rule

**Everything personal lives under the private home directory, and nothing
personal lives anywhere else.**

- Private home: `user-data/` at the repo root (override with the
  `JOBTRACKER_HOME` environment variable, e.g. to keep data outside the clone).
- `user-data/` is gitignored, and `scripts/check_private.py` (pre-commit hook +
  CI) rejects commits that contain it, resume/database files, or the user's
  private terms.
- Never write personal data (name, email, phone, resume text, employers,
  salaries, job history, application notes) into: source files, skills,
  provider files, `openspec/`, `docs/`, tests, commit messages, or PR text.
- Tests and examples use the fictional persona in `tests/fixtures/` only.

## Layout

```
user-data/                                  private home (gitignored)
├── config.toml                             panel language (en|es), host, port
├── jobtracker.db                           SQLite: the source of truth for all structured data
├── .private-terms                          one term per line (name, email, phone…) for the privacy guard
├── profile/
│   ├── resume-base.<ext>                   the user's resume exactly as provided (pdf/docx)
│   ├── resume-base.md                      extracted text of the base resume
│   └── resume-base-v<N>.<ext>              earlier base resumes, kept when the user updates it
├── applications/
│   └── <job-id>-<company-slug>/            one folder per tracked job, e.g. J0007-altamar-retail
│       ├── posting.md                      job description verbatim, as captured
│       ├── resume-proposed-v<N>.<ext>      resume tailored by the agent (never overwritten; bump N)
│       ├── resume-sent.<ext>               the resume the user actually sent (panel upload or agent copy)
│       └── cover-letter-v<N>.md            proposed cover letter
├── searches/
│   └── <YYYYMMDD-HHMM>/                    raw provider captures for one search run (debug/audit)
├── exports/                                anything the user asks to export
├── backups/                                automatic DB copies before migrations and resets
└── archive/
    └── <YYYYMMDD>-<label>/                 a previous home moved aside by a full reset
```

## Naming rules

| Thing | Rule | Example |
|---|---|---|
| Job id | `J` + 4-digit sequence, assigned by the CLI, never reused | `J0007` |
| Slug | lowercase ASCII, hyphens, max 40 chars, from company name | `altamar-retail` |
| Versioned file | `-v<N>` suffix starting at 1; never overwrite, never renumber | `resume-proposed-v2.docx` |
| Search run folder | local time `YYYYMMDD-HHMM` | `20261115-0912` |
| Dates in the DB | ISO 8601 UTC (`2026-11-15T14:12:00Z`); the panel localizes | |
| Money | integer amount + ISO 4217 currency + period (`month`) + `gross`/`net` | `15000 PEN month gross` |

## What goes in the database vs on disk

- **Database** (`jobtracker.db`): seasons, profile versions (job needs, target
  titles), search runs, postings, scores and their breakdowns, salary
  suggestions with evidence, tracked applications, statuses and tags, form
  questions and answers, the event timeline, rules (preferences and lessons),
  provider state, and the path of every document below.
- **Disk**: only documents a human opens (resumes, cover letters, posting
  snapshots) and raw captures. Every such file is registered in the database.

Structured data is written **only** through the `jobtracker` CLI or the panel
API. Agents do not edit the database or `config.toml` by hand.

## Things that are deliberately *not* in the repo folder

- Claude Code's own memory and transcripts live in `~/.claude/` and are outside
  the repo. Durable user preferences for this tool are stored as **rules** in
  the database (so the panel can show them), not in Claude Code memory.
- Browser sessions/cookies stay in the user's browser profile. The tool never
  stores credentials.
