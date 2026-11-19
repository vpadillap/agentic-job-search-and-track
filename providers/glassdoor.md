---
id: glassdoor
name: Glassdoor
kind: both
regions: [global]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
domains: [glassdoor.com, glassdoor.*]
max_results_per_query: 150
min_seconds_between_requests: 5
last_verified: 2026-11-18
---

# Glassdoor

## Access method

A **headless Scrapling stealth session**, logged out: no cookies, no account,
no sign-in, a new session for every call, discarded after it. No browser
window opens. Every Glassdoor page is opened by the reader commands, never by
you:

```
jt providers read glassdoor <run_id> --title "<title>"
jt providers salary glassdoor --title "<title>"
```

Glassdoor is protected by Cloudflare. A study on 2026-11-18 found that plain
HTTP and a plain headless Chromium get 403, and that an ordinary visible
browser gets Cloudflare's check on any second search (including the site's
own "Show more jobs"). Scrapling's stealth session gets through: searches,
"Show more jobs", posting pages, and salary pages. No account of the user is
involved, so getting past this automated check puts no account at risk.

Forbidden, without exception and without fallback:

- opening Glassdoor yourself (curl, a script, a fetch tool, a browser, the
  browser extension): only the reader commands open Glassdoor;
- the user's Glassdoor account, session, or browser, and signing in;
- calling Glassdoor's internal endpoints directly (`/graph`,
  `/job-search-next/bff/…`, `/autocomplete/…`): more results are loaded only
  by the page's own "Show more jobs" button;
- page 2 URLs (`…_IP2.htm`): logged out they repeat page 1.

If a reader reports that Glassdoor stopped (see "Stop conditions"), do not
try another way: tell the user what it said.

## Countries

Glassdoor searches a country by its own id. Verified ids (a global provider
uses this table as a lookup; it is not a coverage claim):

| Country | Glassdoor id | Place | Last verified |
|---|---|---|---|
| PE | 189 | peru | 2026-11-18 |

For a country not in this table the reader answers `missing_country`. Then
ask the user, once: "search any job title for your country on glassdoor.com
in your own browser and paste the address of the results page". Pass it with
`--search-url "<address>"`; the reader takes the country's id from it and
saves it in the user's private settings (`provider-settings/glassdoor.json`),
so later calls need nothing. An address that is not a Glassdoor job search
(`/Job/…-SRCH_IL.0,<n>_IN<id>…`) is refused.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel** (the reader refuses a
second call while one is running: `reader_busy`).

1. Run the reader: `jt providers read glassdoor <run_id> --title "<title>"`
   (add `--search-url` only as described in "Countries"). Glassdoor is
   searched for the whole profile country; `--location` is not used. A
   call takes about 5 seconds per new posting plus a minute for the search:
   a title with 100 new postings takes about 10 minutes. Postings stored by
   an earlier run are not opened again, so later runs are faster.
2. Read the summary (`read`): `site_total` (results Glassdoor reports),
   `listed` (cards loaded), `new`, `already_seen`, `outside_window`,
   `duplicate_in_run`, `unreadable` (postings skipped because their page had
   no readable description), and `stopped`. When `listed` is less than
   `site_total`, say so in the run report (the site stopped offering more, or
   the cap of 150 was reached).
3. If `drafts_path` is set, read that file, decide each draft's reading (see
   "Fields to extract"), write all readings into one JSON list in the capture
   folder (for example `<capture_folder>/glassdoor-readings-1.json`), and
   import: `jt postings import <run_id> <drafts_path> --readings <readings file>`.
   Never copy or retype a description.
4. If `stopped` is set, import the drafts it wrote before stopping, then:

   - reason `throttled`: Glassdoor is cooling down until `resume_after`. Go on
     with the next provider and tell the user when Glassdoor may go on. After
     that time, if the user wants to wait, call it again in this run for
     the titles not done yet; a call before then is refused with
     `provider_cooling` and sends nothing. If the run is finished first,
     Glassdoor is recorded as failed with reason `throttled`.
   - any other reason: stop Glassdoor for this run. The reader already
     recorded it as failed and refuses further calls in this run; go on with
     the next provider.

When every title is done and Glassdoor did not stop, record
`jt run provider <run_id> glassdoor --status ok`.

### What the reader does

- Search page:
  `https://www.glassdoor.com/Job/<place>-<title>-jobs-SRCH_IL.0,<n>_IN<id>_KO<a>,<b>.htm?fromAge=<days>`,
  where `fromAge` is the smallest of 1, 3, 7, 14, or 30 days that covers the
  run's window (longer windows search without it and drop older postings).
- It presses the page's "Show more jobs" every 5 seconds until the button is
  gone, no new postings arrive, or 150 postings are listed. Glassdoor's
  sign-up prompt ("Never Miss an Opportunity") is closed with Escape or its
  close button; no sign-in option is ever chosen.
- Each new posting's own page is loaded, 5 seconds apart; its fields come
  from the page's structured data (`JobPosting`).
- Pages are saved as `glassdoor-<n>.html` and the "Show more" responses as
  `glassdoor-<n>-more.json` in the capture folder (audit); drafts as
  `glassdoor-drafts-<n>.json`.

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | Glassdoor's listing id (`jl=` in the link) |
| url | the posting's page, without tracking parameters |
| title, company, location | the posting's `JobPosting` data (`hiringOrganization`, address locality and region) |
| country | the profile's country (ISO code) |
| posted_at | `datePosted` |
| description | the `JobPosting` description, complete, as plain text: lines kept, spaces collapsed, never summarized or translated |
| contract_type | the site's attributes, only when they say it plainly ("Tiempo completo", "Full-time", "Part-time", "Contract"…) |

Hints in each draft, for you to read, never imported as they are:
`site_attributes` (Glassdoor's extracted attributes, such as "Permanente",
"Tiempo completo", "Modelo Híbrido"), `site_employment_type` (from the
posting data), and `site_salary` (a pay range the posting data states:
currency, min, max, unit). Start from them, check them against the title and
the description, and when they disagree follow the description and add a
flag saying so (in the panel language).

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, from the title and the complete description; an attribute such as "Modelo Híbrido" supports it but is not enough alone; `null` when not stated |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in the posting's language, close to its words, at most 200 characters; `null` otherwise |
| language | the posting's language (`es`, `en`…) |
| flags | doubts for the user, in the panel language: "work mode not stated" when it applies; a contract the description states when `contract_type` is empty; any other doubt |
| published_salary | when the description or `site_salary` states a pay figure for this job: `{min, max, currency, period, basis}`; `null` otherwise. Glassdoor's estimated ranges on its own pages are not the posting's salary |

### Work mode

Decide it as for every site: only when the title or the description says so.
Words in a benefits list, in the company's general description, or about
technology ("hybrid cloud") do not count. When neither says where the work
is done, leave both `null` and add the flag "work mode not stated" (in the
panel language). Such a posting is never excluded for its work mode.

## Application form questions

Not visible without applying. Never click "Easy Apply", "Apply on employer
site", "Sign in to apply", or any apply link.

## Salary data

Glassdoor publishes salaries its users report, per title and country, on a
salary page. Use it as **one** source of salary evidence; the two-source rule
still applies (a second comparable source is needed before suggesting a
figure).

1. `jt providers salary glassdoor --title "<title>"` (the profile's country;
   `--search-url` as in "Countries"). Use the title closest to the posting's
   level: Glassdoor has separate pages such as "Data Engineer" and "Senior
   Data Engineer".
2. With `"data": true`, the result holds an `evidence` draft: `source`,
   `url`, `amount_min`/`amount_max` (the 25th–75th percentile, Glassdoor's
   "most likely range"), `currency`, `period`, `sample_size` (reports shown),
   `observed_on` (the newest report date), `country`, and a `summary` with the
   median and the 10th–90th percentiles. The figures come only from the page's
   structured data, never from its text (the page's FAQ text names the wrong
   period).
3. Add what only you can decide: `basis` (Glassdoor reports gross pay),
   `level` (the seniority of the page's title), and `posting_id` or
   `research`; check comparability (same country and level, similar work mode
   and industry); then store it with `jt salary evidence add -`.
4. With `"data": false`, record that Glassdoor had no data for that title
   among the sources you checked (`jt salary none … --checked`).

## Limits and etiquette

- **Terms of use.** Glassdoor's terms (glassdoor.com/about/terms.htm; since
  July 2026 they name Indeed, Inc. as the operator) forbid collecting
  information by automated means and using robots, spiders, or scraping
  tools without prior written permission (as summarized by ConductAtlas on
  2026-11-18; the page itself is behind Cloudflare). The reader uses no
  account, but it is automated access and it gets past Glassdoor's automated
  check (Cloudflare) on purpose. The realistic consequence is that Glassdoor
  blocks requests from the user's IP address for a while. Tell the user this
  before they turn Glassdoor on.
- At least 5 seconds between page loads and clicks, also between one call and
  the next; at most 150 postings per title; each posting opened once per run.
- Read-only: never apply, save, follow, message, or sign in.
- **When Glassdoor asks to slow down** (a soft block, see "Stop conditions"),
  the reader waits and sends the same request again: as long as the site's
  `Retry-After` header says when it sends one, otherwise 10–20 seconds, then
  20–40 seconds. At most 3 tries per request, never more than 2 minutes per
  wait, at most 6 retries per run. If that does not clear it, Glassdoor cools
  down for 15 minutes (30 the second time, longer when the site asks) and
  the same run goes on after that; a third throttle in a run stops Glassdoor
  for the run. There is no way to end a cool-down early.
- Waiting is the only answer to a block: never a proxy, a different IP, a
  changed or rotating user agent or headers, an account, cookies, or a fresh
  browser identity to get past it.

### Stop conditions

**Soft blocks** (a throttle: the site asks to slow down):

- a page answers HTTP 429, or its title is a security check ("Security |
  Glassdoor", "Un momento…", "Just a moment…") that Scrapling did not pass.

A salary page that stays throttled answers `{"data": false, "throttled":
true, "resume_after": …}`: record no Glassdoor evidence for that title and
do not ask for that salary page again before `resume_after`.

The reader waits and retries as stated in "Limits and etiquette". When the
throttle does not clear, it ends the call with `stopped.reason: throttled`
and `resume_after` (the time it may go on), keeps what was already read, and
records a cool-down on the run; calls before that time are refused without
any request (`provider_cooling`). The first call after it goes on in the
same run: a title already completed is not searched again, and postings
already opened are not opened again (a posting whose page was throttled is
opened then); the search page itself is loaded again.

**Hard blocks and errors.** The reader stops **all** Glassdoor work for the
rest of the run, keeps what was already read, records Glassdoor as failed
for the run, and refuses later calls in that run (`provider_stopped`) when:

- a page answers 403, or its title is a Cloudflare block page ("Attention
  Required!", "Access denied"), or a sign-in prompt does not close: reason
  `blocked`;
- a search page has no postings and does not say 0 results, a "Show more"
  response does not parse, or three postings in a row have no readable
  description: reason `error`, with what is missing;
- the browser itself fails: reason `error`.

A single posting without a readable description is skipped and listed in
`unreadable`; the reader goes on.

## Known pitfalls

- Plain HTTP and a plain headless Chromium get 403 ("Security | Glassdoor").
- A visible Playwright browser loads one search per session; any second
  search, and "Show more jobs", get Cloudflare's check (Turnstile). That is
  why the reader uses Scrapling.
- Page 2 URLs (`…_IP2.htm`) repeat page 1 when logged out.
- Typing a country in Glassdoor's location box is not reliable for finding
  its id; use the table or a pasted search address.
- Some postings never show their description logged out (seen once in the
  study); they are skipped.
- The salary page's FAQ text called a monthly figure yearly; only the
  structured data is used.
- "Show more jobs" stopped offering more at 127 of 152 results in the study:
  `listed` can be smaller than `site_total`.
