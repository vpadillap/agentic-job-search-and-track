---
id: greenhouse
name: Greenhouse
kind: jobs
regions: [global]
access: http
requires_login: false
live_walk: false
dependencies: []
max_results_per_query: 100
min_seconds_between_requests: 5
last_verified: 2026-11-18
---

# Greenhouse

## Access method

Greenhouse is the applicant-tracking system many companies use; each company
has its own job board. Postings are read only through Greenhouse's **public
Job Board API** (`https://boards-api.greenhouse.io/v1/boards/<board>/jobs`),
over plain HTTP, with no sign-in, by the reader command:

```
jt providers read greenhouse <run_id> --title "<title>" --found <links file>
```

Greenhouse documents the API as public ("Job Board data is publicly
available, so authentication is not required for any GET endpoints").

The API has no search across companies: it needs each company's **board
name** (the part after `greenhouse.io/` in a board or posting link, for
example `encora10` in `https://job-boards.greenhouse.io/encora10/jobs/5283692007`).
You find boards and postings for each title, in one of two ways (see "Search
recipe"), and pass their links to the reader; the reader also rechecks the
boards it remembers for this user.

Forbidden, without exception:

- typing or handling the user's MyGreenhouse credentials, or signing in for
  them;
- reading, copying, or storing the account data MyGreenhouse shows (name,
  email, profile, applications);
- pressing Apply, saving jobs, setting alerts (the bell), or changing
  anything in the user's MyGreenhouse account or on any company board;
- reading postings any other way than through the reader (no scraping of
  board pages, no posting pages).

## Countries

Greenhouse postings say their location in their own words. The reader keeps a
posting when its location names the country or one of its cities (place
words), or says it is remote together with one of the region's words. A lookup
for this global provider, not a coverage claim:

| Country | Place words | Region words (remote postings) | Last verified |
|---|---|---|---|
| PE | Peru; Perú; Lima; Arequipa; Trujillo; Cusco; Piura | LATAM; Latin America; Latinoamérica; South America; Americas | 2026-11-18 |

For a country not in this table the reader answers `missing_country`. Ask the
user once which words mark a job as being in their country (its name in
English and Spanish and its main cities) and pass them with
`--place-words "Chile; Santiago; Valparaíso"`; they are saved in the user's
private settings (`provider-settings/greenhouse.json`), so later calls need
nothing.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel** (the reader refuses a
second call while one is running: `reader_busy`).

### 1. Find links for the title

**When the user said in this conversation that they are present and signed in
to MyGreenhouse in their own Chrome** (ask at the start of the run; do not
assume), use the signed-in search with Claude in Chrome:

1. Open a **new tab**:
   `https://my.greenhouse.io/jobs/search?query=<title>&location=<Country>&location_type=country&country_short_name=<CC>`
   (the country's English name and ISO code, e.g. `Peru` and `PE`).
2. If the page asks to sign in, do not sign in: close the tab and use web
   search below.
3. Scroll the result list to its end at a person's pace (a few seconds per
   scroll) until no more cards load.
4. Open each card, copy the link under the posting's title
   (`job-boards.greenhouse.io/<board>/jobs/<id>`), close it with Escape, a
   few seconds apart. Never press Apply, the bell, or save.
5. Close the tab.

**Otherwise** (the user is not present, not signed in, or did not say), use
web search, one query per host:

- `site:job-boards.greenhouse.io "<title>" <country or main city>`
- `site:boards.greenhouse.io "<title>" <country or main city>`
- `site:job-boards.eu.greenhouse.io "<title>" <country or main city>`

Collect the result links that point to a Greenhouse board or posting. Old
results are harmless: the API returns only current postings.

When the user asks to always check a company, add its board link (or any of
its Greenhouse posting links) to the list.

### 2. Read them

Write the links as a JSON list in the capture folder (for example
`<capture_folder>/greenhouse-found-1.json`) and run:
`jt providers read greenhouse <run_id> --title "<title>" --found <that file>`.

Read the summary (`read`): `found_postings`, `boards` (found now plus
remembered), `boards_gone` (boards that no longer exist, forgotten),
`other_title`, `other_country`, `outside_window`, `new`, `already_seen`,
`duplicate_in_run`, `capped` (100 postings reached), `ignored_links` (links
that are not Greenhouse boards or postings), and `stopped`.

### 3. Import

If `drafts_path` is set, read that file, decide each draft's reading (see
"Fields to extract"), write all readings into one JSON list in the capture
folder (for example `<capture_folder>/greenhouse-readings-1.json`), and
import: `jt postings import <run_id> <drafts_path> --readings <readings file>`.
Never copy or retype a description or a question.

If `stopped` is set, import the drafts it wrote before stopping, then:

- reason `throttled`: Greenhouse is cooling down until `resume_after`. Go on
  with the next provider and tell the user when Greenhouse may go on. After
  that time, if the user wants to wait, call it again in this run for
  the titles not done yet; a call before then is refused with
  `provider_cooling` and sends nothing. If the run is finished first,
  Greenhouse is recorded as failed with reason `throttled`.
- any other reason: stop Greenhouse for this run. The reader already
  recorded it as failed and refuses further calls in this run; go on with
  the next provider.

When every title is done and Greenhouse did not stop, record
`jt run provider <run_id> greenhouse --status ok`.

### What the reader does

- Postings from the signed-in search are read directly
  (`…/boards/<board>/jobs/<id>?questions=true`): Greenhouse already matched
  them to the title; the reader checks country and window.
- Boards (found now and remembered) are read once per run
  (`…/boards/<board>/jobs?content=true`); a posting is kept when its title
  contains the searched title's words (seniority words such as senior, lead,
  junior, II aside), its location matches the country (see "Countries"), and
  it was first published inside the run's window. Each kept posting's
  questions are read with `?questions=true`.
- Boards with postings in the user's country are remembered and rechecked in
  later runs; a board that answers 404 is forgotten.
- At least 5 seconds between requests, also between calls; postings stored by
  an earlier run are not read again; at most 100 postings per title.
- Answers are saved in the capture folder (`greenhouse-board-<board>.json`,
  `greenhouse-<board>-<id>.json`); drafts as `greenhouse-drafts-<n>.json`.

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | the posting id |
| url | `absolute_url` (the company's careers page when it has one) |
| title, company, location | `title`, `company_name`, `location.name` |
| country | the profile's country (ISO code) |
| posted_at | `first_published` (`updated_at` when missing) |
| description | `content`, complete, as plain text: lines kept, spaces collapsed, never summarized or translated |
| form_questions | every application question with its label, kind (text, long text, file, choice, multiple choice), options, and whether it is required, including location questions |

Hints in each draft, for you to read, never imported as they are:
`site_language` (the posting's language as Greenhouse records it),
`site_departments`, and `site_offices`.

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, from the title, the location, and the complete description; `null` when not stated |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in the posting's language, close to its words, at most 200 characters; `null` otherwise |
| language | the posting's language (`es`, `en`…); `site_language` helps but the description decides |
| flags | doubts for the user, in the panel language: "work mode not stated" when it applies; a contract type the description states; a remote posting that may not accept the user's country; any other doubt |
| published_salary | when the description states a pay figure for this job: `{min, max, currency, period, basis}`; `null` otherwise |

### Work mode

Decide it as for every site: only when the title, the location, or the
description says so. Words in a benefits list, in the company's general
description, or about technology ("hybrid cloud") do not count. When none
says where the work is done, leave both `null` and add the flag "work mode not
stated" (in the panel language). Such a posting is never excluded for its
work mode.

## Application form questions

Read by the reader from the public API (`?questions=true`) and stored with the
posting: the standard fields (name, email, resume, cover letter…) and the
company's own questions. Never open, fill, or submit an application form.

## Limits and etiquette

- **Terms of use.** The Job Board API is documented by Greenhouse as public
  for reading (docs.greenhouse.io, read 2026-11-18); no rate limits are
  stated. The signed-in search runs in the user's own MyGreenhouse account,
  through their own Chrome: keep it read-only and at a person's pace.
- At least 5 seconds between API requests; at most 100 postings per title.
- Read-only: never apply, save, follow, message, set alerts, or sign in.
- **When Greenhouse asks to slow down** (a soft block, see "Stop conditions"),
  the reader waits and sends the same request again: as long as the site's
  `Retry-After` header says when it sends one, otherwise 10–20 seconds, then
  20–40 seconds. At most 3 tries per request, never more than 2 minutes per
  wait, at most 6 retries per run. If that does not clear it, Greenhouse cools
  down for 15 minutes (30 the second time, longer when the site asks) and
  the same run goes on after that; a third throttle in a run stops Greenhouse
  for the run. There is no way to end a cool-down early.
- Waiting is the only answer to a block: never a proxy, a different IP, a
  changed or rotating user agent or headers, an account, cookies, or a fresh
  browser identity to get past it.

### Stop conditions

**Soft blocks** (a throttle: the site asks to slow down):

- the API answers 429 (its `Retry-After` is honoured), or 503 with a
  `Retry-After` header.

The reader waits and retries as stated in "Limits and etiquette". When the
throttle does not clear, it ends the call with `stopped.reason: throttled`
and `resume_after` (the time it may go on), keeps what was already read, and
records a cool-down on the run; calls before that time are refused without
any request (`provider_cooling`). The first call after it goes on in the
same run: postings already read are not read again; boards are checked
again.

**Hard blocks and errors.** The reader stops **all** Greenhouse work for the
rest of the run, keeps what was already read, records Greenhouse as failed
for the run, and refuses later calls in that run (`provider_stopped`) when:

- the API answers 403: reason `blocked`;
- three answers in a row are not the expected JSON: reason `error`.

A board or posting that answers 404 no longer exists; the reader goes on.

## Known pitfalls

- The candidate search (`my.greenhouse.io/jobs/search`) needs a sign-in: logged
  out it redirects to `/users/sign_in`.
- A search result card has no link; the board name is only in the opened card
  (the link under the title).
- Web search results are often old postings or boards that no longer exist
  (404); that is expected.
- There is no `boards-api.eu.greenhouse.io`: boards on
  `job-boards.eu.greenhouse.io` are read through the same API host.
- Some companies show their Greenhouse postings on their own careers site
  (`…?gh_jid=<id>`); those links do not carry the board name and are ignored.
