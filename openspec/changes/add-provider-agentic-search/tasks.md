## 1. Provider file

- [ ] 1.1 `providers/agentic-search.md`: front matter (`regions: [global]`, `access: web-search`, limits), discover / judge / expand / read / stop recipe, reputation rules (D5), sites with their own provider (D2), records (D3), budget (D4), pitfalls
- [ ] 1.2 Test: the file is valid and names the forbidden sources and the caps

## 2. Import and panel

- [ ] 2.1 `core/search.py`: optional `source_site` on a posting record (validated as a host name), stored and returned
- [ ] 2.2 Search board shows the source site next to the provider name; en/es locales
- [ ] 2.3 Tests: import with and without `source_site`; posting without a date stays without a date

## 3. Skill

- [ ] 3.1 `job-search` skill: providers with `access: web-search` (no reader, records built by the agent, `source_site`, flags for missing dates, report when a cap was reached)

## 4. Real check and wrap-up

- [ ] 4.1 Real check with one title in a temporary home; report the sources chosen and why to the owner
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-agentic-search --strict`
