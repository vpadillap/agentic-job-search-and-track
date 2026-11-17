## 1. Study (real pages, few loads, 5 s or more apart; findings added to design.md)

- [x] 1.1 Headless check: open the search page, the 7-day search page, and one posting page in headless Chromium; record whether Cloudflare serves them, and settle B2 (headless, or a visible window, or stop and ask the owner)
- [x] 1.2 Confirm the second results page URL (expected `?page=2`, checked against the captured `number`) and the posting URL that can be built from an id alone (list entries carry no link)
- [x] 1.3 Find one posting with choice questions and one with a published salary (or record that none appeared in a reasonable sample) and note their JSON shapes
- [x] 1.4 Save fictional fixtures from the observed shapes (fictional companies and texts only): a search response, a posting response with simple and choice questions, one with a salary range, one closed posting, and a Cloudflare block page

## 2. Reader

- [x] 2.1 `core/readers/bumeran.py`: browser interface (open page, captured responses, document status and title) with the Playwright implementation: fresh context per call, `es-PE`, images/fonts/media cancelled, any `postular` request cancelled, never clicks
- [x] 2.2 URL building: title slug, posting-age window table, page 2, posting URL
- [x] 2.3 Run context, state file, lock, and pacing between page loads (at least 5 s and the provider file's value, across calls)
- [x] 2.4 List handling: outside window, duplicate in run, already stored (seen, no page opened), new
- [x] 2.5 Posting data to draft: fixed fields, plain-text description (LinkedIn helper), form questions, hints (`site_work_mode`, `site_contract`, `site_salary`, `closing_date`); unreadable postings listed
- [x] 2.6 Stop conditions: block or challenge page, 403/429 on document or API, missing or malformed response, page mismatch; recorded on the run; later calls refused
- [x] 2.7 Missing Playwright package or Chromium answered as `missing_dependency` with the install command, before any page
- [x] 2.8 Register `bumeran` in `core/readers/__init__.py`; summary in the same shape as LinkedIn's
- [x] 2.9 Tests with the fake browser and fixtures: every `provider-bumeran` scenario that does not need the real site, the import of a drafts file with readings (questions stored, hints ignored), and that no `postular` request is ever made

## 3. Provider file, dependency, skills, docs

- [x] 3.1 `providers/bumeran.md` from the template: front matter (`regions: [PE]`, `access: playwright`, `requires_login: false`, `live_walk: false`, `dependencies: [playwright]`, `max_results_per_query: 40`, `min_seconds_between_requests: 5`), access method with everything forbidden, recipe around the reader, field table, form questions, limits, terms-of-use risk (clause 1.5.1), known pitfalls
- [x] 3.2 `pyproject.toml` optional group `browser`; confirm `jt doctor` reports Playwright for an enabled Bumeran
- [x] 3.3 `job-search` skill: how to use Bumeran's hints when reading drafts (follow the description, flag a disagreement)
- [x] 3.4 README and AGENTS status lines
- [x] 3.5 Tests: the provider file validates, its terms-risk and forbidden-access statements are present, and doctor names the missing dependency

## 4. Verification

- [x] 4.1 Live check (marked, skipped by default): one search page read through the reader against the real site
- [x] 4.2 Dry run of `/job-search` with Bumeran enabled for the fictional persona's titles in a temporary home; confirm drafts, readings, import, questions visible in the panel, and the run report
