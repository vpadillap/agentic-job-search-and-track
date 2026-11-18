## Why

Glassdoor is the next job site the owner wants, a global site (`regions:
[global]`) next to LinkedIn and Indeed. A first study on 2026-11-18, logged
out, searching "data engineer" in Peru with a 7-day window:

| Route | Result |
|---|---|
| Plain HTTP (curl) to `/Job/jobs.htm?…` and the SEO search URL | 403, "Security \| Glassdoor" page |
| Headless Chromium | 403, "Un momento…" challenge |
| Calling the site's internal endpoints from the page (location lookup) | 404 / 403, and the next page load was challenged; **not used** |
| **Visible Chromium, fresh profile: search URL** | **200**, 30 postings per page in the page's embedded data (`jobListings[].jobview.header`: id, title, company, location, age in days, salary, extracted attributes such as full-time and hybrid) |
| **Same page, clicking a card** | **complete description in the side panel** (3,983, 2,970, and 5,375 characters in three tries); it loads a moment after the click |
| After one or two clicks | a "Never Miss an Opportunity" sign-up modal; **Escape closes it** and it did not return in that run |

Search URL: `https://www.glassdoor.com/Job/<place>-<title>-jobs-SRCH_IL.0,<n>_IN<locId>_KO<a>,<b>.htm?fromAge=<days>`,
where `locId` is Glassdoor's country id (Peru = 189, Portugal = 195); the
plain form `/Job/jobs.htm?sc.keyword=<title>&locT=N&locId=<id>` redirects to
it. `fromAge=7` cut the Peru results from 143 to 11.

Glassdoor's `robots.txt` excludes AI crawlers (ClaudeBot, anthropic-ai, …).
The owner decided it does not apply: this tool is not a crawler; it reads
pages for one user, as Indeed's reader does. Glassdoor's terms of use still
forbid automated access; the provider file says so before the user turns it
on, as for LinkedIn and Indeed.

## Still to confirm in this change (before implementing the reader)

1. Reading every posting of a page in a row (at least 10) with the modal
   closed by Escape: does the modal come back, does a hard sign-in wall
   appear, after how many postings?
2. Pagination: how the second page is reached and whether it stays logged out
   without a wall.
3. How the reader finds `locId` for a country other than Peru without calling
   internal endpoints (the site's own search box set `locId=189` for "Peru").
4. Whether the side-panel description is the complete text (compare with the
   card's snippet and the posting's length) and what the posting link should
   be.

The results are written into this proposal and the design, and the owner
approves them before the reader is built.

### Study log

**2026-11-18, point 1 (one results page in a row).** Peru, "data engineer",
7 days: 11 results, 8 cards rendered. Seven postings read in a row with
complete descriptions (2,241–7,190 characters). The sign-up modal appeared
once, after the second posting; Escape closed it; it did not return. No
sign-in wall.

The eighth posting (one employer) never loaded its description: the panel
showed its header and skeleton lines for more than 40 seconds, also when it
was the first posting opened in a fresh session. So it is that posting, not
throttling: the reader must skip such a posting with a note and continue,
not stop.

**2026-11-18, point 2 (more results), interrupted.** In the same browser
session, loading a second search URL with `page.goto` got the "Un momento…"
challenge, which did not clear. The same happened earlier in the day when a
second page was loaded directly after calls to internal endpoints. Open
question: is a second direct navigation in one session what triggers it, or
the number of study sessions from this IP today (about 20)? The study pauses
to let the IP cool down; the next probe moves to the next page or the next
title through the page itself (the site's search box and its own
"more results" control), not a second direct URL load.

## What Changes

- New reader `jobtracker providers read glassdoor <run_id> --title "<title>"`:
  a visible Chromium with a fresh profile (logged out by construction) opens
  the search URL for the profile's country and the run's window, takes the
  postings from the page's embedded data, clicks each new posting, closes the
  sign-up modal with Escape when it appears, copies the description from the
  side panel, and writes drafts and raw captures to the run's capture folder.
  The agent imports them with `--readings`, as for Indeed.
- Same shared rules as the other readers (`readers/common.py`): at least 5
  seconds between actions, one call at a time per run, a posting stored by an
  earlier run is not opened, stop and record Glassdoor as blocked on a block
  page, a challenge that does not clear, or a sign-in wall that Escape does
  not close; stop with an error when the page no longer matches the reader.
- `providers/glassdoor.md`: `regions: [global]`, access `playwright`,
  `dependencies: [playwright]`, no login, the recipe, fields, the terms risk,
  stop conditions, pitfalls (headless and plain HTTP are blocked; internal
  endpoints are not called; the modal).

## Capabilities

### New Capabilities

- `provider-glassdoor`: how Glassdoor is searched and read, logged out,
  through a visible browser, and what is never done there.

### Modified Capabilities

None.

## Impact

- New `src/jobtracker/core/readers/glassdoor.py` (Playwright imported only
  when it runs); registry entry `glassdoor`.
- `providers/glassdoor.md` (new).
- Tests with a fake browser and fictional pages; a real check with one title.
- Playwright and its Chromium are installed by `/setup` only when the user
  turns Glassdoor on (already the case for Indeed and Bumeran).
