---
id: getonbrd
name: Get on Board
kind: jobs
regions: [global]
access: http
requires_login: false
live_walk: false
dependencies: []
domains: [getonbrd.com]
max_results_per_query: 60
min_seconds_between_requests: 5
last_verified: 2026-11-18
---

# Get on Board

## Access method

Get on Board is a job board for technology roles, mostly in Latin America and
remote. It publishes a **free public API** that needs no key; the reader uses
it over plain HTTP:

```
jt providers read getonbrd <run_id> --title "<title>"
```

The API (`https://www.getonbrd.com/api/v0/search/jobs`) gives every posting
of a search with its complete description, date, remote scope, salary range,
and company, so no page is opened and no browser is needed.

Forbidden, without exception:

- opening Get on Board yourself (a script, a fetch tool, a browser): only the
  reader reads it;
- the user's Get on Board account, and signing in;
- the private API (`/api/v0/jobs/<id>` answers 401: it needs a key; the search
  already carries everything);
- applying, or starting an application.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel** (`reader_busy`).

1. `jt providers read getonbrd <run_id> --title "<title>"`.
2. Read the summary (`read`): `searches` (the country search and the remote
   search, with the new postings each added), `cards`, `other_title`
   (postings whose title does not match: the site searches the whole text),
   `outside_window`, `new`, `already_seen`, `duplicate_in_run`, `capped` (60
   reached), `note` (for example when the profile has no country), and
   `stopped`.
3. If `drafts_path` is set, read that file, decide each draft's reading (see
   "Fields to extract"), write all readings into one JSON list in the capture
   folder (`<capture_folder>/getonbrd-readings-1.json`), and import:
   `jt postings import <run_id> <drafts_path> --readings <readings file>`.
   Never copy or retype a description.
4. If `stopped` is set, import the drafts it wrote before stopping, then:

   - reason `throttled`: Get on Board is cooling down until `resume_after`. Go on
     with the next provider and tell the user when Get on Board may go on. After
     that time, if the user wants to wait, call it again in this run for
     the titles not done yet; a call before then is refused with
     `provider_cooling` and sends nothing. If the run is finished first,
     Get on Board is recorded as failed with reason `throttled`.
   - any other reason: stop Get on Board for this run. The reader already
     recorded it as failed and refuses further calls in this run; go on with
     the next provider.

If `title_problem` is set (`stopped` is empty), the reader ended only that
title: a page was not what it expects, also when it loaded it once more.
Import the drafts it wrote, go on with the next title, and remember the title
and `title_problem.kind` for the report. Get on Board is not stopped: every title
is tried. When `site_may_have_changed` is true, the same problem ended every
title that read anything in this run: say in the report that Get on Board has
probably changed, so the owner can fix its reader. A title with no results
is never a problem.

When every title is done and Get on Board did not stop, record
`jt run provider <run_id> getonbrd --status ok`, adding
`--detail "<n> titles ended early: <title> (<kind>), …"` when titles ended
with a title problem (and "the site may have changed" when the last summary
said so).

### What the reader does

- Two searches per title, 120 postings per page, up to 5 pages each:
  1. `?query=<title>&country_code=<profile country>`: postings in the
     country and remote postings open to it (the site applies the scope and
     leaves out remote postings limited to other countries);
  2. `?query=<title>&remote=true`: postings remote from anywhere, which the
     country search leaves out but are valid for the user.
- Both with `expand=["company","seniority","modality"]`; postings merged by
  id.
- Kept: the posting's title contains the searched title's words (seniority
  words such as senior, lead, II aside), published inside the run's window,
  not stored by an earlier run (then seen), not already handled in the run.
- At least 5 seconds between requests; answers saved in the capture folder
  (`getonbrd-<n>.json`); drafts as `getonbrd-drafts-<n>.json`.

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | the posting's id (a slug) |
| url | `links.public_url`, the posting's page on Get on Board |
| title, company | `title`; the expanded company name |
| location | the posting's `countries` ("Remote" for remote postings) |
| country | the profile's country (ISO code) |
| posted_at | `published_at` |
| description | the posting's sections in the site's order, each headline over its text (`description`, `projects`, `functions`, `desirable`, `benefits`), as plain text: never summarized or translated |

Hints in each draft, for you to read, never imported as they are:
`site_remote` (`fully_remote`: from anywhere; `remote_local`: remote within
some countries or regions, already filtered for the user's country; `hybrid`;
`no_remote`), `site_seniority` ("Semi Senior"…), `site_modality` ("Full
time"…), `site_salary` (`{min, max}` as the site gives them, **without
currency**), `site_perks`, `site_category`.

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | `remote` for `fully_remote` and `remote_local`; `hybrid` or `onsite` as the description says; check the description, which decides |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode (for example "remote, LatAm time zones"), close to its words, at most 200 characters |
| language | the posting's language (`es`, `en`…) |
| flags | in the panel language: "work mode not stated" when it applies; "salary currency not stated" when `site_salary` is set and the description does not say the currency; any other doubt |
| published_salary | from `site_salary` when the description or the posting states the currency and period (Get on Board ranges are usually monthly, in USD or local currency; never assume): `{min, max, currency, period, basis}`; otherwise `null` with the flag |

### Work mode

Decide it as for every site: only when the title, the remote scope, or the
description says so. Words in a benefits list or about technology ("hybrid
cloud") do not count. When nothing says where the work is done, leave both
`null` and add the flag "work mode not stated".

## Application form questions

Not in the public data. Never open, start, or submit an application.

## Limits and etiquette

- **Terms of use.** The API is free and needs no key. Using it means agreeing
  to Section 7.1 of Get on Board's Terms (getonbrd.com/about/tos#public-api-use,
  read 2026-11-18): show "Get on Board" as the source and link each job to its
  page, send applicants to Get on Board, show job data unchanged and
  refreshed at least every 24 hours, and do not resell the data or train
  models with it. This tool is personal use: the panel names Get on Board as
  the site of each posting, links to its page, shows the date it was read, and
  keeps the description unchanged; the owner accepted the 24-hour clause as
  personal use (a posting stays as it was on the day of the search; open its
  page for the current version). `robots.txt` allows every agent (`Allow: /`),
  with `Content-Signal: search=yes, ai-train=no, use=reference`.
- At least 5 seconds between requests; at most 60 postings per title.
- Read-only: never apply, save, follow, or sign in.
- **When Get on Board asks to slow down** (a soft block, see "Stop conditions"),
  the reader waits and sends the same request again: as long as the site's
  `Retry-After` header says when it sends one, otherwise 10–20 seconds, then
  20–40 seconds. At most 3 tries per request, never more than 2 minutes per
  wait, at most 6 retries per run. If that does not clear it, Get on Board cools
  down for 15 minutes (30 the second time, longer when the site asks) and
  the same run goes on after that; a third throttle in a run stops Get on Board
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
same run: a title already completed is not searched again, and postings
already opened are not opened again (a posting whose request was throttled
is opened then).

**Hard blocks and errors.** The reader stops **all** Get on Board work for
the rest of the run, keeps what was already read, records Get on Board as
failed for the run, and refuses later calls in that run (`provider_stopped`)
when:

- the API answers 403: reason `blocked`;
- three requests in a row get no answer at all (the network): reason `error`.

A search with no results is not an error.

**Title problems** end only that title, never the provider: the reader
keeps what the title read, sets `title_problem` (`kind`, `detail`), and the
next title is read normally. A search page that is not what the reader
expects is loaded once more (after the usual wait) before it counts. They
are:

- three answers in a row are not the expected JSON, each also on a second
  try: `unreadable_answers`.

One unreadable answer ends only that search (country or remote).

When the same kind has ended every title that read anything in the run (two
at least), the summary sets `site_may_have_changed`. One posting that cannot
be read is listed in `unreadable` and the title goes on.

## Known pitfalls

- The search matches the whole text: "data engineer" also returns ".NET" or
  "Full-Stack" roles. The reader keeps only matching titles (`other_title`).
- The country filter leaves out postings remote from anywhere; the reader's
  second search brings them.
- Salary ranges come without currency.
- Postings are mostly from Chile, Mexico, Peru, Colombia, and remote; other
  countries may return few or none.
