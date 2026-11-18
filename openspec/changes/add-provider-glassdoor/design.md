## Context

See the proposal's table for the first study. Observed details:

- Search page: Next.js app. The postings are in the page's flight data
  (`self.__next_f`): `searchResultsData.jobListings.jobListings[]`, each with
  `jobview.header` (`ageInDays`, `employerNameFromSearch`, `jobTitleText`,
  `locationName`, `payPeriod` and salary fields, `indeedJobAttribute.
  extractedJobAttributes` such as "Integral/Full-time" and "Modelo Híbrido",
  `easyApply`, `expired`) and the listing id. The same page has a JSON-LD
  `ItemList` with each posting's name and `job-listing/…?jl=<id>` URL.
- Cards: `li[data-test="jobListing"][data-jobid=<id>]`. A transparent tracking
  link (`a[data-test="job-link"]`) covers each card; a click on the card goes
  to it and the site shows the posting in the side panel without leaving the
  page. The first posting is selected on load.
- Description: element whose class starts with `JobDetails_jobDescription`;
  it shows skeleton lines until the text arrives, a moment after the click.
- Sign-up modal: `dialog[open]` with "Never Miss an Opportunity", buttons
  "Continue with Google", "Continue with Apple or email", and a close button
  `data-test="auth-modal-close-button"`. Escape closed it.
- Headless and plain HTTP get 403; calling internal endpoints (location
  lookup) from the page led to a challenge on the next load.

## Goals / Non-Goals

**Goals:** Glassdoor postings with complete descriptions and Glassdoor
salary reports as evidence, logged out, with the same pacing, stop rules, and
draft/readings flow as Indeed.

**Non-Goals:** signing in; the user's browser; anything that hides
automation; internal endpoints; posting pages under `/job-listing/` (403 even
on a first load; links in the drafts only); page 2 of a search (it repeats
page 1 logged out); a second search in a context; individual salaries that
need a sign-in; company reviews; applying.

## Decisions

### D1. A reader like Indeed's, one fresh context per search

`readers/glassdoor.py` with an injectable browser adapter
(`search(url) -> (status, title, html)`, `open(job_id) -> panel text`,
`salary(url) -> (status, title, html)`, `close()`); the real adapter is a
visible Chromium with a **new context for every search page and every salary
page** (owner's decision 1): the first load of a context is the only search
request it makes; clicking postings inside it is allowed. Locale of the
country. Parsing the flight data, the JSON-LD, and the salary page are pure
functions tested with fictional pages. Shared run state, pacing, lock, seen
postings, and stop recording come from `readers/common.py`.

### D2. The modal is closed, never answered

When `dialog[open]` appears, the reader presses Escape once; if a dialog is
still open it clicks only `data-test="auth-modal-close-button"`. It never
clicks a sign-in option. If the dialog stays open, Glassdoor is recorded as
blocked (sign-in wall).

### D3. Search URL and country id

`https://www.glassdoor.com/Job/<place>-<title>-jobs-SRCH_IL.0,<len(place)>_IN<locId>_KO<len(place)+1>,<len(place)+1+len(title)>.htm?fromAge=<d>`
with slugs in lowercase and hyphens; `fromAge` the smallest of 1, 3, 7, 14,
30 covering the run's window (larger windows use 30; the import drops older
postings). `locId` comes from the provider file's `## Countries` table (a
global provider may carry it as a lookup table: country, Glassdoor id, date
verified), or from `--search-url <url>` (the reader takes `IN<digits>` and
the place slug from a URL the user pasted; anything else is refused). A
country with neither is skipped with reason `error` and a detail asking for
the URL.

### D4. Postings, at most 30 per title

The page's flight data (`jobListings[].jobview.header`) gives up to 30
postings (owner's decision 2). If the page's total is larger, the run report
says the title was cut off at 30. `external_id` = listing id; `url` = the
JSON-LD `job-listing` URL; title, company, location as given;
`posted_at` = run date minus `ageInDays`; description = side-panel text
(spaces collapsed per line, at most one blank line); hints `site_attributes`
(extracted job attributes such as "Full-time", "Hybrid") and `site_salary`
(the card's salary text as shown, with "Employer provided" or estimate). Work
mode and contract type are the agent's reading, as for Indeed.

A posting whose description does not appear within 30 seconds of the click is
skipped with a note in the capture and the run continues (one employer's
posting never loaded, also on a fresh context); after three such postings in
a row the reader stops with `error`.

### D5. Salary reader

`jt providers salary glassdoor --title "<title>" [--country CC] [--run <id>]`
(country defaults to the profile's). URL:
`/Salaries/<place>-<title>-salary-SRCH_IL.0,<n>_IN<locId>_KO<a>,<b>.htm`.
It returns one evidence draft, never stored by itself:

| Evidence field | From |
|---|---|
| `source` | "Glassdoor" |
| `url` | the salary page |
| `amount_min`, `amount_max` | P25 and P75 of the JSON-LD `MonetaryAmountDistribution` (Glassdoor's "most likely range") |
| `currency`, `period` | its `currency`; `duration` P1M → month, P1Y → year (anything else: refused) |
| `sample_size` | "N salaries" in the page |
| `observed_on` | the newest visible report date, else today |
| `summary` | median and P10–P90, pay type ("base"), total pay range if shown |
| `country` | the search's country |

The agent adds `basis`, `level`, the posting or research key, and decides
comparability, then stores it with `jt salary evidence add`. The page's FAQ
text is never used for figures (it names the wrong period). No JSON-LD
distribution → "no data" with the reason; nothing guessed.

### D6. Stop rules

Blocked (record `blocked`, refuse later calls in the run): response 403/429
on a first load, a title with "Security", "Un momento", or "Just a moment"
that does not clear within 30 seconds, or a sign-in wall (D2). Error: no
postings data on a page that is not a "no results" page, a card without its
id, three descriptions in a row that never load, or a salary page without the
`Occupation` data.

## Risks / Trade-offs

- [A window appears on the user's screen during the search] → Said in the
  provider file; one title per call.
- [30 postings per title] → Narrow windows (`fromAge`); cut-off reported.
- [A country without an id] → The user pastes one search URL once.
- [Glassdoor changes the page or its checks] → The reader stops with
  `error` or `blocked` naming what happened.
- [Terms] → Stated before turning it on.

## Migration Plan

None: no schema change; Glassdoor starts switched off.
