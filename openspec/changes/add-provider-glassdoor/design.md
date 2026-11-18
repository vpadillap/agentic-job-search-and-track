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

**Goals:** Glassdoor postings with complete descriptions, logged out, with
the same pacing, stop rules, and draft/readings flow as Indeed.

**Non-Goals:** signing in; the user's browser; anything that hides
automation; internal endpoints; posting pages under `/job-listing/` (they are
links in the drafts only); salary pages and company reviews; applying.

## Decisions

### D1. A reader like Indeed's

`readers/glassdoor.py` with an injectable browser adapter (`search(url)`,
`open(job_id) -> panel text`, `close()`); the real adapter is a visible
Chromium, a new context per call, locale of the country. Parsing the flight
data is a pure function tested with fictional pages. Shared run state,
pacing, lock, seen postings, and stop recording come from
`readers/common.py`.

### D2. The modal is closed, never answered

When `dialog[open]` appears, the reader presses Escape once; if a dialog is
still open it clicks only the button with `data-test="auth-modal-close-button"`.
It never clicks a sign-in option. If the dialog stays open, or a page asks to
sign in to see postings, Glassdoor is recorded as blocked (sign-in wall).

### D3. Fields

`external_id` = listing id; `url` = the JSON-LD `job-listing` URL; title,
company, location as given; `posted_at` = run date minus `ageInDays`;
description = side-panel text (spaces collapsed per line, at most one blank
line); informational `attributes` (the extracted job attributes) and
`salary_shown` (the card's salary text, "Employer provided" or estimate kept
as shown). Work mode and contract type are left to the agent's reading, as
for Indeed.

### D4. Stop rules

Blocked: response 403/429, a page title with "Security" or "Un momento" /
"Just a moment" that does not clear within 30 seconds, or a sign-in wall
(D2). Error: no postings data on a page that is not a "no results" page, a
card without its id, or a panel whose description does not appear within 20
seconds of the click.

## Open Questions

Answered in this change before the reader is built (proposal, "Still to
confirm"): modal frequency over a full page, pagination, `locId` for other
countries, and description completeness. D1–D4 are revised with the results.

## Risks / Trade-offs

- [A window appears on the user's screen during the search] → Said in the
  provider file; one title per call.
- [Glassdoor changes the page or its checks] → The reader stops with
  `error` or `blocked` naming what happened.
- [Terms] → Stated before turning it on.

## Migration Plan

None: no schema change; Glassdoor starts switched off.
