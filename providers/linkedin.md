---
id: linkedin
name: LinkedIn
kind: jobs
regions: [global]
access: http
requires_login: false
live_walk: false
dependencies: [curl]
max_results_per_query: 30
min_seconds_between_requests: 5
last_verified: 2026-11-17
---

# LinkedIn

## Access method

Plain HTTP with `curl`, logged out: no browser, no cookies, no account. Two
kinds of page, and nothing else:

1. **Guest search** (the list of postings):
   `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`.
   It returns an HTML fragment with 10 postings ("cards") per page.
2. **Public posting page** (one posting):
   `https://www.linkedin.com/jobs/view/<id>/`. It has the complete
   description, the seniority, and the contract type.

Forbidden, without exception and without fallback:

- the user's LinkedIn session, cookies, or credentials, and logging in;
- the browser extension, Playwright, or any other browser;
- the `https://www.linkedin.com/jobs/search` page (it shows a sign-in pop-up
  and its filters push to a login screen);
- the guest detail endpoint `jobs-guest/jobs/api/jobPosting/<id>` (it gave the
  wrong seniority in the study; use the posting page);
- proxies, rotating user agents, or anything meant to get around LinkedIn's
  limits;
- following a redirect.

If these pages stop working as described here, record LinkedIn as failed for
this run (see "Stop conditions") and tell the user that the recipe needs to
be revisited. Do not try another way.

## Search recipe

Run every request with these exact options (on Windows PowerShell write
`curl.exe`, not `curl`):

```
curl -s -o "<capture_folder>/linkedin-<n>.txt" \
  -w "%{http_code} %{redirect_url}" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36" \
  -H "Accept-Language: en-US,en;q=0.9" \
  "<url>"
```

`-w` prints the status code and, for a redirect, where it points: read it
after every request (see "Stop conditions"). `<n>` counts up from 1 for
the run; the saved file is the capture the job-search skill asks for.

**Wait at least 5 seconds between any two LinkedIn requests**, search or
posting page.

### 1. Search each title

For each title in `titles`, one search:

```
https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=<title>&location=<location>&f_TPR=<window>&start=<start>
```

- `keywords`: the title, URL-encoded (`Senior%20Data%20Engineer`).
- `location`: the profile's `country` as its English name, URL-encoded
  (`Peru`, `United%20States`). Leave the parameter out when the profile has
  no country. Cities and remote scope are checked later, in the first-pass
  filter.
- `f_TPR`, the posting age. LinkedIn offers visitors only three windows; use
  the smallest that covers the run's window (`posting_age_days`):

  | Run window | `f_TPR` |
  |---|---|
  | 1 day | `r86400` |
  | 2–7 days | `r604800` |
  | 8–30 days | `r2592000` |

  For more than 30 days use `r2592000`; postings older than the run's window
  are dropped by the import, so no extra check is needed.
- `start`: `0`, then `10`, then `20`. At most these 3 pages per title
  (`max_results_per_query: 30`). Stop earlier when a page has fewer than 10
  cards.

These are the only parameters LinkedIn honours for visitors (verified
2026-11-17). Do **not** send `f_WT` (work mode), `f_JT` (contract type),
`f_E` (experience), or `sortBy`: they are ignored and change nothing.
Results come in relevance order, not by date.

### 2. Read the cards

Each card is a `<div>` whose class contains `base-search-card`. From each
card take:

- the job id from `data-entity-urn="urn:li:jobPosting:<id>"`;
- the publication date from `<time ... datetime="YYYY-MM-DD">`.

Skip a card whose date is older than the run's `published_since`, and a job
id already read in this run (the same posting can appear under two titles).

### 3. Open each posting

For each remaining card, open `https://www.linkedin.com/jobs/view/<id>/`
with the same `curl` options (and the 5-second wait). Read the fields below
from the card and the posting page, then build the posting record.

Import in batches with `jt postings import <run_id> -` as you go (for
example after each title), so that a stop keeps what was already read.

## Fields to extract

| Field | Where to find it | Notes |
|---|---|---|
| external_id | card: `data-entity-urn="urn:li:jobPosting:<id>"` | the numeric id only |
| url | built: `https://www.linkedin.com/jobs/view/<id>/` | never the card's link (it carries a slug and tracking parameters) |
| title | card: element with class `base-search-card__title` | text, whitespace collapsed |
| company | card: element with class `base-search-card__subtitle` | text of its link |
| location | card: element with class `job-search-card__location` | as shown ("San Diego, CA") |
| country | from the location and the search's `location` | ISO code (PE, US) |
| posted_at | card: `<time datetime="YYYY-MM-DD">` | already an absolute date |
| description | posting page: element with class `show-more-less-html__markup` | the complete text, verbatim, as plain text: keep paragraph breaks and list items (one per line, with their bullet), drop the HTML tags, never summarize or translate |
| seniority | posting page criteria: the `description__job-criteria-text` under the heading "Seniority level" | as shown ("Mid-Senior level"); omit when it says "Not Applicable" |
| contract_type | posting page criteria: "Employment type" | Full-time → `full-time`, Part-time → `part-time`, Contract → `contractor`; omit anything else (Temporary, Internship, Volunteer, Other) and say it in a flag |
| work_mode | **your reading** of the title and the complete description | see "Work mode" below; LinkedIn shows visitors no work-mode field |
| work_mode_detail | **your reading** of the description | see "Work mode" below |
| published_salary | the description, or a card element with class `job-search-card__salary-info` | only when a pay figure for this job is stated; none appeared in the study |
| language | the description | the posting's language (es, en…) |
| flags | | "work mode not stated" (in the panel language) when it applies; any other doubt |
| form_questions | | never: not visible without applying |

### Work mode

LinkedIn does not show logged-out visitors whether a job is remote, hybrid,
or on site. Read the title and the complete description and decide it
yourself, as a person would:

- `work_mode`: `remote`, `hybrid`, or `onsite`, only when the posting says
  so (in the title, such as "Business Analyst | Hybrid (Oakland)", or in the
  text). Words in a benefits list, in the company's general description, or
  in another job's title do not count. A posting that only names an office
  city is not "onsite" for that reason alone.
- `work_mode_detail`: how the posting describes the arrangement when it
  says more than the mode, in the posting's language and close to its words,
  at most 200 characters. Examples: "Híbrido: 2 días presencial por semana",
  "Hybrid: Tuesday to Thursday in the Oakland office", "Remote within the US;
  quarterly on-site week", "Summer hours: Fridays until noon". Leave it
  `null` when the posting says nothing more.
- When neither the title nor the description says where the work is done,
  leave both `null` and add the flag "work mode not stated" (in the panel
  language). Such a posting is never excluded for its work mode.

## Application form questions

Not visible without applying. LinkedIn's apply flow needs an account (or
leads to the company's own site), so nothing is recorded. Never click or
request an apply link.

## Limits and etiquette

- **Terms of use.** LinkedIn's User Agreement (section 8.2, effective
  2025-11-03) forbids scraping or copying its services with software,
  scripts, crawlers, or browser plug-ins, and it applies to logged-out
  visitors as well as members (section 1.2). Its robots.txt disallows
  `/jobs-guest/` and says automated access without permission is prohibited.
  This recipe never involves the user's account, but it is still automated
  access that LinkedIn does not permit. The realistic consequence is that
  LinkedIn throttles or blocks requests from the user's IP address for a
  while. Tell the user this before they turn LinkedIn on.
- At least 5 seconds between requests; at most 3 search pages per title and
  one posting page per job id per run.
- Read-only: never apply, save, follow, message, or sign in.

### Stop conditions

Stop **all** LinkedIn requests for the rest of the run, keep what was already
imported, and record
`jt run provider <run_id> linkedin --status failed --reason blocked --detail "<status> <url>"`
when any request:

- answers HTTP 429 or 999;
- answers any 3xx redirect (do not follow it; name where it points, for
  example `authwall`, `login`, `signup`, or `checkpoint`);
- answers 200 on `start=0` without any card and with a sign-in form in the
  body.

If the HTML no longer matches this file (no `base-search-card` in a page that
has postings, or no `show-more-less-html__markup` on posting pages), record
`--status failed --reason error --detail "<what changed>"` and stop
LinkedIn for this run.

A search that returns no cards and no sign-in form simply has no results for
that title.

## Known pitfalls

- **Ignored filters.** `f_WT`, `f_JT`, and `sortBy` look like they work
  because pages come back normally, but the cards are identical to the
  unfiltered search. Work mode and contract type come from each posting.
- **Relevance order.** Without date sorting, the newest postings can sit
  beyond page 3. The age window keeps results recent; nothing else can be
  done logged out.
- **Wrong seniority on the guest detail endpoint.** It said "Not Applicable"
  where the posting page said "Mid-Senior level". Always use the posting
  page.
- **Sign-in markup on posting pages.** The posting page contains the markup
  of a sign-in pop-up and links to `uas/login` and `signup`. That is normal;
  only a redirect is a block.
- **"Remote" or "Hybrid" in the wrong place.** Posting pages list similar
  jobs whose titles may say "Remote" or "Hybrid". Read only this posting's
  title and description.
- **The same posting under two titles.** Open its page once.
- **Location text.** Free-text `location` resolves to LinkedIn's own place id
  (`geoId`); a country's English name works. An unusual spelling can return
  results for another place: check the cards' locations on the first page.
