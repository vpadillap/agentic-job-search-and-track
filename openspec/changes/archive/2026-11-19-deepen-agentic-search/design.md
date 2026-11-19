## Context

Every other provider has a reader: code that requests its site exactly as the
provider file says and writes drafts. The agentic web search has none: the
agent discovers with a web-search tool and reads with `curl` and its own
copy-paste. A run on 2026-11-18 (Peru, 15 commercial and marketing titles)
imported nothing: discovery found mostly aggregator and job-board listings,
`curl` got `403` from a national job board with no provider file, and
JavaScript careers pages showed no openings. Greenhouse already uses the
split this change adopts: the agent finds links, the reader reads them
(`--found`). Glassdoor's reader already parses JSON-LD `JobPosting` and turns
HTML into plain text (`readers/glassdoor.py`: `_json_ld`, `parse_posting`,
`plain_text`). A parallel change (`retry-soft-blocks-and-browser-choice`) is
editing `readers/common.py`; this change uses it as it is.

## Goals / Non-Goals

**Goals:** more company and ATS postings per title; JavaScript pages read;
descriptions taken from the page by code, never retyped; the original posting
preferred over copies; sites with their own provider refused in code;
politeness (`robots.txt`, per-host pacing) enforced in code.

**Non-Goals:** reading search-engine result pages; getting past refusals;
reading provider sites; signing in or applying; studying or adding a national
job board (its own change).

## Decisions

### D1. The agent discovers, the reader reads

```
jt providers read agentic-search <run_id> --title "<title>" --found <file>
```

`--found` is a JSON list; each item is a link, or an object
`{"url", "found_via", "lines": [first, last], "synonym": true}` (`lines`
and `synonym` only for a page this run already captured: D5, D4). The reader writes
drafts and a summary; the agent adds its reading (work mode, flags…) and
imports with `jt postings import`, as for every reader.

*Alternatives:* a `--url` flag per page (one process per link: no shared
pacing, robots cache, or dedupe across a title; rejected); the reader also
discovering by requesting search-engine pages (forbidden by their terms,
answered with challenges; rejected); keeping `curl` (no JavaScript, no
dedupe, no domain check; rejected).

### D2. What the reader refuses before any request

1. **Provider domains.** New optional front-matter field `domains: [...]` in
   provider files (hosts, matched with their subdomains). The reader refuses a
   link whose host belongs to any provider other than `agentic-search`,
   built-in or private, enabled or not. Refused links are listed in the
   summary (`refused: provider_domain`). Every built-in file gets its domains
   (from today's "Sites you never read here" table).
2. **`robots.txt`.** Fetched once per host per run (cached in the capture
   folder), read with `urllib.robotparser` for the reader's user agent
   `jobtracker` and `*`. A disallowed path is refused (`refused: robots`). An
   unreachable `robots.txt` (network error, `5xx`) refuses the host for the
   run; a `404` allows it, as the standard says.
3. **Non-pages.** Only `http`/`https`; no links to sign-in, apply, or account
   paths (`/login`, `/signin`, `/apply`, `/account`, `/register`…) on any host.

*Alternatives for domains:* keep the table in the Markdown only (the agent
must remember it; private providers are missed; rejected); derive hosts from
reader modules (private providers without readers missed; rejected).

### D3. Fetch: plain HTTP first, a plain headless browser when needed

- Plain HTTP (stdlib), honest user agent
  `jobtracker (local job-search assistant; +reads public job postings)`,
  `Accept-Language` from the posting country's language and English.
- A page "needs a browser" when it answers `200` with no `JobPosting` data and
  less visible text than a posting (threshold in code, tested), or with a
  known JavaScript shell (an empty `#root`/`#app`, `noscript` asking for
  JavaScript). Then, if Playwright is installed, the reader renders it once in
  headless Chromium (no cookies kept, no sign-in, same user agent suffix,
  waits for network idle with a time limit) and uses the rendered HTML.
- Without Playwright: the page is reported `needs_browser` and the summary
  says how to install it (`jt providers install agentic-search`).
- **Refusals**: `401`, `403`, `429`, or a challenge page (captcha, "verify you
  are human", Cloudflare interstitial) refuse the **host** for the rest of the
  run (`refused: site_refused`). No retry with a browser, no other user agent.
  A refused host that is a job board (listing many companies' postings) is
  reported as `suggest_provider` so the agent offers `/add-provider`.
- Pacing: at least `min_seconds_between_requests` (raised to the readers'
  common minimum, 5) between two requests to the same host, kept in the run's
  state file so it holds across calls; one call at a time per run
  (`common.lock`). At most `max_results_per_query` pages read per call.
- Every page is saved: `agentic-search-<n>.html` (raw or rendered) and
  `agentic-search-<n>.txt` (URL on the first line, then numbered plain-text
  lines).

*Alternatives:* Scrapling stealth (made to get past automated checks;
appropriate only for a site studied in its own change; rejected); the user's
Chrome through the browser extension (needs the user present; stays a manual
fallback in the recipe, not the reader); always the browser (slow, heavier
on sites; rejected).

### D4. Extraction: JSON-LD first, verbatim

- `JobPosting` JSON-LD (reusing Glassdoor's parser, moved to a small shared
  helper if needed without changing Glassdoor's behavior): title,
  `hiringOrganization.name`, `jobLocation`, `datePosted`, `validThrough`,
  `employmentType`, `baseSalary` (as a hint), `description` turned into plain
  text with lines kept, `url`, `identifier`.
- `validThrough` in the past, or a page saying the posting is closed
  ("no longer accepting", "ya no está disponible"…), drops the posting
  (`closed`).
- Draft fields: `provider`, `external_id` and `url` (canonical: JSON-LD `url`
  or `<link rel=canonical>` when on the same company or ATS host, else the
  fetched URL; tracking parameters `utm_*`, `ref`, `source`, `gh_src`, `lever-
  source`… removed), `source_site`, `title`, `company`, `location`, `country`
  only when the location is in the profile's country, `posted_at` only from
  the page, `description`, `contract_type` only from `employmentType`.
- Title check: `common.title_matches`. A page whose posting title does not
  match is reported `other_title` with that title and not drafted. When the
  agent judges it a synonym of the searched title (for example "Ejecutivo de
  Cuentas Clave" for "Key Account Manager"), it passes the link again with
  `"synonym": true`; the reader then drafts it from the capture, with no new
  request.

*Alternatives:* LLM-side extraction from the saved page (the problem today;
rejected); readability-style heuristics (unreliable boundaries; replaced by
D5).

### D5. Pages without structured data: the agent points, the reader cuts

A page with no `JobPosting` comes back as `{"status": "no_structured_data",
"text_file": "agentic-search-<n>.txt", "lines": <count>}`. The agent reads
the numbered text, decides where the posting starts and ends, and passes the
same URL again with `"lines": [first, last]` plus the title and company it
read. The reader takes those lines from the capture (no new request) and
writes the draft. The description is therefore always the page's own text.

*Alternatives:* the agent pastes the description into the draft (retyping;
rejected); automatic boundary detection (wrong on navigation-heavy pages;
rejected).

### D6. Careers listings

- **Lever** (`jobs.lever.co/<company>`) and **Ashby**
  (`jobs.ashbyhq.com/<org>`): read through their public posting APIs
  (`api.lever.co/v0/postings/<company>?mode=json`,
  `api.ashbyhq.com/posting-api/job-board/<org>`), filtered by title and the
  profile's country or remote for it, each kept posting turned into a draft
  from the API's text.
- **Any other listing page** (a company careers page, Workday, SmartRecruiters,
  Workable…): the reader returns `candidate_links`: links on the (rendered)
  page whose text matches the title, same host or a known ATS host. The agent
  passes the ones it wants back with `--found`.

*Alternatives:* APIs for every ATS (more code and terms to check per ATS;
later changes can add them); crawling a careers site (unbounded; rejected).

### D7. Originals over copies

- **Pointer**: when a page's JSON-LD `url`, canonical link, or apply link
  points to a company or ATS host other than the fetched host, the reader
  reads that original instead (within the call's page limit), and records the
  first page as a copy.
- **Same posting, several sources in one run**: drafts are grouped by
  normalized company and title (`common.words`) plus location; the draft from
  the best source is kept (company's own host > ATS host > other site), the
  others are listed under `copies` in the summary. A kept draft from a site
  that is neither company nor ATS gets the flag "found on <site>, not on the
  company's own page" as a suggestion for the agent.
- The import's own seen/duplicate checks still apply across runs.

### D8. Discovery recipe (provider file, not code)

Per title, query families, each in the posting language of the profile's
country and in English where usual, up to **12 searches per title** (budget
stated in the file):

1. Title variants: the profile's title, its local-language synonyms and common
   variants (for example "Key Account Manager" / "Ejecutivo de cuentas clave"
   / "KAM"), each with city or country.
2. ATS `site:` queries: Lever, Ashby, Workday (`myworkdayjobs.com`),
   SmartRecruiters, Workable, BambooHR, Teamtailor, Recruitee, Breezy.
3. Careers phrases: "trabaja con nosotros", "únete a nuestro equipo",
   "careers", "vacantes" with the title.
4. **Sector employers**: once per season, the agent builds a list of the
   leading employers in the profile's sector and country (from public lists,
   with links) and records them with `jt companies record`; each run then
   revisits them first (they become "known companies").

Any web-search tool the agent has may be used, and more than one when
available (a second engine catches what the first misses); never the
search-engine pages through the reader. Results on provider domains are
dropped; aggregator results are used only to find the original.

### D9. Effort and reporting

Stops per title unchanged (40 postings, 15 companies). The summary counts
pages read, refused (by reason), `needs_browser`, `no_structured_data`,
`closed`, `other_title`, copies, and `suggest_provider` hosts; the agent puts
them in the run report.

## Risks / Trade-offs

- A plain headless browser is still automated access; the per-site terms are
  not read for every company page. Mitigation: `robots.txt`, honest user
  agent, per-host pacing, refusals end the host, public pages only.
- Playwright is about 150 MB with Chromium; it stays optional.
- Discovery quality still depends on the agent's web-search tools; the
  sector-employer list is the part that does not.
- Adding `domains` to provider files touches every provider file; the field is
  optional, so private providers without it stay valid (their hosts are then
  only refused by the recipe, and `jt providers validate` warns).

## Migration Plan

No data migration. Existing runs are unaffected. Provider files without
`domains` stay valid.

## Open Questions

None. The owner approved both recommended answers on 2026-11-19 (job boards
without a provider file are used to find originals and offered to
`/add-provider` when they refuse; plain headless Playwright for JavaScript
pages).

## Implementation notes

- Playwright is listed as the provider's dependency but stays optional: the
  provider file tells the agent to search anyway without it, and the reader
  reports `needs_browser` pages.
- For Lever and Ashby, the API gives no company name; the draft's company is
  the board's name, as Greenhouse does.
- A posting drafted in an earlier call of the run is not drafted again from
  another source (`copies`): drafts already written cannot be withdrawn,
  since every draft needs a reading at import.
- Pages already captured in the run are reused (second passes with `lines`
  or `synonym`, or the same link again) with no new request.
