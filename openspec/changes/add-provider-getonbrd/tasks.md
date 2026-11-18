## 1. Study (scratch scripts only; nothing in the repo but this change's text)

- [x] 1.1 Public structured data: API or embedded data for searches and postings; filters, paging, description (every address verified with a real request)
- [x] 1.2 Pages: search and posting pages over plain HTTP, headless, visible browser; checks or sign-in walls
- [x] 1.3 Fields: id, link, title, company, location and remote scope, date, salary, seniority, description; application questions without applying
- [x] 1.4 Coverage: countries served, how a posting states its country or remote scope; global or local
- [x] 1.5 Terms of use and robots.txt
- [x] 1.7 Scrapling for Get on Board: time and results against the other routes
- [ ] 1.8 Scrapling on Indeed, Bumeran, LinkedIn (study only): time, postings, descriptions, blocks, window; results recorded for the owner (changes to those providers go in their own changes)
- [ ] 1.6 Write the results table into the proposal and design (D3+); owner chooses the route before section 2

## 2. Implementation (shape depends on 1.6)

- [ ] 2.1 Reader `core/readers/getonbrd.py` and registry entry, or a step-by-step recipe
- [ ] 2.2 Tests with fictional responses or pages: drafts, window, seen, salary hint, blocked, changed page, no results

## 3. Provider file

- [ ] 3.1 `providers/getonbrd.md`: coverage, access, recipe, fields, terms, stop conditions, pitfalls
- [ ] 3.2 `providers/agentic-search.md`: Get on Board in "Sites you never read here"

## 4. Real check and wrap-up

- [ ] 4.1 Real check: one title through the chosen route; import with readings in a temporary home
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-getonbrd --strict`
