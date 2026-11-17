## Why

Indeed is the second job site the owner wants. The study of 2026-11-17 tried
every route with real requests, logged out:

| Route | Result |
|---|---|
| Plain HTTP (curl, urllib) to `pe.indeed.com/jobs?…` | 403, Cloudflare challenge ("Security Check") |
| Headless Chromium | 403, "Blocked - Indeed.com" |
| Official MCP connector (`mcp.indeed.com/claude/mcp`) added to Claude Code | sign-in completes, but the server refuses the session on every reconnect (three attempts, two client identities); it serves only claude.ai's own connector, which the user would have to set up by hand |
| Posting page `/viewjob?jk=…` in a visible browser | 401, sign-in page |
| **Visible Chromium, fresh profile: search page** | **200, 15 postings in the page's job-card JSON** (id, title, company, location, publication date, relative age, remote flag, job types, extracted salary) |
| **Same page, clicking a posting** | **complete description in the side panel** (1,621 and 3,423 characters for the two postings tried) |

The owner chose the last route: a visible, logged-out browser that reads the
search page and its side panel, as a person would. No stealth plugins, no
proxies, no tricks: the browser is an ordinary Chromium and Indeed's check
completes by itself. It is still automated access that Indeed's terms
(section 21) do not permit; the provider file says so before the user turns
it on, as for LinkedIn.

## What Changes

- New reader `jobtracker providers read indeed <run_id> --title "<title>"
  [--location "<place>"]`: opens a visible Chromium with a fresh profile
  (logged out by construction), searches the title on the Indeed site of the
  profile's country with the posting-age window, takes the postings from the
  page's job-card data, clicks each new posting and copies the description
  from the side panel, and writes drafts and raw captures to the run's
  capture folder. The agent reads the drafts and imports them with
  `--readings`, exactly as for LinkedIn.
- The same rules as the LinkedIn reader, shared: at least 5 seconds between
  actions, kept across calls; one call at a time per run; a posting stored by
  an earlier run is not opened again (recorded as seen); a job id is opened
  once per run; stop and record Indeed as blocked on a block page, a
  challenge that does not clear, or a sign-in page; stop with an error when
  the page no longer matches the reader.
- `providers/indeed.md`: access `playwright`, `dependencies: [playwright]`,
  no login, the recipe, fields, the terms-of-use risk, stop conditions, and
  pitfalls (headless is blocked; posting pages need a sign-in).
- The shared parts of the LinkedIn reader (run state, pacing, lock, seen
  postings, stop) move to a small common module used by both readers.
- Fix found on the way: `jt doctor` checked the tools of every provider that
  was never turned on, since providers became switched off by default. It now
  checks only providers the user turned on.

## Capabilities

### New Capabilities

- `provider-indeed`: how Indeed is searched and read, logged out, through a
  visible browser, and what is never done there.

### Modified Capabilities

None (the readings import and readers come from `add-linkedin-reader`; the
doctor fix restores what `provider-recipes` already requires).

## Impact

- New `src/jobtracker/core/readers/indeed.py` (Playwright imported only when
  it runs) and `readers/common.py`; `readers/linkedin.py` uses the common
  module; registry entry `indeed`.
- `providers/indeed.md` (new); `core/doctor.py` (enabled providers only).
- Tests with a fake browser and fictional pages; repository provider files
  valid; a real check with one title.
- Playwright and its Chromium are installed by `/setup` only when the user
  turns Indeed on.
