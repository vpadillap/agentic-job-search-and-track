## 1. Browser folder

- [x] 1.1 `core/browsers.py`: `configure()` sets `PLAYWRIGHT_BROWSERS_PATH` to `%USERPROFILE%\.cache\ms-playwright` on Windows when unset; `location()` names the folder in use (D1)
- [x] 1.2 CLI `main()` calls `configure()` before running any command
- [x] 1.3 Tests: Windows default, user's value kept, other systems untouched, CLI sets it

## 2. Installer checks the browser

- [x] 2.1 Recipes split into `package`, `browser`, `check` (D3)
- [x] 2.2 A tool with a recipe counts as already installed only when the check passes; otherwise the browser steps run and the check again, listed as repaired (D2); the report names the browser folder
- [x] 2.3 Tests: already installed runs only the check; broken browser is repaired without pip; failed repair is reported; missing package runs every step

## 3. Readers and docs

- [x] 3.1 Bumeran and Glassdoor readers use Scrapling's own Chromium (no `real_chrome`)
- [x] 3.2 `CONTRIBUTING.md`: where browsers go on Windows and why
- [x] 3.2a `/job-search`: a reader that answers `missing_dependency` gets one `jt providers install <id>` and one more read (the import-only `doctor` check cannot see a broken browser)
- [x] 3.2b `test_overridden_location` (owner's request): a clone with its own `user-data/` passes; the test checks that the repo's `user-data/` is untouched and gitignored, not that it is absent
- [x] 3.3 Tests: ruff and the whole suite pass; a real Scrapling start on Windows through `jt providers install`
