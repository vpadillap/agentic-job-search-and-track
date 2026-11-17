## Why

Following `providers/linkedin.md` by hand makes the agent download each
posting page (about 250 KB of HTML, measured 2026-11-17) and pull the fields
out itself, writing throwaway code every run. A real search (4 titles, up to
3 pages each, one page per posting) can mean 120+ pages: slow, expensive in
tokens, and less consistent than the dry run. The agent then retypes every
description into the import record, which costs output and risks changing the
text that must stay verbatim. The fixed part of the work (requests, pacing,
stop conditions, extracting title, company, date, description, seniority, and
contract) does not need judgment; only reading the work mode, its detail, the
language, and any salary in the text does.

## What Changes

- New command `jobtracker providers read linkedin <run_id> --title "<title>"
  [--location "<country in English>"]`: searches one title on LinkedIn's guest
  search, opens each new posting's public page, and writes a drafts file
  (import records with the fixed fields filled in) to the run's capture
  folder. It prints a short summary with the drafts file path. Python's
  standard library only (verified with real requests: same answers as curl);
  `curl` is no longer a LinkedIn dependency.
- The reader applies the provider file itself: its pacing
  (`min_seconds_between_requests`, kept across calls of the same run), its
  page limit (`max_results_per_query`), the posting-age window, no redirects,
  and the stop conditions. On a block it records LinkedIn as failed for the
  run, and any later call in that run is refused.
- Postings LinkedIn already gave in an earlier run are not opened again: the
  reader records them as seen in this run from what is stored. Daily searches
  repeat many postings, so this means fewer requests to LinkedIn and less risk
  of being blocked. A job id is opened at most once per run across titles.
- `jobtracker postings import <run_id> <drafts> --readings <file>`: the agent
  sends only its reading of each draft (work mode, work-mode detail, language,
  flags, published salary), and the import merges it by job id. Every draft
  needs a reading. The description is never retyped by the agent, so it stays
  exactly as captured.
- `providers/linkedin.md`: the access method becomes the reader command; the
  manual curl recipe is removed (the request rules stay, as what the reader
  does), and the agent's part is the reading. Front matter: `dependencies: []`.
- A posting page that cannot be read (for example, removed) is left out and
  listed in the summary, instead of being imported with an empty description,
  which the import does not accept.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-linkedin`: LinkedIn is read through the system's reader (the
  agent never requests LinkedIn itself); pacing and stop conditions are
  enforced by the reader and hold across its calls; postings stored by an
  earlier run are not reopened; an unreadable posting page is reported, not
  imported.
- `job-search`: the import accepts the agent's readings merged into drafts
  made by a reader, so descriptions captured by a reader are never retyped.

## Impact

- New `src/jobtracker/core/readers/linkedin.py` (standard library: `urllib`,
  `html.parser`), `cli/main.py` (`providers read`, `postings import
  --readings`), `core/search.py` (merging readings).
- `providers/linkedin.md` rewritten around the command; `job-search` skill
  (import with readings).
- Tests with fictional HTML pages and a fake network (no real requests in
  tests).
- No database change; no panel change.
