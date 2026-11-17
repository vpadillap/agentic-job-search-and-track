## Why

Learning must work from the results of each application: how far it got and
what was offered. Three gaps remain (decided by the owner on 2026-11-17, see
`docs/backlog.md`):

- The salary the company offered is not recorded anywhere.
- The learning history given to the agent names statuses by built-in key or
  English name, so the agent cannot read the path of a custom status, or read
  it in the user's language.
- A separate "application snapshot" copies facts at application time. The
  history plus the current data are enough, and the copy is sometimes wrong:
  the sent resume is often uploaded after marking Applied, so the snapshot
  records "base" or "tailored" for an application that went out with the sent
  resume.

## What Changes

- **Offered salary.** Every application gets an offered salary (amount,
  currency, gross or net, monthly, like the asked salary). The user enters
  it in the application's details. The table shows it next to the asked and
  suggested salaries, it is recorded in the history, and the agent gets it.
- **Learning uses it.** Recording an offered salary counts the application
  as having reached an offer, even with a custom status. Insights report how
  many offers have a recorded amount and the median difference between
  offered and asked, and between offered and suggested, with their cases. The
  agent's history carries the offered salary of each application.
- **Statuses by name in learning.** The learning history gives each
  application's current status by its full name in the panel language (plus
  the key for built-ins, and whether it ended) and its whole status path by
  full names with dates.
- **BREAKING (internal): no application snapshot.** The
  `application_snapshots` table is removed (migration 0013). The moment an
  application first gets an applied date becomes an `applied` event in its
  history; existing snapshots become those events, with their dates. The
  facts at application time are derived:
  - the score and the salary suggestion: the version that was current at
    that moment (both keep every version), or the first one when the posting
    was scored only later;
  - applied date, asked and offered salary, channel, sent resume or tailored
    resume, cover letter, and work mode: the current data;
  - title, site, contract type, and posting age: the posting plus the applied
    date.
- Everything that read the snapshot reads these derived facts: insights,
  prediction, the agent's history, `jt score show --history`
  (`at_application`), the Applications board's suggested salary, and both
  demos.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `application-tracking`: application details include the offered salary;
  the history records when the application first got an applied date, and
  the facts at application time are derived from the history and the stored
  versions instead of a copy.
- `applications-board`: the table shows the offered salary next to the asked
  and suggested salaries.
- `outcome-insights`: an offered salary counts as an offer; insights compare
  offered with asked and suggested salaries; the agent's history names
  statuses and status paths in full and carries the offered salary.

## Impact

- Database: migration `0013_learn_from_results.sql` (offered salary columns,
  `applied` events from snapshots, drop `application_snapshots`).
- Code: `core/applications.py`, `core/insights.py`, `core/predict.py`,
  `core/refresh.py`, `core/scoring.py`, `core/tracking.py`, `core/demo.py`,
  `core/demo_learning.py`, `cli/main.py`, `web/static/boards/applications.js`,
  `web/static/boards/learning.js`, locales.
- Skills: `analyze-results` (history fields, analysis guide).
- Tests: tracking, learning, browser.
- Not touched: `add-seasons` (in progress by another contributor).
