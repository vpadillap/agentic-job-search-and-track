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

**Not tried yet (1.2):** the candidate search through the user's own Chrome
(Claude in Chrome) with the user signed in to MyGreenhouse. It needs the
owner to sign in; whether it is worth it depends on the route chosen. Everything below "What Changes" is the expected shape and is revised
after the study.

## What Changes (expected; revised after the study)

- `providers/greenhouse.md`: `regions: [global]`, the access method the owner
  chooses, its recipe, fields, terms risk, stop conditions, pitfalls.
- A reader (`jt providers read greenhouse …`) if the chosen route is the
  candidate search or the public board API; no reader if the route is the
  browser extension (the agent follows the provider file step by step, as a
  live walk).
- Application-form questions are captured when the posting shows them without
  applying (Greenhouse boards usually list them).

## Capabilities

### New Capabilities

- `provider-greenhouse`: how Greenhouse postings are found and read, and what
  is never done there.

### Modified Capabilities

None expected.

## Impact

- `providers/greenhouse.md`; possibly `core/readers/greenhouse.py` and a
  registry entry; tests with fictional pages.
- If the extension route is chosen: no new dependency in Python;
  `dependencies: [chrome-extension]`, checked by `jt doctor`.
