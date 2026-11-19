## 0. Owner decisions

- [x] 0.1 Owner answers the proposal's two questions (job boards without a provider file; browser choice); both recommended answers approved on 2026-11-19

## 1. Provider domains

- [x] 1.1 `providers.py`: optional `domains` field (list of host names), validated; a warning (not a failure) when a non-agentic provider has none; returned by `jt providers list`
- [x] 1.2 `providers/_template.md` and `providers/CONTRIBUTING.md` document `domains`; every built-in provider file gets its domains
- [x] 1.3 Tests: valid, wrong type, missing (warning), subdomain matching, private provider's domains listed

## 2. Reader: fetching

- [x] 2.1 `readers/agentic_search.py`: `--found` parsing (links and objects with `url`, `found_via`, `lines`, `synonym`), registry entry and `OPTIONS` (`found`)
- [x] 2.2 Refusals before any request: provider domains, non-http schemes, sign-in/account/apply paths
- [x] 2.3 `robots.txt` per host per run (cached in the capture folder; `404` allows, unreachable refuses the host)
- [x] 2.4 Plain HTTP fetch with honest user agent; per-host pacing in the run state; page limit per call; `common.lock`
- [x] 2.5 Refused hosts (`401`, `403`, `429`, challenge pages) ended for the run; job-board hosts reported as `suggest_provider`
- [x] 2.6 "Needs a browser" detection; plain headless Playwright rendering when installed, `needs_browser` otherwise; `jt providers install agentic-search` installs and checks it
- [x] 2.7 Captures: `agentic-search-<n>.html` and numbered `agentic-search-<n>.txt` with the URL on the first line
- [x] 2.8 Tests with an injected getter and renderer and fictional pages: domain refusal, robots disallow, pacing per host across calls, 403 ends the host with no retry, JavaScript shell rendered / reported, page limit

## 3. Reader: extraction

- [x] 3.1 JSON-LD `JobPosting` drafts (own parser, also reading `@graph`; Glassdoor's `plain_text` reused, Glassdoor unchanged); canonical URL without tracking parameters; country only when the location is in the profile's country
- [x] 3.2 Closed postings dropped (`validThrough`, closed wording in en/es)
- [x] 3.3 Pages without structured data: `no_structured_data` with the text file; `lines` cuts the description from the capture without a request
- [x] 3.4 Title check with `common.title_matches`; `other_title` reported; `synonym` drafts from the capture
- [x] 3.5 Lever and Ashby boards through their public APIs; `candidate_links` for other listings
- [x] 3.6 Originals: follow structured `url`, canonical, or ATS apply link; one draft per posting per run by source rank; `copies` in the summary; the "found on <site>" flag
- [x] 3.7 Already-stored postings recorded as seen (`common.finish`)
- [x] 3.8 Tests with fictional pages built in `tests/test_agentic_search_reader.py`: JSON-LD posting, expired posting, plain page cut by lines, synonym, Lever and Ashby answers, generic careers page, aggregator copy with an ATS apply link, duplicate in one run, already stored

## 4. Provider file and recipe

- [x] 4.1 `providers/agentic-search.md`: reader command, query families and per-title budget, sector employers recorded once per season, several web-search tools, refusals and `/add-provider` offer, `dependencies: [playwright]`, `min_seconds_between_requests: 5`, fields, pitfalls; "Sites you never read here" points at `domains`
- [x] 4.2 `/job-search` skill text runs the agentic-search reader after discovery; `/add-provider` asks for `domains`
- [x] 4.3 Tests: `jt providers validate` passes; skill evals unchanged

## 5. Proof

- [x] 5.1 A real run with generic titles in one country (counts only in the change, no personal data): pages read, refused, rendered, drafted, imported (table in the proposal)
- [x] 5.2 `ruff check .`, `pytest`, privacy guard, `openspec validate deepen-agentic-search --strict` (OpenSpec CLI not installed here: deltas checked with a structural script)
