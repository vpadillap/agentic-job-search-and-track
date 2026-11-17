## Why

LinkedIn is the only job site so far, and for a user in Peru it misses much of
the local market. Bumeran Perú is one of the largest Peruvian job boards. Its
site is a JavaScript application: the HTML has no postings, and the data comes
from a JSON API that Cloudflare's firewall refuses to anything that is not a
real browser (plain HTTP got 403 in the study, while a real Chromium visiting
the public pages got every answer). This change studies Bumeran and adds it as
the second provider, read through a real browser without an account.

## What Changes

- Add `providers/bumeran.md`, the binding recipe for Bumeran Perú:
  - access is a real Chromium driven by Playwright, logged out, with no
    account, no saved cookies, and no user browser; it opens only the public
    search page (`/empleos-publicacion-menor-a-<N>-dias-busqueda-<title>.html`)
    and each posting's public page (`/empleos/<slug>-<id>.html`), and reads the
    JSON those pages receive from the site (`api/avisos/searchV2` for the list,
    `api/candidates/fichaAvisoNormalizada/<id>` for each posting);
  - the site's own filters that the page puts in its URL: title and posting
    age (Bumeran's windows of 2 to 7, 15, and 30 days);
  - what Bumeran gives structured, which the agent no longer has to guess from
    the text: work mode, contract, seniority, publication date, a published
    salary range, and the application-form questions, which are visible
    without applying;
  - conservative pacing, a small page cap per title, and an immediate stop on
    a Cloudflare challenge or block, HTTP 403 or 429;
  - the terms-of-use risk stated plainly (Bumeran's terms, clause 1.5.1,
    forbid any software or agent other than the site's own search tools, and
    apply to visitors without an account).
- Explicitly forbid, in that file: requesting the API directly (curl, Python
  HTTP, a fetch tool), impersonating a browser's TLS fingerprint, reusing
  Cloudflare cookies, proxies or rotating identities, stealth plugins, the
  user's own browser or Bumeran account, and any application endpoint
  (`postularV2` and similar). Nothing is clicked on the page.
- New reader `jobtracker providers read bumeran <run_id> --title "<title>"`,
  like the LinkedIn reader: one title per call, drafts file in the run's
  capture folder, pacing kept across calls, one call at a time per run, seen
  postings not reopened, stop recorded on the run.
- Drafts carry the fixed fields and the form questions; the work mode, salary
  range, and language that Bumeran states are passed to the agent as hints,
  and the agent's reading still decides them (no change to the import).
- Optional dependency group `browser` (Playwright) so `/setup` can install it
  only for users who turn Bumeran on; `jt doctor` and the reader name the
  missing package or browser and how to install it.
- README and AGENTS status: Bumeran is the second available job site.

## Non-goals

- Plain-HTTP access to Bumeran's API, or any way of making a non-browser look
  like a browser. If the real browser is refused, the provider fails for that
  run and a new change revisits it.
- The user's Chrome, the browser extension, a live walk, or a Bumeran account.
- Clicking, applying, saving postings, or any write on Bumeran.
- Searching by location or other Bumeran filters (area, seniority, work mode):
  the agent's first-pass filter already applies the profile.
- Other Navent sites (Bumeran in other countries, Konzerta, Laborum,
  Multitrabajos): each gets its own change.
- Salary research from Bumeran's salary pages (`kind: jobs`).

## Capabilities

### New Capabilities

- `provider-bumeran`: how Bumeran Perú is searched and read: a real browser on
  the public pages, the site's own filters, the JSON the pages receive,
  pacing and stop conditions, field mapping including form questions, what
  the agent still reads, the terms-of-use risk, and what is forbidden.

### Modified Capabilities

None. The reader follows the existing `job-search` and `provider-recipes`
requirements (drafts with readings, provider dependencies, read-only
behavior).

## Impact

- New `providers/bumeran.md`; new `src/jobtracker/core/readers/bumeran.py`
  registered in `core/readers/__init__.py`.
- `pyproject.toml`: optional group `browser = ["playwright>=1.45"]` (already a
  dev dependency for the panel's browser tests).
- `job-search` skill: Bumeran's hints in the drafts; `setup` skill unchanged
  (it already installs a provider's `dependencies`).
- Tests with fictional JSON responses and a fake browser (no real requests in
  tests); one optional live check marked like the browser tests.
- No database change; no panel change.
- Runtime: only after the user turns Bumeran on, a search opens about 2 search
  pages plus one page per new posting per title on bumeran.com.pe, from the
  user's IP, in a visible Chromium window (Cloudflare blocked headless in the
  study).
