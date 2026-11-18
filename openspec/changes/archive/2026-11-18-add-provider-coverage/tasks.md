## 1. Coverage

- [x] 1.1 `core/providers.py`: validate `regions` ([global] or uppercase two-letter codes), add `coverage` and `countries` to listed providers (D1, D2)
- [x] 1.2 `core/providers.py`: `## Countries` table checked per country; required for local providers with two or more countries (D5)
- [x] 1.3 Tests: valid global, valid local (one and several codes), invalid values, countries table (missing row, missing date, extra row, complete), list output; repository files stay valid

## 2. Search

- [x] 2.1 `core/search.py`: skip reason `other_country` at run start, with a detail; no skip without a profile country (D3)
- [x] 2.2 Tests: matching country, other country, no country, disabled stays disabled
- [x] 2.3 `job-search` skill: mention the new skip reason in the run report

## 3. Setup and panel

- [x] 3.1 `setup` skill step 8: global sites plus local sites of the user's country; others not offered
- [x] 3.2 Providers endpoint and Profile & agent board return `profile_country`
- [x] 3.3 Panel: coverage tag and country filter in the Profile & agent job-site list and the Search tab's job-site dialog; `skip.other_country`; en/es locales (D4)
- [x] 3.4 Browser test covering the tag and the filter

## 4. Docs and wrap-up

- [x] 4.1 `providers/_template.md` and `providers/README.md`: global vs local, the `## Countries` table
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-coverage --strict`
