## 1. Core

- [x] 1.1 `providers.salary_sources(country)`; `set_enabled` refuses salary-only sources (D1, D2)
- [x] 1.2 `jt salary lookup` returns `sources` with what each answered for the posting's keys
- [x] 1.3 Installer and doctor include the salary sources of the profile's country (D3)
- [x] 1.4 Tests

## 2. Agent and panel

- [x] 2.1 Salary guide; `/setup` (job sites step) and `/update` (new sources) wording
- [x] 2.2 Panel: switches for job sites only, a line naming the salary sources; en/es; browser test
- [x] 2.3 README (en/es), CHANGELOG

## 3. Wrap-up

- [x] 3.1 `ruff check .`, full `pytest`, privacy guard, `openspec validate salary-sources-always-on --strict`
