---
id: agentic-search
name: Web search (company sites)
kind: jobs
regions: [global]
access: web-search
requires_login: false
live_walk: false
dependencies: [playwright]
max_results_per_query: 40
min_seconds_between_requests: 5
last_verified: 2026-11-19
---

# Web search (company sites)

## Access method

Two parts: **you discover**, the **reader reads**. The goal is openings that
job boards miss: those published on companies' own careers pages and
applicant-tracking boards, and on reputable sites that have no provider file.

- **Discover** with your web-search tools (more than one search engine when
  you have them: a second engine finds what the first misses). Never open a
  search engine's result pages any other way.
- **Read** every page through the reader, never with `curl`, a web fetch
  tool, or by copying text yourself:

  ```
  jt providers read agentic-search <run_id> --title "<title>" --found <file> [--location "Peru; Lima"]
  ```

  `<file>` is a JSON list of what you found: links, or objects
  `{"url", "found_via"}` (see "Search recipe" for `lines` and `synonym`).
  `--location` gives the words that place a posting in the profile's country
  (the country's name in the posting language and in English, main cities).
- The reader, for each link:
  - refuses, without any request, sites of other providers (their
    `domains`), sign-in, account, and application pages, and paths the
    site's `robots.txt` disallows;
  - waits at least 5 seconds between two requests to the same site, across
    calls of the run, and identifies itself honestly;
  - reads the page over plain HTTP; when the page needs JavaScript, renders
    it once in a plain headless Chromium (Playwright: no stealth, no cookies
    kept, no sign-in). Without Playwright it says which pages needed it
    (`needs_browser`) and how to install it: `jt providers install
    agentic-search`. Playwright is the only dependency and it is optional
    here: if it cannot be installed, search anyway (do not skip this
    provider as `missing_dependency`) and say in the report how many pages
    needed it;
  - stops using a site for the rest of the run when it refuses (`401`,
    `403`, `429`, or a "verify you are human" page). It never retries that
    site another way;
  - saves every page in the run's capture folder (`agentic-search-<n>.html`
    and `agentic-search-<n>.txt`, numbered lines, the URL on the first line);
  - writes drafts from the posting's `JobPosting` data, verbatim.
- Lever and Ashby boards are read through their documented public posting
  APIs (`api.lever.co/v0/postings/…`, `api.ashbyhq.com/posting-api/…`);
  `robots.txt` is not asked for those APIs.
- Use the browser extension (the user's Chrome) only when the reader reports
  a page as `needs_browser`, Playwright cannot be installed, **and** the user
  said in this conversation that they are present. Read only; never for a
  site that refused the reader.
- Never sign in, create an account, apply, fill or submit a form, subscribe to
  alerts, or give any personal data to a site.

### Sites you never read here

A site that has its own provider file is searched by its own provider, or not
at all if the user turned it off. Never read it here, whether that provider is
on or off, and never import a posting found only there. Each provider file
names its sites in `domains`; the reader refuses them, including the user's
private providers. Today:

| Provider | Domains |
|---|---|
| linkedin | `linkedin.com` |
| indeed | `indeed.com` and its country sites (`pe.indeed.com`…) |
| bumeran | `bumeran.com.pe` (and other `bumeran.*` sites) |
| glassdoor | `glassdoor.com` and its country sites |
| greenhouse | `greenhouse.io` (`job-boards.greenhouse.io`, `boards.greenhouse.io`, `job-boards.eu.greenhouse.io`) |
| getonbrd | `getonbrd.com` |

### Job boards without a provider file

A national or professional job board with no provider file (for example
Computrabajo) may be used to find the company behind a posting: look for
the same posting on the company's own page or applicant-tracking board first.
Pass a board's posting page to the reader only when no original exists; when
the board refuses the reader (the summary lists it under `suggest_provider`),
do not try again in any other way: tell the user and offer to add the board
as its own provider with `/add-provider`.

## Search recipe

### 0. Before the first title

1. `jt companies list --all`: the companies earlier runs of this season found
   (`excluded: false`) and the ones the user excluded (`excluded: true`).
2. **Sector employers**, once per season: when no company was recorded with
   `found_via` "sector employers", build a list of about 20 leading employers
   of the profile's sector in the profile's country, from public lists (rankings,
   chambers of commerce, business press), each with its careers page, and
   record them with `jt companies record -` (`found_via`: "sector employers:
   <source link>", `matches`: 0). They become known companies, revisited
   first.
3. Decide the mode for this run:
   - **normal**: revisit known companies, then discover new ones;
   - **different companies**: when the user asked in this conversation for
     other or different companies, skip step 1 below and leave every known
     company out of discovery.
4. A company the user asks never to see ("never show me X"): store a rule
   (`jt rules add`) and `jt companies exclude <id or careers page> --reason
   "<the user's words>"`. Never explore an excluded company, and never import
   its postings from this provider.

### For each title in the run's `titles`

Stop a title when you reach **40 postings** or **15 companies explored**
(known and new together); say in the run report which limit was reached.

1. **Revisit** (normal mode): collect the `careers_url` of each known, not
   excluded company whose `titles` include this title (and the sector
   employers).
2. **Discover**: up to **12 searches** per title, spread over these
   families, in the posting language of the profile's country and in English
   where postings there use it:
   - *Title variants*: the title, its local-language synonyms and common
     variants (for "Key Account Manager": "Ejecutivo de Cuentas Clave",
     "KAM", "Gerente de Cuentas Clave"), each with the city or country:
     `"<variant>" <ciudad o país> empleo`, `"<title>" <city> careers`.
   - *Applicant-tracking boards*: `"<title>" <country>` with
     `site:jobs.lever.co`, `site:jobs.ashbyhq.com`, `site:myworkdayjobs.com`,
     `site:jobs.smartrecruiters.com`, `site:apply.workable.com`,
     `site:<company>.bamboohr.com`, `site:teamtailor.com`,
     `site:recruitee.com`.
   - *Careers phrases*: `"<variant>" "trabaja con nosotros"`, `"únete a
     nuestro equipo"`, `"vacantes"`, `"careers"` with the country.
   - *Sector employers*: `"<employer>" <variant> empleo` for employers whose
     careers page lists no openings without a search.

   From the results, note posting links and the companies behind them. Leave
   out the sites in "Sites you never read here" and, in "different
   companies" mode, every known company. An aggregator result only tells you
   which company is hiring: search for the original.
3. **Judge the source** (reputation rules, in order of preference):
   1. the company's own careers page;
   2. the company's applicant-tracking board (Lever, Ashby, Workday,
      SmartRecruiters, Workable, BambooHR, Teamtailor, Recruitee…);
   3. government or university job portals;
   4. established national or professional job sites with no provider file
      (see "Job boards without a provider file").

   **Never use**: aggregators that copy postings from elsewhere (find the
   original instead), pages without a company name, pages that ask for
   payment or personal data before showing the posting, and postings whose
   page says they are closed.
4. **Read**: write the posting links and careers pages into one `--found`
   file and run the reader. Its summary says, besides the drafts:
   - `candidate_links`: links on a careers page whose text matches the
     title; pass the ones that are postings back in a new `--found` file;
   - `other_title`: postings whose title does not match the title searched,
     with the title they have; when one is a synonym of it (judge it as a
     recruiter would), pass `{"url": …, "synonym": true}` back;
   - `no_structured_data`: pages without posting data, with their numbered
     text file. Open the file, find the posting's first and last line (from
     its first line to its last paragraph: keep a final compensation or
     equal-opportunity paragraph, leave out navigation, benefits links, and
     the footer), and pass `{"url": …, "lines": [first, last], "title": …,
     "company": …, "location": …}` back, with title and company exactly as
     the page shows them (add `"synonym": true` when the title is a
     variant). The reader cuts those lines from the saved page: never type
     or paste a description yourself;
   - `copies` (set aside in favor of the original), `not_original` (no
     original found: add the flag below), `closed`, `gone`, `refused`,
     `refused_hosts`, `suggest_provider`, `needs_browser`.
   Second passes read from the capture with no new request.
5. **Expand**: for each new company, pass its careers page once and follow
   its `candidate_links`.
6. **Remember the companies**: `jt companies record -` with one item per
   company you explored or revisited for this title:
   `{"name", "careers_url", "found_via" (the query or page where it
   appeared), "title" (this title), "matches" (matching postings you
   found)}`. A company the answer lists under `excluded` must not be imported.
7. **Import** the drafts with your reading: `jt postings import <run_id>
   <drafts_path> --readings <file>`, then the next title.

When every title is done, record `jt run provider <run_id> agentic-search
--status ok`. If you could not search at all (no web search tool), record
`--status failed --reason error --detail "<what happened>"`.

## Fields to extract

The reader builds each draft:

| Field | What it holds |
|---|---|
| provider | `agentic-search` |
| external_id | the posting's canonical URL, without tracking parameters (`utm_*`, `ref`, `source`, `gh_src`, `lever-source`…) |
| url | the same URL |
| source_site | the host of that URL, e.g. `careers.example.com`, `jobs.lever.co` |
| title, company, location | as the posting states them (for a Lever or Ashby board, the company is the board's name) |
| country | the profile's country when the posting's location is in it (its code, or a `--location` word); otherwise empty |
| posted_at | only when the page states a date; otherwise empty |
| description | the complete text, verbatim, as plain text (lines kept): from the posting data, the board's API, or the lines you pointed at |
| contract_type | only from the posting's own employment type |
| `site_…` | hints from the posting data (`site_salary`, `site_employment_type`, `site_valid_through`, `site_workplace_type`, `site_remote`): what the site states, never imported as they are |

Your reading (`--readings`, one per draft):

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, only when the title, location, or description says so; `null` otherwise |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in its language, close to its words, at most 200 characters |
| language | the posting's language (`es`, `en`…) |
| flags | in the panel language: "work mode not stated"; "publication date not shown" when the draft has no date; "found on <site>, not on the company's own page" for the reader's `not_original`; any other doubt |
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

- At most 40 postings and 15 companies explored per title; up to 12
  discovery searches per title; the reader reads at most 40 pages per call
  and waits at least 5 seconds between two requests to the same site.
- `robots.txt` is obeyed for every page; a site that refuses is left alone
  for the rest of the run. No stealth browser, no other identity, no retry.
- Respect each site's terms: public pages only, at a person's pace; never sign
  in, never use a site that asks for an account or payment to show postings.
- Read-only everywhere. One reader call at a time per run.

## Known pitfalls

- Search results vary between runs; the import's seen and duplicate checks
  keep the panel consistent. The reader keeps one draft per posting in a run;
  do not de-duplicate further yourself.
- Many careers pages load openings with JavaScript; the reader renders them
  when Playwright is installed (`needs_browser` otherwise).
- Aggregators copy postings with wrong or missing dates; the reader follows
  their link to the original when the page has one (`copies`).
- A posting you find on a provider's site (for example on LinkedIn) is not
  yours to import, even if the provider is off; the reader refuses it.
- Many postings in search results are already closed (Lever answers "Document
  not found"; the reader lists them as `gone` or `closed`). Pass the
  company's board link instead: the reader reads its current openings.
- Seen on 2026-11-18 for commercial and marketing titles in Peru: discovery
  returned mostly aggregator and job-board listings, and a national job board
  with no provider file answered `403` to a plain request, so nothing was
  imported. That is why discovery has families and sector employers, and why
  refusing boards are offered to `/add-provider` instead of being forced.
- Seen on 2026-11-18 for "Senior Data Engineer" in Peru: of the companies a
  search found, one board no longer existed, one (815 postings) had only older
  roles for other countries, and one careers page had a current posting with
  no publication date. That is a normal run.
