---
id: indeed
name: Indeed
kind: jobs
regions: [global]
access: scrapling
requires_login: false
live_walk: false
dependencies: [scrapling]
max_results_per_query: 60
min_seconds_between_requests: 5
last_verified: 2026-11-18
---

# Indeed

## Access method

**Headless Scrapling stealth sessions**, logged out: no cookies, no account,
no sign-in, no window. Every Indeed page is opened by the reader command,
never by you:

```
jt providers read indeed <run_id> --title "<title>" --location "<place>"
```

The reader uses Indeed's search pages and nothing else. It takes the
postings from the job-card data each page embeds, clicks each new posting,
and copies its description from the side panel that opens next to the list.

**One page per search, so several searches per title.** Logged out, Indeed
serves only the first results page of a search: the second answers "Security
Check" (403) to a normal browser and a sign-in page to Scrapling (studied
2026-11-18). So the reader loads the first page of several variants of the
same search (relevance, sorted by date, last day, the other place, remote,
last 3 days), each in a fresh session; together they give about three times
what one page gives (44 against 15 for a broad title in Peru).

No account is involved, so getting past Indeed's automated check puts no
account at risk. If Scrapling is missing, run `jt providers install indeed`
(`/job-search` does it for the user).

Forbidden, without exception and without fallback:

- opening Indeed yourself (curl, a script, a fetch tool, a browser, the
  browser extension): only the reader opens Indeed;
- the user's Indeed account, session, or browser, and signing in;
- posting pages (`/viewjob?jk=…`): logged out they ask to sign in or take
  minutes under Scrapling;
- Indeed's MCP connector: it refuses sessions from Claude Code (tried
  2026-11-17), so it is not an option here.

If the reader reports that Indeed stopped (see "Stop conditions"), do not try
another way: tell the user what it said.

## Search recipe

For each title in the run's `titles`, one call, then import, then the next
title. **One title at a time, never in parallel** (the reader refuses a
second call while one is running: `reader_busy`).

1. Run the reader:
   `jt providers read indeed <run_id> --title "<title>" --location "<place>"`.
   `<place>` is where the profile's user wants to work, written as Indeed
   expects it (a city: `Lima`, `Arequipa`); leave `--location` out to search
   the whole country. The Indeed site is chosen from the profile's
   `country` (`PE` → `pe.indeed.com`, `US` → `www.indeed.com`). No window
   opens. A title takes from one minute (few results) to about ten (many
   results: several first pages and a click per new posting).
2. Read the summary (`read`): `new`, `already_seen` (stored by an earlier
   run, recorded as seen without clicking them), `outside_window`,
   `duplicate_in_run`, and `stopped`.
3. If `drafts_path` is set, read that file, decide each draft's reading (see
   "Fields to extract"), write all readings into one JSON list in the capture
   folder (for example `<capture_folder>/indeed-readings-1.json`), and import:
   `jt postings import <run_id> <drafts_path> --readings <readings file>`.
   Never copy or retype a description.
4. If `stopped` is set, stop Indeed for this run: the reader already recorded
   it as failed and refuses further calls in this run. Import what it wrote
   before stopping, then go on with the next provider.

When every title is done and Indeed did not stop, record
`jt run provider <run_id> indeed --status ok`.

### What the reader does

- First pages, each in a fresh session, in this order:
  1. relevance: `https://<cc>.indeed.com/jobs?q=<title>&l=<place>&fromage=<days>`;
  2. sorted by date (`&sort=date`);
  3. last day (`fromage=1`);
  4. the whole country (no `l`), when a place was given;
  5. remote (`l=remoto`);
  6. last 3 days (`fromage=3`), when the window is longer.
- It stops when 60 postings are reached, when it has met as many postings as
  Indeed's own total for the search, or when two variants in a row show
  nothing new. A sign-in or security page on a variant after the first ends
  the title (`ended_early` in the summary), not Indeed: the next titles are
  still read.
- `fromage`, the posting age: the smallest of 1, 3, 7, or 14 days that covers
  the run's window (more than 14 days uses 14; the import drops older
  postings).
- At least 5 seconds between any two page loads or clicks, also between one
  call and the next.
- Each posting is clicked once per run; postings stored by an earlier run
  and postings outside the window are never clicked.
- Search pages are saved as `indeed-<n>.html` and descriptions as
  `indeed-<n>-<job>.txt` in the capture folder (audit); drafts as
  `indeed-drafts-<n>.json`. The summary lists each variant with the postings
  it added (`variants`) and Indeed's total (`site_total`).

## Fields to extract

The reader fills in these fields; you never change them:

| Field | Source |
|---|---|
| external_id | the card's job key (`jobkey`) |
| url | `https://<cc>.indeed.com/viewjob?jk=<jobkey>` (opens for a signed-in user) |
| title, company, location | the card, as shown |
| country | the profile's country (ISO code) |
| posted_at | the card's publication date |
| description | the side panel, complete, as plain text: lines kept, spaces collapsed, never summarized or translated |
| contract_type | `job_types`, only when they say it plainly (see below) |

Three more fields in each draft are for you to read, not to import:
`job_types` (Indeed's own words, such as "Indefinido", "Medio tiempo",
"Contrato por obra"), `remote_hint` (Indeed's remote marker), and
`salary_shown` (a pay figure on the card, with its period).

Your reading of each draft:

| Field | What to decide |
|---|---|
| work_mode | `remote`, `hybrid`, or `onsite`, from the title and the complete description; `remote_hint` alone is not enough; `null` when not stated |
| work_mode_detail | how the posting describes the arrangement when it says more than the mode, in the posting's language, close to its words, at most 200 characters; `null` otherwise |
| language | the posting's language (`es`, `en`…) |
| flags | doubts for the user, in the panel language: "work mode not stated" when it applies; the `job_types` when they are not clearly full-time, part-time, or contract; any other doubt |
| published_salary | when the description or `salary_shown` states a pay figure for this job: `{min, max, currency, period, basis}`; Indeed Peru shows soles (`PEN`); `null` otherwise |

The reader fills `contract_type` only when `job_types` says it plainly
("Tiempo completo"/"Full-time", "Medio tiempo"/"Part-time", "Contract",
"Freelance"); otherwise it is empty, and when the description says it, add it
as a flag (a reading cannot set `contract_type`).

### Work mode

Decide it as for every site: only when the title or the description says so.
Words in a benefits list, in the company's general description, or about
technology ("hybrid cloud") do not count. When neither says where the work
is done, leave both `null` and add the flag "work mode not stated" (in the
panel language). Such a posting is never excluded for its work mode.

## Application form questions

Not visible without applying. Never click "Postularse" / "Apply" or any
apply link.

## Limits and etiquette

- **Terms of use.** Indeed's Terms (section 21, last updated 2026-09-29)
  forbid using "any automated system (bots, scrapers, spiders, AI or Agentic
  AI)" to access the site without written permission, except crawling as its
  robots.txt allows; robots.txt allows the search pages (`/jobs?…`) and
  disallows posting pages for generic bots. The reader uses no account, but it
  is automated access that Indeed does not permit, and it gets past Indeed's
  automated check on purpose. The realistic consequence is that Indeed blocks
  requests from the user's IP address for a while. Tell the user this before
  they turn Indeed on.
- At least 5 seconds between actions; at most 60 postings per title; each
  posting clicked once per run.
- Read-only: never apply, save, follow, message, or sign in.

### Stop conditions

The reader stops **all** Indeed work for the rest of the run, keeps what was
already read, records Indeed as failed for the run, and refuses later calls
in that run when:

- the **first** page of a title answers 403 or 429, or its title is a block
  or security check ("Blocked - Indeed.com", "Security Check", "Un
  momento…"), or a sign-in page appears instead of results: reason `blocked`
  (on a later variant the same page only ends that title);
- a search page has no job-card data, or a clicked posting shows no
  description: reason `error`, with what is missing;
- the browser itself fails: reason `error`.

A search page whose job-card data has no postings simply has no results for
that title.

## Known pitfalls

- **Plain headless is blocked.** A plain browser without a window gets
  "Blocked - Indeed.com" (403); plain HTTP gets a Cloudflare challenge.
  Scrapling's stealth session passes (2026-11-18).
- **No second page logged out.** `start=10` answers "Security Check" (403) to
  a normal browser and a sign-in page to Scrapling; the reader uses other
  first pages instead.
- **Posting pages ask to sign in.** `/viewjob?jk=…` answers 401 with
  "Iniciar sesión | Cuentas Indeed" when logged out; the description is read
  from the search page's side panel instead.
- **Stale panel.** After a click the panel can briefly still show the
  previous posting; the reader waits for the address to name the clicked
  posting and for the text to change.
- **Job types are local words** ("Indefinido", "Medio tiempo"): read them, do
  not map them blindly.
- **Relevance order** by default; the date-sorted variant adds the newest.
