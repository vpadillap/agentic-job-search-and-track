---
id: agentic-search
name: Web search (company sites)
kind: jobs
regions: [global]
access: web-search
requires_login: false
live_walk: false
dependencies: []
max_results_per_query: 40
min_seconds_between_requests: 3
last_verified: 2026-11-18
---

# Web search (company sites)

## Access method

No reader: **you** search the open web with your web search and web fetch
tools and follow this recipe step by step. The goal is openings that job
boards miss: those published on companies' own careers pages and
applicant-tracking boards, and on reputable sites that have no provider file.

- Use your web search tool to discover. A web fetch tool that answers with a
  summary is fine for looking around a careers page, but **never for a
  description**: it does not return the text unchanged. To read a posting,
  save the page itself into the capture folder (for example
  `curl -sL "<url>" -o <capture_folder>/agentic-search-<n>.html`) and copy the
  description from that file, or use the site's public JSON when it has one
  (Lever: `https://api.lever.co/v0/postings/<company>/<id>`, field
  `descriptionPlain` plus its `lists`).
- Use the browser extension only when a careers page shows its openings only
  with JavaScript **and** the user said in this conversation that they are
  present; otherwise record that company as "not readable" in the capture
  file and move on.
- Never sign in, create an account, apply, fill or submit a form, subscribe to
  alerts, or give any personal data to a site.

### Sites you never read here

A site that has its own provider file is searched by its own provider, or not
at all if the user turned it off. Never read it here, whether that provider is
on or off, and never import a posting found only there. Today:

| Provider | Domains |
|---|---|
| linkedin | `linkedin.com` |
| indeed | `indeed.com` and its country sites (`pe.indeed.com`…) |
| bumeran | `bumeran.com.pe` (and other `bumeran.*` sites) |
| glassdoor | `glassdoor.com` and its country sites |
| greenhouse | `greenhouse.io` (`job-boards.greenhouse.io`, `boards.greenhouse.io`, `job-boards.eu.greenhouse.io`) |

`jt providers list` shows every provider file; when a new one appears, treat
its site the same way (its file names it).

## Search recipe

### 0. Before the first title

1. `jt companies list --all`: the companies earlier runs of this season found
   (`excluded: false`) and the ones the user excluded (`excluded: true`).
2. Decide the mode for this run:
   - **normal**: revisit known companies, then discover new ones;
   - **different companies**: when the user asked in this conversation for
     other or different companies, skip step 1 below and leave every known
     company out of discovery.
3. A company the user asks never to see ("never show me X"): store a rule
   (`jt rules add`) and `jt companies exclude <id or careers page> --reason
   "<the user's words>"`. Never explore an excluded company, and never import
   its postings from this provider.

### For each title in the run's `titles`

Stop a title when you reach **40 postings** or **15 companies explored**
(known and new together); say in the run report which limit was reached.

1. **Revisit** (normal mode): for each known, not excluded company whose
   `titles` include this title, open its `careers_url` and look for current
   openings matching any included title, in the profile's country or remote
   for it.
2. **Discover** with web search, about five queries, in the posting language
   of the profile's country and in English, for example:
   - `"<title>" <city or country> careers` / `"<title>" <ciudad o país> empleo`
   - `"<title>" <country> site:jobs.lever.co`, `site:jobs.ashbyhq.com`,
     `site:myworkdayjobs.com`, `site:jobs.smartrecruiters.com`,
     `site:apply.workable.com`, `site:<company>.bamboohr.com`
   - `"<title>" "<country>" "trabaja con nosotros"` (or the local phrase)

   From the results, note postings and the companies behind them. Leave out
   the sites in "Sites you never read here" and, in "different companies"
   mode, every known company.
3. **Judge the source** (reputation rules, in order of preference):
   1. the company's own careers page;
   2. the company's applicant-tracking board (Lever, Ashby, Workday,
      SmartRecruiters, Workable, BambooHR, Teamtailor, Recruitee…);
   3. government or university job portals;
   4. established national or professional job sites with no provider file.

   **Never use**: aggregators that copy postings from elsewhere (find the
   original instead), pages without a company name, pages that ask for
   payment or personal data before showing the posting, and postings whose
   page says they are closed.
4. **Expand**: for each new company, open its careers page once and look for
   other openings matching any included title.
5. **Read** each posting from the most direct source you found for it (the
   company's own page over any copy). Copy the description **verbatim and
   complete**. Record the publication date only when the page states it.
6. **Remember the companies**: `jt companies record -` with one item per
   company you explored or revisited for this title:
   `{"name", "careers_url", "found_via" (the query or page where it
   appeared), "title" (this title), "matches" (matching postings you
   found)}`. A company the answer lists under `excluded` must not be imported.
7. **Import** the postings (below) with `jt postings import <run_id> -`, then
   the next title.

Save what you read (page text) into the run's `capture_folder`, one file per
page, named `agentic-search-<n>.txt`, with its URL on the first line. These
are for audit only.

When every title is done, record `jt run provider <run_id> agentic-search
--status ok`. If you could not search at all (no web search tool), record
`--status failed --reason error --detail "<what happened>"`.

## Fields to extract

You build each record yourself:

| Field | What to put |
|---|---|
| provider | `agentic-search` |
| external_id | the posting's canonical URL, without tracking parameters (`utm_*`, `ref`, `source`, `gh_src`…) |
| url | the same URL |
| source_site | the host of that URL, e.g. `careers.example.com`, `jobs.lever.co` |
| title, company, location | as the posting states them |
| country | the profile's country, when the posting is in it or remote for it |
| posted_at | only when the page states a date; otherwise leave it out and add the flag "publication date not shown" (in the panel language). Never guess a date |
| description | the complete text, verbatim, as plain text (lines kept); never summarized or translated |
| contract_type, seniority | only when the posting says it plainly |
| work_mode, work_mode_detail, language, flags, published_salary | your reading, as for every provider (see below) |
| form_questions | only when the page shows the application questions without starting an application |

Your reading:

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, only when the title, location, or description says so; `null` otherwise |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in its language, close to its words, at most 200 characters |
| language | the posting's language (`es`, `en`…) |
| flags | in the panel language: "work mode not stated"; "publication date not shown"; "found on <site>, not on the company's own page" when you could not find the original; any other doubt |
| published_salary | only when the posting states a figure: `{min, max, currency, period, basis}` |

### Work mode

Decide it as for every site: only when the title, the location, or the
description says so. Words in a benefits list, in the company's general
description, or about technology ("hybrid cloud") do not count. When none
says where the work is done, leave both `null` and add the flag "work mode not
stated" (in the panel language).

## Application form questions

Only when the page lists them without starting an application (some
applicant-tracking boards show the whole form). Never click "Apply", never
start or save an application.

## Limits and etiquette

- At most 40 postings and 15 companies explored per title; about five
  discovery searches per title; at least 3 seconds between page loads on the
  same site.
- Respect each site's terms: read public pages only, at a person's pace;
  never sign in, never use a site that asks for an account or payment to
  show postings.
- Read-only everywhere.

## Known pitfalls

- Search results vary between runs; the import's seen and duplicate checks
  keep the panel consistent, so do not de-duplicate yourself.
- Many careers pages load openings with JavaScript; web fetch then sees none.
  Note the company as "not readable" and move on (or use the browser
  extension when the user is present).
- Aggregators copy postings with wrong or missing dates; prefer the original.
- A posting you find on a provider's site (for example on LinkedIn) is not
  yours to import, even if the provider is off.
- Many postings in search results are already closed (Lever answers "Document
  not found"). Look at the company's current list instead: on Lever,
  `https://api.lever.co/v0/postings/<company>?mode=json` lists every open
  posting with its location and creation date.
- A careers page carries navigation, benefits links, and FAQs around the
  posting. The description runs from the first line of the posting to its
  last paragraph: keep every paragraph of the posting (including a final
  compensation or equal-opportunity paragraph) and none of the page around it.
  Check the last lines before importing; a link inside a paragraph is part of
  the paragraph.
- Seen on 2026-11-18 for "Senior Data Engineer" in Peru: of the companies a
  search found, one board no longer existed, one (815 postings) had only older
  roles for other countries, and one careers page had a current posting with
  no publication date. That is a normal run.
