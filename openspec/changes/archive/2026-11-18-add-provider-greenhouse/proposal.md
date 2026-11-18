## Why

Many companies publish their openings through Greenhouse, an applicant
tracking system. Those postings often appear nowhere else, or appear first
there. The owner wants Greenhouse as a job site. Greenhouse has a public
job search for candidates (at least after signing in), and every company
using it has its own public job board. How Greenhouse should be read is not
known yet: it is decided by a study inside this change, as for every
provider.

## Study (first section of this change; nothing is built before it)

Logged out first, with real requests, scratch scripts only:

1. **Candidate job search.** Does Greenhouse's job search for candidates
   work logged out? Which URL, which filters (title, location, remote,
   posting age), how many results, how results and the posting text are
   delivered (embedded data, API calls seen by the page, HTML)? Plain HTTP,
   headless, and a visible Chromium are each tried, as for Indeed.
2. **If the search needs a sign-in.** Try it through the Claude in Chrome
   extension in the user's own Chrome, where the user signs in themselves:
   no password ever passes through Playwright or the agent. Record what the
   extension can read, how long it takes, and what the user must do. This
   would make the provider `requires_login: true` and `live_walk: true`.
3. **Company job boards.** Each company board
   (`job-boards.greenhouse.io/<company>`, and the public Job Board API at
   `boards-api.greenhouse.io/v1/boards/<company>/jobs`) is checked with a
   real request: is it public, what does it return (title, location, updated
   date, full description, application questions), what are its limits?
   How would the agent know which companies to read (the candidate search,
   web search, or the agentic-search provider)?
4. **Terms of use** of each route.

The results go into this proposal and the design with a table like the one
in `add-provider-indeed`, and the owner chooses the route before section 2
starts.

### Study log (2026-11-18, logged out, real requests)

| Route | Result |
|---|---|
| Candidate search `my.greenhouse.io/jobs/search?query=…`, plain HTTP | 302 to `/users/sign_in` |
| Same, visible Chromium | lands on the MyGreenhouse sign-in page ("Send security code", or continue with a Google/other account): **the candidate search needs a sign-in** |
| **Job Board API** `GET boards-api.greenhouse.io/v1/boards/<company>/jobs?content=true`, plain HTTP | **200, no sign-in, no challenge**, under 1.2 s: every current posting of the company with `id`, `title`, `location.name`, `offices`, `first_published`, `updated_at`, `language`, `company_name`, `absolute_url`, and the complete description (`content`, HTML, ~5,600–7,000 characters). Greenhouse 26 postings, Stripe 791, Airbnb 202 |
| `GET …/jobs/<id>?questions=true` | 200: the **application-form questions** (label, required, field types such as `input_text`, `textarea`, `input_file`, `multi_value_single_select`, with options), plus location and demographic questions |
| A company that has no board | 404 `{"status":404,"error":"Job not found"}` |
| Boards on the European subdomain (`job-boards.eu.greenhouse.io/<company>`) | the same API host serves them (`saasgroup`: the same 13 postings as its EU page); `boards-api.eu.greenhouse.io` does not exist |
| **Finding companies**: web search `site:job-boards.greenhouse.io "<title>" <city/country>` | finds boards of companies hiring for the title in the country (for "data engineer" Lima: thoughtworksreferral, launch2, topsort, santex, cookunity, coderoad, neoris); many results are old, but the API shows only current postings (thoughtworksreferral: 8 current postings in Peru/LatAm, e.g. "Lead Data Engineer, Lima"; neoris: board gone, 404) |

**Terms.** Greenhouse's Job Board API documentation (docs.greenhouse.io,
read 2026-11-18): "Job Board data is publicly available, so authentication is
not required for any GET endpoints." No rate limits or usage restrictions are
stated for GET; only submitting applications (POST, never done here) needs a
key. `my.greenhouse.io/robots.txt` allows everything.

**1.2, the candidate search signed in (2026-11-18)**, through Claude in Chrome
in the owner's own Chrome, where the owner was already signed in to
MyGreenhouse; read-only, no account data recorded:

| Observation | Detail |
|---|---|
| Search address | `my.greenhouse.io/jobs/search?query=<title>&location=<country>&location_type=country&country_short_name=<CC>` (plus coordinates the location box adds); filters for date posted, salary, work type, employment type |
| Results | cards across **all companies on Greenhouse**: title, company, work mode, locations, "Posted · <relative age>"; infinite scroll; "data engineer" in Peru: **48 postings** (Encora, Sezzle, Nortal, N-iX, Aspenview…), against about 7 boards found by web search |
| A card | opens a modal with the full description; the title links to the company's board posting, e.g. `job-boards.greenhouse.io/encora10/jobs/5283692007`; the card itself carries no link, so the board name is read from the modal |
| Through the public API | `encora10` / `5283692007`: the same posting ("Senior Data Engineer AWS", Peru, 2,974-character description, 9 form questions) |
| Delivery | the page is an Inertia app; the search is a page visit, no separate data request seen. The page data also holds the signed-in user's name and email (never read or stored) |

So the signed-in search is a far better **discovery** source (every company,
filtered by country), and the public API stays the source of each posting.
It needs the user signed in in their own Chrome and present (live walk), and
it uses the user's MyGreenhouse account, so an account is involved: pace like
a person, read-only, never apply or save. Everything below "What Changes" is the expected shape and is revised
after the study.

## What Changes

Route chosen by the owner after the study (2026-11-18): postings are read
through the **public Job Board API**; the boards to read are found by the
**MyGreenhouse candidate search** in the user's own Chrome when the user is
present and signed in, and by **web search** over Greenhouse's board
addresses otherwise.

- New reader `jt providers read greenhouse <run_id> --title "<title>"
  [--found <file>] [--place-words "<words>"]` (plain HTTP, standard library):
  reads the postings and boards the agent found plus the boards remembered
  for this user; keeps postings that match the title, the user's country (or
  remote for the user's region), and the run's window; writes drafts with the
  complete description and the application-form questions.
- Boards are remembered per user (`provider-settings/greenhouse.json`) and
  rechecked every run; a board that no longer exists is dropped.
- `providers/greenhouse.md`: `regions: [global]`, `access: http`, no login,
  no dependencies, the two discovery recipes (signed-in search with Claude in
  Chrome; web search), the country place words (Peru), fields, form
  questions, terms, stop conditions, pitfalls.

## Capabilities

### New Capabilities

- `provider-greenhouse`: how Greenhouse postings are found and read, and what
  is never done there.

### Modified Capabilities

None.

## Impact

- New `src/jobtracker/core/readers/greenhouse.py` and its registry entry;
  `--found` and `--place-words` on `jt providers read`.
- `providers/greenhouse.md` (new); `provider-settings/greenhouse.json` in the
  private home (already in `docs/workspace-layout.md`).
- Tests with a fake HTTP getter and fictional boards; a real check.
- No new dependency.
