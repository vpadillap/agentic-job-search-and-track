---
id: bumeran
name: Bumeran Perú
kind: jobs
regions: [PE]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
domains: [bumeran.*]
max_results_per_query: 40
min_seconds_between_requests: 5
last_verified: 2026-11-18
---

# Bumeran Perú

## Access method

A headless Scrapling stealth session (a real Chromium with no window), driven
by the reader command, logged out: no account, no saved cookies, not the
user's own Chrome. Every Bumeran page is
opened by the reader, never by you:

```
jt providers read bumeran <run_id> --title "<title>"
```

Bumeran's pages are a JavaScript application: the HTML has no postings, and
the data comes from the site's own API, which Cloudflare refuses to anything
that is not a real browser. The reader opens two kinds of public page and
keeps the data the site sends to them:

1. **Search results** for one title and posting age:
   `https://www.bumeran.com.pe/empleos-publicacion-menor-a-7-dias-busqueda-data-engineer.html`
   (the page receives `api/avisos/searchV2`, 20 postings per page).
2. **One posting**: `https://www.bumeran.com.pe/empleos/<id>.html` (the site
   moves to the posting's canonical address, and the page receives
   `api/candidates/fichaAvisoNormalizada/<id>`: the complete description and
   the application-form questions).

**No window opens.** A plain headless browser is blocked by Cloudflare;
Scrapling's stealth session gets the same pages a normal window gets (studied
2026-11-18: the search data and each posting's data, with complete
descriptions). No account is involved, so getting past the automated check
puts no account at risk. If Scrapling is missing, run
`jt providers install bumeran` (`/job-search` does it for the user).

Forbidden, without exception and without fallback:

- requesting Bumeran yourself (curl, a script, a fetch tool, a browser):
  only the reader opens Bumeran pages;
- calling Bumeran's API directly, from anything: the reader only keeps what
  the pages it opens receive;
- the user's Chrome, the browser extension, or the user's Bumeran account;
- clicking anything on Bumeran, and any application request (`postularV2`
  and similar): the reader cancels them even if a page tries.

If the reader reports that Bumeran stopped (see "Stop conditions"), do not
try another way: tell the user what it said.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel**: the pause between pages
only holds when calls follow one another, so the reader refuses a call while
another one for the same run is still running (`reader_busy`). Wait for the
call to finish; never remove its lock file.

1. Run the reader: `jt providers read bumeran <run_id> --title "<title>"`.
   Bumeran searches all of Peru; no location is sent (the first-pass filter
   applies the profile's places). A call takes a few minutes (a session
   start, then at least 5 seconds and about 14 seconds per page).
2. Read the summary it prints (`read`): `new`, `already_seen` (stored by an
   earlier run, recorded as seen without opening them again),
   `outside_window`, `duplicate_in_run`, `unreadable` (closed or empty
   postings: not imported; mention them to the user), `unknown_questions`
   (questions of a shape the reader does not know, imported as plain text),
   and `stopped`.
3. If `drafts_path` is set, read that file and write one reading per draft
   (see "Fields to extract") into one JSON list in the capture folder, for
   example `<capture_folder>/bumeran-readings-1.json`:

   ```json
   [{"external_id": "900001", "work_mode": "hybrid",
     "work_mode_detail": "Híbrido: 3 días en oficina", "language": "es",
     "flags": [], "published_salary": null}]
   ```

4. Import the drafts with the readings:
   `jt postings import <run_id> <drafts_path> --readings <readings file>`.
   Every draft needs exactly one reading; a reading may only set
   `work_mode`, `work_mode_detail`, `language`, `flags`, and
   `published_salary`. Never retype a description; the form questions are
   imported from the draft.
5. If `stopped` is set, import the drafts it wrote before stopping, then:

   - reason `throttled`: Bumeran is cooling down until `resume_after`. Go on
     with the next provider and tell the user when Bumeran may go on. After
     that time, if the user wants to wait, call it again in this run for
     the titles not done yet; a call before then is refused with
     `provider_cooling` and sends nothing. If the run is finished first,
     Bumeran is recorded as failed with reason `throttled`.
   - any other reason: stop Bumeran for this run. The reader already
     recorded it as failed and refuses further calls in this run; go on with
     the next provider.

When every title is done and Bumeran did not stop, record
`jt run provider <run_id> bumeran --status ok`.

### What the reader does

Shown so that you and the user know exactly what happens; you do not do any
of this yourself.

- Search page: `https://www.bumeran.com.pe/empleos-<window>-busqueda-<title>.html`,
  where `<title>` is the title in lowercase without accents, words joined by
  hyphens, and `<window>` the smallest posting age Bumeran offers that covers
  the run's window:

  | Run window | `<window>` |
  |---|---|
  | 1–2 days | `publicacion-menor-a-2-dias` |
  | 3, 4, 5, 6 days | `publicacion-menor-a-<N>-dias` |
  | 7 days | `publicacion-menor-a-7-dias` |
  | 8–15 days | `publicacion-menor-a-15-dias` |
  | 16–30 days | `publicacion-menor-a-1-mes` |
  | more than 30 days | none: `…/empleos-busqueda-<title>.html` |

  Postings older than the run's window are skipped by the reader and, if
  any got through, dropped by the import.
- Page 2: the same address with `?page=2`; at most 2 pages per title
  (`max_results_per_query: 40`), fewer when there are fewer results.
- At least `min_seconds_between_requests` (5) between page loads, also
  between one call and the next.
- One posting page per posting per run, never for a posting stored by an
  earlier run or outside the window.
- The browser does not load images, fonts, or media, and never sends an
  application request. A fresh browser profile is used for every call and
  thrown away after it.
- What each page received is saved as `bumeran-<n>.json` in the capture
  folder (audit); the drafts as `bumeran-drafts-<n>.json`.

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | Bumeran's posting id |
| url | `https://www.bumeran.com.pe` + the posting's canonical address |
| title, location | as shown (location like "Lima, Lima") |
| company | as shown; "Confidencial" when the company is hidden |
| country | `PE` |
| posted_at | the posting's publication date (day-first on the site, stored as a date) |
| description | complete, as plain text: paragraphs and list items kept (one per line, with "• "), never summarized or translated |
| seniority | the site's level ("Senior", "Semi Sr", "Junior"…); empty for "Otro" |
| contract_type | the site's job type: Full-time → `full-time`, Part-time → `part-time`; empty for anything else (see `site_contract`) |
| form_questions | the application form's questions, in order: free-text questions as text, choice questions with their options. Read without applying |

Hints in each draft, for your reading (the import ignores them):

| Hint | Meaning |
|---|---|
| site_work_mode | what Bumeran states: `onsite` (Presencial), `hybrid` (Híbrido), `remote` (Remoto) |
| site_contract | Bumeran's job type and hiring type (for example "Full-time", "Indeterminado" or "Temporal") |
| site_salary | a salary range the posting publishes, as given (`min`, `max`, frequency, type), or null |
| asks_expected_salary | the application asks for the candidate's expected salary |
| closing_date | when the posting closes |

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | start from `site_work_mode` and check it against the title and description; when they disagree, follow the description and add a flag such as "Bumeran says remote; the description requires the office" |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode (days on site, area), in its language, at most 200 characters; `null` otherwise |
| language | the posting's language (almost always `es`) |
| flags | doubts for the user, in the panel language; a job type that is not full-time or part-time (from `site_contract`, for example "Contrato temporal"); a work-mode disagreement |
| published_salary | from `site_salary` or a figure in the description: `{min, max, currency, period, basis}`; Peruvian postings are usually monthly in PEN, but write only what the posting says; `null` when nothing is stated |

## Application form questions

Visible without applying: the posting's data lists them, and the reader puts
them in the draft (`form_questions`), so `/form-answers` can prepare answers.
The site also tells which option of a choice question the employer expects;
the reader never keeps it, because answers must be true, not tuned to pass a
screen. When `asks_expected_salary` is true, the application asks the
expected salary; `/form-answers` handles it like any salary question.

## Limits and etiquette

- **Terms of use.** Bumeran's terms (last updated 2026-10-01), clause 1.5.1
  "Usos prohibidos", forbid "el uso o intento de uso de cualquier máquina,
  software, herramienta, agente u otro mecanismo para navegar o buscar en
  este Sitio Web que sean distintos a las herramientas de búsqueda provistos
  por BUMERAN", and the terms apply to everyone who visits, with or without
  an account (clause 1.5.2 allows suspending users). This provider never
  involves the user's account, but it is still automated browsing that the
  terms forbid, and it gets past Cloudflare's automated check on purpose. The realistic consequence is that Bumeran (through
  Cloudflare) blocks the user's IP address for a while. Tell the user this
  before they turn Bumeran on.
- At least 5 seconds between page loads; at most 2 result pages per title
  and one posting page per posting per run; postings stored by an earlier
  run are not opened again.
- Read-only: never apply, save, report, follow companies, or sign in.
- **When Bumeran asks to slow down** (a soft block, see "Stop conditions"),
  the reader waits and sends the same request again: as long as the site's
  `Retry-After` header says when it sends one, otherwise 10–20 seconds, then
  20–40 seconds. At most 3 tries per request, never more than 2 minutes per
  wait, at most 6 retries per run. If that does not clear it, Bumeran cools
  down for 15 minutes (30 the second time, longer when the site asks) and
  the same run goes on after that; a third throttle in a run stops Bumeran
  for the run. There is no way to end a cool-down early.
- Waiting is the only answer to a block: never a proxy, a different IP, a
  changed or rotating user agent or headers, an account, cookies, or a fresh
  browser identity to get past it.

### Stop conditions

**Soft blocks** (a throttle: the site asks to slow down):

- a page or the site data answers HTTP 429, or a page is a Cloudflare
  challenge ("Just a moment…", "Un momento…") that was not passed.

The reader waits and retries as stated in "Limits and etiquette". When the
throttle does not clear, it ends the call with `stopped.reason: throttled`
and `resume_after` (the time it may go on), keeps what was already read, and
records a cool-down on the run; calls before that time are refused without
any request (`provider_cooling`). The first call after it goes on in the
same run: a title already completed is not searched again, search pages
already read are skipped, and postings already opened are not opened again
(a posting whose request was throttled is opened then).

**Hard blocks and errors.** The reader stops **all** Bumeran work for the
rest of the run, keeps what was already read, records Bumeran as failed for
the run, and refuses later calls in that run (`provider_stopped`) when:

- a page or the site data answers HTTP 403, or a page is a Cloudflare block
  page ("Attention Required!", "Access denied") instead of Bumeran: reason
  `blocked`;
- a page does not receive its data within 30 seconds, or the data no longer
  has the expected shape, or page 2 is not page 2: reason `error`, with what
  is missing;
- the browser cannot load a page: reason `error`.

A search with no results simply has no postings for that title.

## Known pitfalls

- **Plain headless is blocked.** Cloudflare answered 403 to a plain headless
  browser on every page (2026-11-17). Scrapling's stealth session passes
  (2026-11-18); if it is blocked too, the provider stops.
- **Plain HTTP is blocked.** curl and Python requests to `api/` get
  Cloudflare's "Sorry, you have been blocked" page, even with the same
  headers the site sends; the IP is not blocked by that (other pages still
  answer).
- **Empty HTML.** Search and posting pages downloaded without a browser are
  the same empty application shell; there is nothing to read in them.
- **Sitemap dates.** `sitemap_avisos_bum.xml` lists every open posting with
  the same date; it cannot be used to find recent postings.
- **Dates are day-first** ("16-11-2026"); the reader converts them.
- **A posting's data can arrive twice** on its page; the reader uses the first
  complete answer.
- **robots.txt** disallows `recientes=true`, `relevantes=true`, and the
  `localidades` parameter; the reader uses none of them.
