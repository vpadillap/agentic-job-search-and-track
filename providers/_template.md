---
id: example                      # lowercase, matches the file name
name: Example Jobs
kind: jobs                       # jobs | salary | both
regions: [global]                # ISO country codes or "global"
access: playwright               # playwright | scrapling | http | web-search | live-walk
anonymous_only: true             # always true: never sign in or use the user's session
live_walk: false                 # true = the user must be present; skip in unattended runs
dependencies: []                 # e.g. [playwright], installed by /setup when this provider is enabled
max_results_per_query: 50
min_seconds_between_requests: 3
last_verified: 2026-01-01
---

# Example Jobs

## Access method

Which tool to use and why, as found by studying the live site as a logged-out
visitor. State explicitly what does NOT work (for example "plain HTTP requests
are blocked; use Playwright"). The site is always read without signing in and
without the user's cookies.

## Sign-in prompts and walls

What the site shows to anonymous visitors, when a sign-in prompt appears, how
to dismiss it if the content behind it is public, and when to stop and report
the provider as skipped. Never sign in.

## Search recipe

1. URL pattern or UI steps, with placeholders for title, location, work mode,
   contract type, and posting age in days.
2. How to paginate and when to stop.

## Fields to extract

| Field | Where to find it | Notes |
|---|---|---|
| external_id | | stable id used for de-duplication |
| url | | canonical link to the posting |
| title / company / location | | |
| work_mode / contract_type | | map to: remote, hybrid, onsite / full-time, part-time, contractor |
| posted_at | | convert relative dates to absolute |
| description | | verbatim, do not summarize |
| published_salary | | only if the posting states it |

## Application form questions

How to see the application questions without submitting anything, or "not
visible without applying".

## Salary data (kind: salary | both)

Where salary reports are found, which filters make a report comparable, and
what to record as evidence (source, URL, sample size, date).

## Limits and etiquette

Pacing, daily caps, terms-of-use constraints. Never submit applications, send
messages, or change anything in the user's account.

## Known pitfalls

Things that broke before and how to recognize them.
