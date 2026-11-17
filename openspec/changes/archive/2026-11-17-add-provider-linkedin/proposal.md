## Why

`/job-search` works but has no job site to search. LinkedIn is the first site,
and the one that needs the most care: logged-in automation can get the user's
account restricted, and the logged-out `jobs/search` page shows a sign-in
pop-up and can push to a login screen when filters are clicked. This change
studies LinkedIn and adds its provider file, using an access method that never
touches the user's account.

## What Changes

- Add `providers/linkedin.md`, the binding recipe for LinkedIn:
  - access is plain HTTP, logged out, with no browser, no cookies, and no
    account: the guest search (`jobs-guest/jobs/api/seeMoreJobPostings/search`)
    for the list, and each posting's public page (`jobs/view/<id>/`) for its
    description, seniority, and contract type;
  - only the filters LinkedIn offers visitors (keywords, location, posting
    age, paging), sent in the URL; work mode and contract type are not
    filterable for visitors and are read from each posting instead;
  - the agent reads each posting's title and description to decide its work
    mode and to note how the posting describes it (for example, two days a
    week on site), using the work-mode detail added by
    `add-work-mode-detail`;
  - conservative pacing, a small page cap per title, and an immediate stop on
    throttling or any redirect to a login page;
  - the field mapping from LinkedIn's HTML to the posting record;
  - the terms-of-use risk stated plainly (LinkedIn's User Agreement covers
    logged-out visitors; its robots.txt disallows `/jobs-guest/`).
- Explicitly forbid, in that file, the logged-in session, the browser
  extension, Playwright, and the `jobs/search` page.
- Job sites are switched off until the user turns them on. Today a provider
  without a stored choice counts as enabled, so updating the repository would
  start searching a new site the user never chose. From now on a provider with
  no stored choice is disabled; `/setup` asks which sites to turn on, and the
  panel toggle and `jt providers enable` keep working. When no site is
  enabled, `/job-search` names the available sites and how to turn one on.
- Add a check that the repository's provider files are valid.
- Update the README and AGENTS status: LinkedIn is the first available job
  site.

## Capabilities

### New Capabilities

- `provider-linkedin`: how LinkedIn is searched and read: the logged-out guest
  search and posting pages, the visitor filters, pacing and stop conditions,
  field mapping, work mode read by the agent, and what is forbidden.

### Modified Capabilities

- `provider-recipes`: "Per-user provider state" changes: a provider the user
  has not turned on is disabled, so a provider added by an update never runs
  without the user's choice.

## Non-goals

- Logged-in access, live walkthroughs, browser automation, or any fallback to
  them. If these pages stop working, the provider fails for that run
  and the recipe is revisited in a new change.
- Reading application form questions (they are not visible without applying).
- Salary data from LinkedIn (`kind: jobs`).
- Proxies, rotating user agents, or anything meant to evade LinkedIn's limits.
- New application code for LinkedIn: no parser, fetch command, or new access
  method. The only code change is the off-by-default provider state.
- Other job sites; each gets its own change.

## Impact

- New file `providers/linkedin.md`; tests in `tests/test_providers.py`.
- `src/jobtracker/core/providers.py`: the default state of a provider without
  a stored choice becomes disabled. This reaches `jt providers list`,
  `jt context`, `jt run start`, `jt doctor` (dependency checks only for
  enabled providers), and the panel's provider toggles. Tests and fixtures
  that relied on providers being on by default turn them on explicitly.
- Skills: `/setup` step "Job sites" turns on the chosen sites instead of
  turning off the unwanted ones; `/job-search` explains how to turn a site on
  when none is enabled.
- Dependency: `curl`, which ships with Windows 10+, macOS, and most Linux
  distributions; `jt doctor` already reports it when it is missing.
- README and AGENTS status lines.
- Depends on `add-work-mode-detail` (applied and merged first).
- Runtime: only after the user turns LinkedIn on, `/job-search` sends up to
  about a hundred requests to linkedin.com per run from the user's IP.
