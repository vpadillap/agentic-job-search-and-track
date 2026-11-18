## 1. Provider file

- [x] 1.1 `providers/agentic-search.md`: front matter (`regions: [global]`, `access: web-search`, limits), revisit / discover / judge / expand / read / stop recipe, reputation rules (D5), sites with their own provider (D2), records (D3), budget (D4), remembered companies (D6), pitfalls
- [x] 1.2 Test: the file is valid and names the forbidden sources and the caps

## 2. Remembered companies

- [x] 2.1 Migration: `companies` table (D6); `core/companies.py`
- [x] 2.2 CLI `jt companies list|record|exclude|include`; `jt context` lists it
- [x] 2.3 `docs/workspace-layout.md` database section
- [x] 2.4 Tests: record, update on a later run, list, exclude, include, new season starts fresh

## 3. Import and panel

- [x] 3.1 `core/search.py`: optional `source_site` on a posting record (validated as a host name), stored and returned
- [x] 3.2 Search board shows the source site next to the provider name; en/es locales
- [x] 3.3 Tests: import with and without `source_site`; posting without a date stays without a date

## 4. Skill

- [x] 4.1 `job-search` skill: providers with `access: web-search` (no reader, records built by the agent, `source_site`, flags for missing dates, known companies first, "different companies" requests, exclusions, report when a cap was reached)

## 5. Real check and wrap-up

- [x] 5.1 Real check with one title in a temporary home, run twice (second run revisits known companies; then a "different companies" run); report the sources chosen and why to the owner
- [x] 5.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-agentic-search --strict`
