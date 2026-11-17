---
id: linkedin
name: LinkedIn
kind: jobs
regions: [global]
access: http
requires_login: false
live_walk: false
dependencies: []
max_results_per_query: 30
min_seconds_between_requests: 5
last_verified: 2026-11-17
---

# LinkedIn

## Access method

Plain HTTP, logged out: no browser, no cookies, no account. Every LinkedIn
request is made by the reader command, never by you:

```
jt providers read linkedin <run_id> --title "<title>" --location "<country>"
```

The reader uses two kinds of page and nothing else:

1. **Guest search** (the list of postings):
   `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`,
   an HTML fragment with 10 postings ("cards") per page.
2. **Public posting page** (one posting):
   `https://www.linkedin.com/jobs/view/<id>/`, with the complete
   description, the seniority, and the contract type.

Forbidden, without exception and without fallback:

- requesting LinkedIn yourself (curl, a script, a fetch tool, a browser):
  only the reader sends LinkedIn requests;
- the user's LinkedIn session, cookies, or credentials, and logging in;
- the browser extension, Playwright, or any other browser;
- the `https://www.linkedin.com/jobs/search` page (it shows a sign-in pop-up
  and its filters push to a login screen);
- the guest detail endpoint `jobs-guest/jobs/api/jobPosting/<id>` (it gave the
  wrong seniority in the study);
- proxies, rotating user agents, or anything meant to get around LinkedIn's
  limits;
- following a redirect.

If the reader reports that LinkedIn stopped (see "Stop conditions"), do not
try another way: tell the user what it said.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel**: the pause between
LinkedIn requests only holds when calls follow one another, so the reader
refuses a call while another one for the same run is still running
(`reader_busy`). Wait for the call to finish; never remove its lock file.

1. Run the reader:
   `jt providers read linkedin <run_id> --title "<title>" --location
   "<country>"`. `<country>` is the profile's `country` written as its
   English name (`PE` → `Peru`, `US` → `United States`, `MX` → `Mexico`).
   Leave `--location` out when the profile has no country. A call takes up
   to about 3 minutes (the pacing is part of it).
2. Read the summary it prints (`read`): `new` postings, `already_seen`
   (stored by an earlier run and recorded as seen without opening them
   again), `outside_window`, `duplicate_in_run` (found under an earlier
   title), `unreadable` (pages that could not be read, usually removed
   postings: they are not imported; mention them to the user), and
   `stopped`.
3. If `drafts_path` is set, read that file. Each draft is an import record
   with the fixed fields already filled in. For each draft decide its
   reading (see "Fields to extract") and write all the readings into one
   JSON list in the capture folder, for example
   `<capture_folder>/linkedin-readings-1.json`:

   ```json
   [{"external_id": "4491707026", "work_mode": "hybrid",
     "work_mode_detail": "Modalidad híbrida en Lima", "language": "es",
     "flags": [], "published_salary": null}]
   ```

4. Import the drafts with the readings:
   `jt postings import <run_id> <drafts_path> --readings <readings file>`.
   Every draft needs exactly one reading; a reading may only set
   `work_mode`, `work_mode_detail`, `language`, `flags`, and
   `published_salary`. Never copy or retype a description: it is taken from
   the draft as captured.
5. If `stopped` is set, stop LinkedIn for this run: the reader already
   recorded it as failed, and it refuses further calls in this run. Import
   the drafts it wrote before stopping, then go on with the next provider.

When every title is done and LinkedIn did not stop, record
`jt run provider <run_id> linkedin --status ok`.

### What the reader does

Shown so that you and the user know exactly what is sent; you do not do any
of this yourself.

- Search URL:
  `…/seeMoreJobPostings/search?keywords=<title>&location=<country>&f_TPR=<window>&start=<start>`,
  with these exact headers and nothing else: `User-Agent: Mozilla/5.0
  (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)
  Chrome/131.0 Safari/537.36` and `Accept-Language: en-US,en;q=0.9`.
- `f_TPR`, the posting age: the smallest window LinkedIn offers visitors that
  covers the run's window.

  | Run window | `f_TPR` |
  |---|---|
  | 1 day | `r86400` |
  | 2–7 days | `r604800` |
  | 8 days or more | `r2592000` |

  Postings older than the run's window are skipped by the reader and, if
  any got through, dropped by the import.
- `start`: `0`, then `10`, then `20`: at most 3 pages per title
  (`max_results_per_query: 30`), fewer when a page has fewer than 10 cards.
- At least `min_seconds_between_requests` (5) between any two requests,
  also between one call and the next.
- One posting page per job id per run, never for a posting stored by an
  earlier run, never for a posting outside the window.
- Each page it receives is saved as `linkedin-<n>.html` in the capture
  folder (audit); the drafts as `linkedin-drafts-<n>.json`.

These are the only parameters LinkedIn honours for visitors (verified
2026-11-17): `f_WT` (work mode), `f_JT` (contract type), `f_E` (experience),
and `sortBy` are ignored, so they are never sent. Results come in relevance
order, not by date.

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | the card's `urn:li:jobPosting:<id>` |
| url | `https://www.linkedin.com/jobs/view/<id>/` |
| title, company, location | the card, as shown |
| country | the profile's country (ISO code) |
| posted_at | the card's date |
| description | the posting page, complete, as plain text: paragraphs and list items kept (one per line, with "• "), tags dropped, never summarized or translated |
| seniority | the posting page's "Seniority level"; empty when it says "Not Applicable" |
| contract_type | "Employment type": Full-time → `full-time`, Part-time → `part-time`, Contract → `contractor`; empty for anything else |

Two more fields in each draft are for you to read, not to import:
`employment_type` (LinkedIn's own text, useful when `contract_type` is empty)
and `salary_shown` (a pay text on the card, when there is one).

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, from the title and the complete description (see "Work mode"); `null` when not stated |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in the posting's language, close to its words, at most 200 characters; `null` otherwise |
| language | the posting's language (`es`, `en`…) |
| flags | doubts for the user, in the panel language: "work mode not stated" when it applies; the `employment_type` when it is not full-time, part-time, or contract (for example "Employment type: Temporary"); any other doubt |
| published_salary | only when the posting states a pay figure for this job (in the description or `salary_shown`): `{min, max, currency, period, basis}`; `null` otherwise |

### Work mode

LinkedIn does not show logged-out visitors whether a job is remote, hybrid,
or on site. Read the title and the complete description and decide it
yourself, as a person would:

- `work_mode`: `remote`, `hybrid`, or `onsite`, only when the posting says
  so (in the title, such as "Business Analyst | Hybrid (Oakland)", or in the
  text). Words in a benefits list, in the company's general description, or
  about the company's technology ("hybrid cloud") do not count. A posting
  that only names an office city is not "onsite" for that reason alone.
- `work_mode_detail`: examples: "Híbrido: 2 días presencial por semana",
  "Hybrid: Tuesday to Thursday in the Oakland office", "Remote within the US;
  quarterly on-site week", "Summer hours: Fridays until noon".
- When neither the title nor the description says where the work is done,
  leave both `null` and add the flag "work mode not stated" (in the panel
  language). Such a posting is never excluded for its work mode.

## Application form questions

Not visible without applying. LinkedIn's apply flow needs an account (or
leads to the company's own site), so nothing is recorded. Never open an
apply link.

## Limits and etiquette

- **Terms of use.** LinkedIn's User Agreement (section 8.2, effective
  2025-11-03) forbids scraping or copying its services with software,
  scripts, crawlers, or browser plug-ins, and it applies to logged-out
  visitors as well as members (section 1.2). Its robots.txt disallows
  `/jobs-guest/` and says automated access without permission is prohibited.
  This provider never involves the user's account, but it is still automated
  access that LinkedIn does not permit. The realistic consequence is that
  LinkedIn throttles or blocks requests from the user's IP address for a
  while. Tell the user this before they turn LinkedIn on.
- At least 5 seconds between requests; at most 3 search pages per title and
  one posting page per job id per run; postings stored by an earlier run are
  not opened again.
- Read-only: never apply, save, follow, message, or sign in.

### Stop conditions

The reader stops **all** LinkedIn requests for the rest of the run, keeps
what was already read, records LinkedIn as failed for the run, and refuses
later calls in that run when:

- a request answers HTTP 429 or 999, or any redirect (it is never followed;
  the detail names where it points, for example `authwall` or `login`), or a
  search page is a sign-in form instead of results: reason `blocked`;
- a page no longer matches what the reader expects (job ids without cards
  on a search page, or a posting page without its description): reason
  `error`, with what is missing;
- the network fails: reason `error`.

A search page with no cards and no sign-in form simply has no results for
that title.

## Known pitfalls

- **Ignored filters.** `f_WT`, `f_JT`, and `sortBy` look like they work
  because pages come back normally, but the cards are identical to the
  unfiltered search. Work mode and contract type come from each posting.
- **Relevance order.** Without date sorting, the newest postings can sit
  beyond page 3. The age window keeps results recent; nothing else can be
  done logged out.
- **Wrong seniority on the guest detail endpoint.** It said "Not Applicable"
  where the posting page said "Mid-Senior level". The reader uses the
  posting page.
- **Sign-in markup on posting pages.** Posting pages contain the markup of a
  sign-in pop-up and links to `uas/login` and `signup`. That is normal; the
  reader does not treat it as a block there.
- **"Remote" or "Hybrid" in the wrong place.** Posting pages list similar
  jobs whose titles may say "Remote" or "Hybrid"; the reader keeps only this
  posting's description, but company texts can still mention them. Read
  only what concerns this job.
- **Location text.** Free-text `location` resolves to LinkedIn's own place id
  (`geoId`); a country's English name works. An unusual spelling can return
  results for another place: check the drafts' locations of the first title.
