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

### J2. De-duplication

Key 1: provider + external id. Key 2: normalized company + normalized title +
location, to catch the same job on two sites; the earliest sighting is kept as
primary and other sources are attached as alternate links. Reposts of a posting
the user dismissed stay hidden; reposts of a tracked posting add a timeline
event.

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

### J6. Provider access: logged-out by default, studied one provider at a time

Principle: providers are read as an anonymous visitor, in a browser that does
not carry the user's accounts or cookies. The agent never uses the user's
logged-in session on a job site. Automated use of a logged-in account is
against the terms of sites such as LinkedIn and can get the account
restricted, and this tool is cloned by other people whose accounts would carry
the same risk.

How each site is read is not decided here. Each provider file is the result of
its own study against the live site, done when that file is written: which
public pages exist, what an anonymous visitor can see, how the site reacts to
automation, and therefore which tool fits (plain page fetch, Playwright, a
live walk with the user watching, or a mix). Sites behave inconsistently (a
sign-in pop-up may or may not appear over LinkedIn's public job search, for
example), so a recipe must describe what to do in each case and when to give
up and report the provider as skipped.

Starting points only, to be confirmed by each study:

| Provider | Kind | Starting point |
|---|---|---|
| LinkedIn | jobs | public job search at `https://www.linkedin.com/jobs/search`, logged out |
| Indeed | jobs, salary | public search and salary pages |
| Bumeran | jobs | public search |
| Computrabajo | jobs | public search |
| Glassdoor | salary | public salary pages; likely limited without an account |

If a study finds that a site shows nothing useful without an account, the
provider is documented as limited or left out. It is not switched to the
user's session.

Each recipe carries `last_verified`. Provider state per user: enabled, last
run status, last error.

*Alternative rejected:* reading through the user's logged-in browser session
(more complete results, but puts the user's account at risk).

### J7. Form questions

When a provider shows application questions without submitting anything, the
agent stores them with the posting (text, type, options, required). They are
answered later by `add-document-preparation`.

## Risks / Trade-offs

- [Anti-bot measures] → anonymous access only, pacing from front matter, small
  result caps, live-walk fallback; never circumvent blocks or sign-in walls.
- [Terms of use] → logged-out, read-only, low-volume personal use; each
  provider file states what its study found about the site's terms; a provider
  can be disabled with one toggle.
- [Less data without an account (fewer results, no form questions)] →
  accepted; the run report says what could not be seen.
- [Stale or wrong salary reports] → evidence older than 18 months is not
  comparable; every number links to its source.
- [Scoring cost on large result sets] → filter and de-duplicate first; research
  budget per run.
