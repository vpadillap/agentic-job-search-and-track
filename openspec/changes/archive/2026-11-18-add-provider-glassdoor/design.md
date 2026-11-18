## Context

See the proposal's study log. The owner chose Scrapling (point 1.7):
Scrapling's `StealthySession` (headless, `solve_cloudflare=True`) loads
searches, the site's "Show more jobs", posting pages, and salary pages in one
session, where Playwright gets Cloudflare's challenge. Observed structure:

- **Search page** (`/Job/<place>-<title>-jobs-SRCH_IL.0,<n>_IN<locId>_KO<a>,<b>.htm?fromAge=<d>`):
  cards `li[data-test="jobListing"][data-jobid=<id>]`, each with a title link
  `a.JobCard_jobTitle…[href="https://www.glassdoor.com/job-listing/…?jl=<id>"]`;
  the page's flight data holds `jobListings[].jobview` for the first 30.
- **"Show more jobs"** (`button[data-test="load-more"]`): each click adds up to
  30 cards; its response (`/job-search-next/bff/jobSearchResultsQuery`) is JSON
  `data.jobListings` with `jobListings[].jobview.header` (`ageInDays`,
  `employerNameFromSearch`, `jobTitleText`, `locationName`, `seoJobLink`,
  `payCurrency`, `indeedJobAttribute.extractedJobAttributes`, `expired`),
  `jobview.job.listingId`, and `totalJobsCount`. In the study the button
  disappeared at 127 cards of 152.
- **Posting page** (`seoJobLink`): JSON-LD `JobPosting` with `title`,
  `datePosted`, `validThrough`, `hiringOrganization.name`,
  `jobLocation.address` (locality, country), `description` (HTML; same text as
  the visible description), `salaryCurrency`, sometimes `baseSalary`,
  `employmentType`, `industry`.
- **Salary page** (`/Salaries/<place>-<title>-salary-SRCH_IL.0,<n>_IN<locId>_KO<a>,<b>.htm`):
  JSON-LD `Occupation.estimatedSalary[]` (`MonetaryAmountDistribution`:
  `currency`, `duration`, `percentile10/25`, `median`, `percentile75/90`);
  page text "N salaries" and "submitted on <date>".
- **Sign-up modal**: `dialog[open]`; Escape closes it.

## Goals / Non-Goals

**Goals:** as many Glassdoor postings per title as the site lists, with
complete descriptions, and Glassdoor salary reports as evidence, logged out,
headless, with the same drafts/readings flow and stop rules as the other
readers.

**Non-Goals:** signing in; the user's browser or account (the project's rule
against working around site checks protects the user's accounts; reading
logged out, working around Cloudflare's check is allowed, owner's
clarification 2026-11-18); the site's internal endpoints called directly
(only the page's own button triggers them); page 2 URLs (they repeat page 1);
individual salaries that need a sign-in; company reviews; applying.

## Decisions

### D1. Scrapling, one stealth session per reader call

`readers/glassdoor.py` with an injectable fetcher adapter:
`search(url, max_cards) -> SearchResult` (page HTML, show-more JSON bodies,
status, title), `page(url) -> (status, title, html)`, `close()`. The real
adapter wraps `scrapling.fetchers.StealthySession(headless=True,
solve_cloudflare=True, locale=<country locale>)`, imported only when it runs,
created per call (one title, or one salary page) and closed at the end: no
cookies survive between calls. No window opens. Parsing (cards, show-more
JSON, JSON-LD) is pure functions tested with fictional pages. Shared run
state, pacing, lock, seen postings, and stop recording come from
`readers/common.py`.

`providers/glassdoor.md`: `access: scrapling`, `dependencies: [scrapling]`.
`INSTALL_HINTS["scrapling"]` becomes `pip install "scrapling[fetchers]", then:
scrapling install` (the browser download, about 120 MB). `/setup` installs it
only when the user turns Glassdoor on.

### D2. The modal is closed, never answered

Inside the search page action, when `dialog[open]` appears the reader presses
Escape; if a dialog stays open it clicks only
`data-test="auth-modal-close-button"`. It never clicks a sign-in option. A
dialog that stays open is a sign-in wall (blocked).

### D3. Search URL and country id

The SEO search URL above, with slugs in lowercase and hyphens and `fromAge`
the smallest of 1, 3, 7, 14, 30 covering the run's window. The country's
Glassdoor id and place slug come from, in order:

1. the provider file's `## Countries` table (`| Country | Glassdoor id |
   Place | Last verified |`, e.g. `| PE | 189 | peru | 2026-11-18 |`);
2. the user's saved setting `<home>/provider-settings/glassdoor.json`
   (`{"countries": {"CL": {"id": …, "place": …, "from_url": …}}}`);
3. `--search-url <url>`: a Glassdoor search URL the user pasted; the reader
   takes `IN<digits>` and the place slug (the first `n` characters of the path
   segment, from `IL.0,<n>`), uses them, and saves them to (2), so the user
   pastes it once. Anything that is not a Glassdoor `/Job/…SRCH_IL…_IN…` URL
   is refused.

A country with none of these is a `missing_country` error that tells the
agent to ask the user for one Glassdoor search URL.

### D4. Listing, up to the provider's cap

The page action clicks "Show more jobs" (5 s apart, Escape for the modal)
until the button disappears, no new cards arrive, or the cards reach
`max_results_per_query` (150 in the provider file). Cards are read in page
order: ids and links from the title links, and `ageInDays`, company, title,
location, attributes, and salary currency from the show-more JSON (and the
page's flight data for the first 30, when present). A card older than the
run's window, already handled in the run, or stored by an earlier run (seen)
is not opened. The run report states the site's total and how many were
listed, so a title cut by the cap or by the site's end is visible.

### D5. One posting page per new posting

Each new posting's `seoJobLink` is loaded in the same session, 5 s apart. The
draft comes from its JSON-LD `JobPosting`: `external_id` = listing id;
`url` = `seoJobLink` without tracking parameters; `title`; `company` =
`hiringOrganization.name`; `location` = address locality (and region when
present); `country` = the profile's country; `posted_at` = `datePosted`'s
date; `description` = the HTML description as plain text (block elements
become line breaks, spaces collapsed, at most one blank line); hints
`site_attributes` (extracted attributes such as "Tiempo completo",
"Modelo Híbrido"), `site_employment_type`, and `site_salary` (from
`baseSalary` when present, as shown). Work mode, contract type, language,
flags, and a stated salary are the agent's reading, as for Indeed.

A posting page without `JobPosting`, or with a description under 100
characters, is skipped with a note (`unreadable` in the summary, the page
kept in the captures); three in a row stop the provider with `error`.

### D6. Salary reader

`jt providers salary glassdoor --title "<title>" [--search-url <url>]` (the
profile's country, D3). One session loads the salary page and returns one
evidence draft, never stored by itself:

| Evidence field | From |
|---|---|
| `source` | "Glassdoor" |
| `url` | the salary page |
| `amount_min`, `amount_max` | `percentile25` and `percentile75` of the first distribution (Glassdoor's "most likely range") |
| `currency`, `period` | `currency`; `duration` P1M → month, P1Y → year (anything else: no data) |
| `sample_size` | "N salaries" in the page, when shown |
| `observed_on` | the newest "submitted on" date, else today |
| `summary` | median, P10–P90, pay type (the distribution's `name`, e.g. "base") |
| `country` | the search's country |

The agent adds `basis`, `level`, the posting or research key, checks
comparability, and stores it with `jt salary evidence add`. The page's prose
(FAQ) is never used for figures: it names the wrong period. No distribution →
`{"data": false, "reason": …}`.

### D7. Stop rules

Blocked (record `blocked`, refuse later calls in the run): status 403/429, a
title with "Security", "Un momento", or "Just a moment" after Scrapling's
challenge handling, or a sign-in wall (D2). Error: a search page with neither
cards nor a "no results" message, show-more JSON that does not parse, three
unreadable postings in a row (D5), or a salary page without `Occupation`
data. `scrapling` not installed → `missing_dependency` naming the install
command.

## Risks / Trade-offs

- [Cloudflare changes its check and Scrapling stops passing] → D7 records
  Glassdoor as blocked; the run continues with the other providers; the
  provider is revisited in its own change.
- [Long runs: up to 150 posting pages per title at 5 s] → New postings only
  (seen ones are not opened); the provider file states the time per title;
  the cap is a front-matter value the user can lower in a private copy later.
- [Third-party dependency, ~120 MB browser] → Installed only when Glassdoor
  is turned on; `jt doctor` checks it.
- [Terms] → Stated before turning it on.

## Migration Plan

None: no schema change; Glassdoor starts switched off.
`docs/workspace-layout.md` gains `provider-settings/<id>.json`.
