## 1. Reader

- [x] 1.1 `core/readers/__init__.py` (registry, `no_reader`) and `core/readers/linkedin.py`: inputs from run, provider front matter, and profile (D1, D2)
- [x] 1.2 HTTP with `urllib` (no redirects, no cookies, fixed headers, timeout), injectable fetch, clock, and sleep (D3)
- [x] 1.3 Run state file: pacing across calls, request counter and raw page captures, job ids opened in the run; one call at a time per run (lock, `reader_busy`, stale lock taken over) (D4)
- [x] 1.4 Card handling: window, duplicate in run, known posting imported as seen, new posting opened; unreadable pages listed (D5)
- [x] 1.5 `html.parser` extraction of cards and posting pages; description as plain text; stop rules (blocked, error, no results) recorded on the run, later calls refused (D6, D9)
- [x] 1.6 Drafts file and summary (D7, D9)

## 2. Import with readings

- [x] 2.1 `core/search.py`: merge readings into drafts by job id (allowed keys only, one reading per draft, unknown ids refused) before validation (D8)
- [x] 2.2 CLI: `providers read <provider> <run_id> --title [--location]` and `postings import … --readings <file>`

## 3. Provider file and skill

- [x] 3.1 `providers/linkedin.md`: access through the command, what the reader does (requests, parameters, window table, limits, stop rules), the agent's part (read drafts, write readings, import, record ok), `--location` as the profile country's English name; front matter `dependencies: []`, `last_verified` updated
- [x] 3.2 `job-search` skill: importing a reader's drafts with `--readings`

## 4. Tests

- [x] 4.1 Fictional HTML fixtures (search page, posting page, sign-in wall) under `tests/fixtures/linkedin/`
- [x] 4.2 Reader tests with a fake network and clock: drafts content and plain-text description, window, duplicate across titles, known posting seen without a request, pacing across calls, 429/999/3xx/sign-in wall stop and refusal, missing markup error, 404 unreadable, no results, `no_reader`
- [x] 4.3 Import tests: readings merged, missing reading, unknown id, extra field refused, nothing stored on error; repo provider file still valid
- [x] 4.4 Real check: one title, first page, logged out, through the command (a few requests, 5 s apart), and import with readings in a temporary home

## 5. Wrap-up

- [x] 5.1 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-linkedin-reader --strict`
