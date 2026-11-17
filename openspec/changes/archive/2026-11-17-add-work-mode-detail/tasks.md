## 1. Storage and core

- [x] 1.1 Migration `0010_work_mode_detail.sql` adding `work_mode_detail` and `work_mode_source` to `postings` (verified by a test migrating a database with existing postings: they keep their data, get source `agent` and no detail)
- [x] 1.2 `jt postings import` accepts `work_mode_detail` (trimmed, ≤200 characters, empty → null, rejected with a clear error when too long) and stores it with source `agent`; `posting()` and the board payloads include both fields (verified by tests in `tests/test_search.py`)
- [x] 1.3 `search.set_work_mode` with validation, change counter, and a `posting`/`work_mode` event holding the previous and new values; a later import of the same posting does not overwrite a user value; `applications.history` includes these events for a tracked posting (verified by tests in `tests/test_search.py` and `tests/test_applications.py`)

## 2. CLI and API

- [x] 2.1 `jt postings work-mode <id> --mode remote|hybrid|onsite|none [--detail "…"]` printing the updated posting as JSON (verified by a CLI test, including an invalid mode and an unknown id)
- [x] 2.2 `POST /api/postings/{id}/work-mode` with `{work_mode, detail}` (pydantic, detail ≤200), source `user`; `/api/search` and `/api/applications` rows carry `work_mode_detail` and `work_mode_source` (verified by tests in `tests/test_api.py`)

## 3. Panel

- [x] 3.1 Shared work-mode editor component (chip as button, popover with mode choice and detail input, Enter saves, Escape cancels, "edited" mark for user values, truncation with full text in the tooltip), locale strings in en and es (verified by browser tests below)
- [x] 3.2 Search table: conditions cell shows mode with detail and opens the editor (verified by browser tests: detail shown; setting a missing work mode persists after reload)
- [x] 3.3 Applications table: mode with detail under the company, same editor, and the edit appears in the Search tab and in the application's history (verified by a browser test)
- [x] 3.4 Demo data: a few postings get details (e.g. "2 días presencial por semana", "Summer hours: Fridays until noon") and one has no work mode, so the panel shows each case (verified by updated demo-count tests and the browser tests above)

## 4. Skill and docs

- [x] 4.1 `job-search/SKILL.md`: posting record rows for `work_mode` and `work_mode_detail` as in design W6, and the first-pass rule for an unstated work mode (verified by `tests/test_job_search_skill.py` asserting both)
- [x] 4.2 README (both languages) mentions that the work mode and its detail can be corrected from the panel (verified by reading the diff)
- [x] 4.3 `ruff check .` and the full `pytest` suite, browser tests included (verified by both passing with Chromium installed)
