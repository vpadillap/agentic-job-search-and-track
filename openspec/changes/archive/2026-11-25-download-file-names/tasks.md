## 1. Full name record

- [x] 1.1 Add `full_name` to `config.toml` handling (`core/config.py`): validation (1–100 characters, no control characters, spaces collapsed) and TOML escaping of quotes and backslashes; verify with unit tests that a name with an apostrophe or quote round-trips
- [x] 1.2 Add `privacy.set_full_name` / `privacy.full_name` in `core/privacy.py`: stores `full_name` and registers it as a private term in the same call, never echoing it; verify the term appears in `.private-terms` and a second name keeps the first term
- [x] 1.3 Add `jt privacy name set "<name>"` and `jt privacy name show` to `cli/main.py` (JSON output as the other commands); verify with CLI tests against a temporary `JOBTRACKER_HOME`
- [x] 1.4 Tests: `tests/test_privacy.py` (or the existing privacy tests) cover set, change, show, validation errors, and that the privacy guard (`scripts/check_private.py`) refuses a staged file containing the recorded name, using the fictional persona's name

## 2. Download name and Word conversion

- [x] 2.1 Add `markdown_to_docx(text) -> bytes` to `core/docx_tools.py` (lazy `import docx`): headings, paragraphs, bullet items, bold; verify by reading the produced document back with python-docx in a test
- [x] 2.2 Add `documents.download_name(...)` in `core/documents.py` per design decision 3 (name/job-id stem, cover-letter suffix by document then posting language, sanitizing, `.docx`, conversion flag); verify with unit tests for name, no name, Spanish and English letters, and forbidden characters
- [x] 2.3 Change the download endpoint in `web/app.py` to use it: `FileResponse` with the new name for `.docx`, converted bytes with `Content-Disposition: attachment` for `.md`; sent resume and posting unchanged; verify with API tests that check the header's `filename*` and that the body opens as a Word document
- [x] 2.4 Tests: `tests/test_applications.py` (API) covers resume `.docx`, resume `.md`, cover letter in `es` and `en`, no recorded name, and `resume-sent` keeping its name; run `uv run pytest` and `uv run ruff check .`

## 3. One editable mark for a missing work mode

- [x] 3.1 Add `is_work_mode_not_stated(flag)` to `core/search.py` per design decision 5; verify with unit tests: "Modalidad no indicada", "Modalidad de trabajo no indicada", "Work mode not stated." match; "Ciudad no indicada en detalle: dice Lima; modalidad no indicada" and "La modalidad solo la indica Bumeran; la descripción no la menciona" do not
- [x] 3.2 Drop matching flags in `import_postings` and leave them out of the `flags` returned by the search-results and posting-detail read models; verify with tests that an import with the flag stores none and that an already stored flag is not returned
- [x] 3.3 In `components/work-mode.js` and `app.css`, style the chip as a warning when `work_mode` is empty, replacing the colliding `empty` class; verify with a browser test (`tests/test_browser.py`) that a posting without work mode shows no orange "not stated" tag, the chip opens the editor, and after saving "hybrid" the chip has no warning style
- [x] 3.4 Tests: run `uv run pytest tests/test_browser.py tests/test_search*.py` and `uv run ruff check .`

## 4. Remove an application from tracking

- [x] 4.1 Add `tracking.remove(conn, job_ids)` per design decision 6 (no time window, `untracked` event, then delete the application's folder with the path check); verify with tests that the application, its documents, tags, answers, and folder are gone, other applications' folders and `profile/` are untouched, a missing folder is not an error, and a re-track gets a new job id
- [x] 4.2 Add `POST /api/applications/remove` in `web/app.py` and `jt applications remove <job_id>…` in `cli/main.py`; verify with API and CLI tests, including an unknown job id (`not_found`)
- [x] 4.3 Add "Remove from tracking" to each application in `boards/applications.js` with an in-panel confirmation naming the job id and saying its data and documents are deleted (en/es texts); after removal the row leaves the board and the posting shows "Track" again in Search; verify with a browser test for confirm and cancel
- [x] 4.4 Tests: run `uv run pytest` and `uv run ruff check .`

## 5. Setup skill and documentation

- [x] 5.1 Update `.claude/skills/setup/SKILL.md` step 4 (privacy): ask for the full name as on the resume, record it with `jt privacy name set`, then register email and phone with `jt privacy terms add`; mirror the change in the Spanish alias template under `i18n/skill-aliases/`; verify `jt skills sync` still installs and the skill evals in `tests/skill-evals/` pass
- [x] 5.2 Update `docs/workspace-layout.md` (`config.toml` holds the full name; download names of resumes and cover letters) and README en/es where downloads, the work-mode chip, removing an application, or setup's privacy step are described; verify by reading the changed sections
- [x] 5.3 Add the `CHANGELOG.md` entry at the top (plain words; `Providers: none`, `Offers: none`, `Action:` record your full name with /setup, privacy step, so downloads carry it); verify the CI changelog check passes locally
- [x] 5.4 Run `openspec validate download-file-names --strict`, `uv run ruff check .`, and `uv run pytest`; all pass
