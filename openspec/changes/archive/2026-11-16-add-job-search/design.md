## Context

Implements D9, D10, D14 of `define-foundation-architecture`. The agent does the
browsing and the judgement; the CLI does de-duplication, validation, and
storage so results are consistent between runs.

## Goals / Non-Goals

**Goals:** trustworthy results (every exclusion and every number explained),
resilience to one provider failing, low load on job sites.

**Non-Goals:** exhaustive crawling; background scheduling; auto-apply.

## Decisions

### J1. Run pipeline

1. `jobtracker context` → profile, rules, enabled providers.
2. `jobtracker run start --days N` → run id and raw-capture folder.
3. Per enabled provider: read `providers/<id>.md`, search each included title,
   save captures, build normalized posting records. Providers flagged
   `live_walk` are skipped unless the user confirmed they are present; failures
   are recorded and the run continues.
4. `jobtracker postings import` → de-duplication and "already seen/dismissed/
   tracked" detection happen here, not in the agent.
5. First-pass filter (J3) on new postings only.
6. Score survivors (J4), then salary research (J5) for postings above the
   display threshold, best score first, within a per-run research budget.
7. `jobtracker run finish` → summary for the panel and for the agent's reply.

*Alternative:* the agent scores everything before de-duplication (wastes most
of the effort on repeats).

### J2. De-duplication: identity only, possible duplicates are a visible hint

A posting is the same posting only when it has the same provider + external id
or the same (normalized) URL. Nothing else merges postings: the same job on two
sites is stored as two postings, each with its own row in the panel, so the
user chooses which site to apply through. Found again in a later run, a posting
counts as already seen; reposts of a posting the user dismissed stay hidden;
reposts of a tracked posting add a timeline event.

Possible duplicates are shown, never resolved automatically: a posting with
the same normalized company and title, a publication date within 7 days of the
other's (or an unknown date), that is part of the same search run or already
tracked, gets a "possible duplicate" mark naming the other postings. The user
and the agent decide what to do with them.
*Alternative (rejected by the project owner):* merging by company + title +
location with alternate links (hides the site choice from the user).

### J3. First-pass filter: hard constraints only, always with a reason

A posting is filtered out only when it clearly violates a hard constraint from
the profile or an active rule: excluded title, wrong work mode or contract
type, location outside accepted zones for onsite/hybrid, required language the
user lacks, excluded company, or published salary below the stated minimum.
Ambiguous cases pass and get a flag (for example "seniority below yours").
Every filtered posting keeps its reason and is visible in the panel.
*Alternative:* silent score threshold (the user cannot audit what was dropped).

### J4. Scoring

Rubric from D9 (title 25, skills 35, seniority 15, conditions 15, history 10).
The agent submits points and a note per component, including matched and
missing skills; the CLI rejects totals that do not match the active weights
version. The history component is supplied by the system: neutral (half
points) until the learning loop provides a value. Notes are written in the
panel language. Scores are stored as history rows tied to the resume they were
judged against.

### J5. Salary research

For each posting the agent looks for: salary published in the posting itself,
reports for the same company and role, and reports for the same role in
comparable companies. Each piece of evidence is stored with source, URL,
amount or range, currency, period, gross/net, sample size, date, and the
comparability attributes (country, level, work mode, industry, company size).
The service accepts a suggestion only with two or more comparable evidence
rows (a salary published in the posting counts as one), converts nothing
across currencies, normalizes to monthly, and computes median, range, and
confidence. Otherwise it stores "no reliable data" with what was tried, so the
agent does not repeat fruitless research. Evidence is cached per company +
role + location and reused for 60 days.

### J6. Provider access is out of scope

This change delivers the provider mechanism only: reading provider files,
validating them, and keeping per-user provider state. It does not decide how
any site is accessed and does not add any provider file.

Each provider is added by its own change, after an individual study of that
site, and that change decides the approach for that provider.

Note recorded from the project owner for the future LinkedIn change: do not
use the logged-in session; open a browser without a session, preferably after
a full investigation of how the site behaves (a pop-up sometimes appears,
sometimes not, so Playwright or a live walk through MCP may be needed).
LinkedIn normally lets logged-out visitors use
`https://www.linkedin.com/jobs/search`.

### J7. Form questions

When a provider shows application questions without submitting anything, the
agent stores them with the posting (text, type, options, required). They are
answered later by `add-document-preparation`.

## Risks / Trade-offs

- [Anti-bot measures and terms of use] → handled per provider, in each
  provider's own change; a provider can be disabled with one toggle.
- [Stale or wrong salary reports] → evidence older than 18 months is not
  comparable; every number links to its source.
- [Scoring cost on large result sets] → filter and de-duplicate first; research
  budget per run.
