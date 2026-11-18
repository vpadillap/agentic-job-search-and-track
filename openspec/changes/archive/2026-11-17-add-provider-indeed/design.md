## Context

See the proposal's table for the study. Details used here:

- Search URL `https://<cc>.indeed.com/jobs?q=<title>&l=<place>&fromage=<days>`
  (`pe` for Peru; `www` for the United States). robots.txt allows `/jobs?…`
  for all agents and disallows `/viewjob` for generic bots; the reader never
  opens `/viewjob`.
- The page embeds `window.mosaic.providerData["mosaic-provider-jobcards"]`;
  `metaData.mosaicProviderJobCardsModel.results[]` has `jobkey`, `title`,
  `company`, `formattedLocation`, `pubDate` (epoch ms), `formattedRelativeTime`,
  `remoteLocation`, `jobTypes` (e.g. "Indefinido"), `extractedSalary`
  (`{min, max, type: MONTHLY…}`), `link`, `viewJobLink`; `metaData.loggedIn`.
  15 results on the first page.
- Each card's title link is `a.jcs-JobTitle[data-jk=<jobkey>]`; clicking it
  adds `&vjk=<jobkey>` and fills the side panel; the description is the text of
  `.simple-job-description-html` under the heading "Descripción completa del
  empleo".
- Headless Chromium gets "Blocked - Indeed.com"; a visible Chromium passes;
  `/viewjob` answers 401 with "Iniciar sesión | Cuentas Indeed".
- The official connector was tried and is refused outside claude.ai (see the
  proposal); it is not used.

## Goals / Non-Goals

**Goals:** Indeed postings with complete descriptions, logged out, with the
same pacing, stop rules, and draft/readings flow as LinkedIn.

**Non-Goals:** signing in; the user's own browser; anything that hides
automation; posting pages; applying.

## Decisions

### D1. A reader like LinkedIn's, with a browser adapter

`readers/indeed.py` exposes `read(paths, run_id, title, location)` with an
injectable browser adapter (`search(url) -> page`, `open(jobkey) -> panel
text`); the real adapter is Playwright (imported inside it), a visible
Chromium, a new context per call (no storage), locale of the country. Tests
use a fake adapter and fictional pages; parsing the job-card JSON is a pure
function.

### D2. Shared reader parts move to `readers/common.py`

Run state file per provider (`<provider>-state.json`: last action time,
counter, job ids handled, drafts), pacing, one-call lock (`<provider>.lock`,
stale after 30 minutes), the context checks on the run (running, provider
pending/ok, refused after a stop), seen-posting records from the database,
the drafts file, and recording a stop. `readers/linkedin.py` keeps its HTTP
and parsing and uses the common parts; its tests must pass unchanged.

### D3. Search parameters

Site: the profile's `country` → `<cc>.indeed.com` (`US` → `www`). `l`: the
`--location` the agent gives (the profile's city, as Indeed expects it, for
example "Lima"); omitted otherwise. `fromage`: 1, 3, 7, or 14, the smallest
that covers the run's window (larger windows use 14; the import drops older
postings). Pages: first page, then `start=10, 20…` while new job ids appear,
up to `max_results_per_query` postings per title (30).

### D4. Fields

`external_id` = jobkey; `url` = `https://<cc>.indeed.com/viewjob?jk=<jobkey>`
(what a signed-in user opens); title, company, `formattedLocation`; country
from the profile; `posted_at` = local date of `pubDate`; description = panel
text, spaces collapsed per line and at most one blank line; informational
`job_types`, `remote_hint` (`remoteLocation`), `salary_shown`
(`extractedSalary` as text). `contract_type` is left to the agent, since
Indeed's job types are local words ("Indefinido", "Medio tiempo").

### D5. Stop rules

Blocked (record `blocked`, refuse later calls): response 403/429, a page
title containing "Blocked" or "Security Check" after waiting, or a sign-in
page. Error (record `error`): no job-card data on a page that is not a "no
results" page, a card without its link, or a panel without the description
after clicking. A first page with no job-card results means no results.

## Risks / Trade-offs

- [A window appears on the user's screen for a few minutes per search] →
  Said in the provider file; one title per call.
- [Indeed changes the page] → The reader stops with `error` naming what is
  missing.
- [Visible browsers may also be challenged later] → Same stop rules; the
  provider is revisited in its own change.
- [Terms] → Stated before turning it on.

## Migration Plan

None: no schema change; Indeed starts switched off.

## Open Questions

None; pagination size and the date sort are confirmed in the real check.
