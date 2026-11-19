## Why

The agentic web search (`providers/agentic-search.md`) is the provider that
finds openings job boards miss: postings on companies' own careers pages and
applicant-tracking boards. Today it is a recipe only: the agent discovers with
one web-search tool, about five queries per title, and saves pages with
`curl`. That is too thin for job seekers outside tech, whose openings are
rarely on Lever or Ashby and often sit on careers pages rendered with
JavaScript or behind sites that reject non-browser requests.

What happened in a real run (2026-11-18, generic description, no personal
data):

| Step | Result |
|---|---|
| Discovery (one web-search tool, ~5 queries per title, 15 commercial and marketing titles, Peru) | Mostly aggregator and job-board listing pages; few company or ATS pages |
| Saving pages with `curl` | `403` from a national job board with no provider file (`pe.computrabajo.com`); nothing readable |
| Careers pages rendered with JavaScript | No openings visible to a plain fetch; companies recorded as "not readable" |
| Import | 0 postings |

The recipe has three gaps: discovery asks too few and too similar questions;
reading has no browser, so JavaScript pages and pages that refuse `curl` are
lost; and the agent copies descriptions by hand from saved pages, which is
slow and error-prone for long texts.

Proving run of the new reader (2026-11-19, a throwaway workspace with the
fictional persona, one generic title, Peru; counts only):

| Links passed | Refused before any request | Refused by the site | Read | Drafted and imported |
|---|---|---|---|---|
| 11 (from two web searches: Lever, a national job board, Greenhouse, Indeed, aggregators, company pages) | 2 (other providers' domains) | 2 hosts (`403`, one at `robots.txt`; both offered for `/add-provider`) | 2 pages and 3 Lever API answers; 3 postings already closed; 1 page without structured data returned as numbered text; other titles listed | 1 (a Lever posting passed back as a title variant, complete description, imported without errors) |

## What Changes

- **A reader for the agentic web search**:
  `jt providers read agentic-search <run> --title "<title>" --found <file>`.
  The agent still discovers; the reader reads. For each link the agent found
  it checks the site may be read here (not a provider's domain, allowed by
  `robots.txt`), fetches it politely (plain HTTP first, a headless browser
  when the page needs JavaScript), saves it to the run's capture folder, and
  writes drafts with the posting text verbatim (JSON-LD `JobPosting` first).
  Pages with no structured data come back as numbered plain text; the agent
  points at the description's lines and the reader cuts them, so no
  description is ever retyped.
- **Careers listings**: Lever and Ashby boards are read through their public
  posting APIs; other careers pages return the links whose text matches the
  title, for the agent to pass back.
- **Copies and originals**: the reader follows a page's pointer to the
  original posting (JSON-LD `url`, canonical link, an apply link to an
  applicant-tracking board) and, within one run, keeps one draft per posting,
  from the most direct source, listing the copies it set aside.
- **Deeper discovery recipe** in `providers/agentic-search.md`: query
  families per title (local-language synonyms and the profile's own title
  variants; ATS `site:` queries; "trabaja con nosotros" / careers phrases; the
  careers pages of the leading employers of the user's sector in the user's
  country, remembered as companies), any web-search tools the agent has (more
  than one engine when available), more queries per title with an explicit
  budget.
- **Refusals are respected, not worked around**: a site that answers `403`,
  `429`, or a challenge page is not retried with a disguised browser; it is
  reported as refused. A job board that refuses (such as Computrabajo) is
  offered to the user as a new provider through `/add-provider`, where its
  own study decides how it may be read.
- **Provider files name their domains**: an optional front-matter field
  `domains` lists the hosts a provider owns; every built-in provider file gets
  it, and the agentic-search reader refuses those hosts (and those of the
  user's private providers) in code, instead of a table the agent must
  remember.
- `providers/agentic-search.md`: `access: web-search` (unchanged: discovery
  is still the agent's), `dependencies: [playwright]`
  (optional: without it the reader reads plain-HTTP pages only and says which
  pages needed a browser), `min_seconds_between_requests: 5` per host, new
  recipe, fields, pitfalls.

## Non-goals

- Scraping search-engine result pages (Google, Bing, DuckDuckGo) from the
  reader: their terms forbid it and they answer with challenges. Discovery
  stays with the agent's own web-search tools.
- Stealth browsing, rotating identities, or any other way past a site that
  refuses automated reading.
- Reading any site that has its own provider file, on or off.
- Reading a national job board in depth here. Such a board gets its own
  provider (`/add-provider`, its own study and change).
- Signing in, applying, filling or submitting forms, subscribing to alerts.
- Adding Computrabajo itself: that is its own change, if the owner wants it.

## Questions for the owner (answered 2026-11-19: both as recommended)

1. **Job boards without a provider file (Computrabajo and similar).**
   Recommended: the agentic search may use a posting found there only to find
   the company's original page; it imports from the board itself only if the
   page reads with plain HTTP or a normal headless browser; when the board
   refuses, the agent suggests adding it with `/add-provider` (a separate
   change). Alternative: forbid importing from any job board here, so every
   board must get its own provider first.
2. **Browser for JavaScript pages.** Recommended: plain Playwright Chromium,
   headless, honest user agent, installed with `jt providers install
   agentic-search`. Alternatives: the Scrapling stealth session other readers
   use (rejected here: stealth is for sites studied in their own change), or
   the user's installed Chrome through the browser extension (needs the user
   present; kept only as the agent's fallback when the user says so).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-agentic-search`: discovery families, a reader that reads found
  links politely and verbatim, originals over copies, refusals respected,
  domains of other providers refused in code.
- `provider-recipes`: provider files may name their domains.

## Impact

- `src/jobtracker/core/readers/agentic_search.py` (new) and its registry
  entry and `OPTIONS` in `readers/__init__.py`; tests with fictional pages in
  `tests/test_agentic_search_reader.py`.
- `src/jobtracker/core/providers.py`: optional `domains` field validated and
  returned by `jt providers list`; `providers/_template.md` documents it;
  every built-in provider file gains `domains`.
- `providers/agentic-search.md` rewritten; `last_verified` updated after a
  proving run.
- `readers/common.py` is used, not changed (a parallel change is editing it).
- The provider stays switched off for every user until they enable it.
