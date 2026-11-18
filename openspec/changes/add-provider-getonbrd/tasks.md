## 1. Study (scratch scripts only; nothing in the repo but this change's text)

- [x] 1.1 Public structured data: API or embedded data for searches and postings; filters, paging, description (every address verified with a real request)
- [x] 1.2 Pages: search and posting pages over plain HTTP, headless, visible browser; checks or sign-in walls
- [x] 1.3 Fields: id, link, title, company, location and remote scope, date, salary, seniority, description; application questions without applying
- [x] 1.4 Coverage: countries served, how a posting states its country or remote scope; global or local
- [x] 1.5 Terms of use and robots.txt
- [x] 1.7 Scrapling for Get on Board: time and results against the other routes
- [x] 1.8 Scrapling on Indeed, Bumeran, LinkedIn (study only): time, postings, descriptions, blocks, window; results recorded for the owner
- [x] 1.6 Results in the proposal and design (D3–D7); owner's decisions of 2026-11-18 recorded
- [ ] 1.9 Owner approves the design before section 2

## 2. Get on Board reader

- [ ] 2.1 `core/readers/getonbrd.py`: two searches per title (country, `remote=true`), merge, paging, title match shared with Greenhouse, window, cap, drafts with sections as plain text and hints (D3, D4); stop rules (D5); registry entry
- [ ] 2.2 Tests with a fake getter and fictional API answers: drafts, both searches merged, remote from anywhere kept, other titles dropped, window, seen, duplicate, paging, cap, no country, blocked, bad JSON, no results
- [ ] 2.3 `providers/getonbrd.md`: `regions: [global]`, `access: http`, recipe, fields, terms (including the 24-hour clause as personal use), stop conditions, pitfalls

## 3. Bumeran and Indeed on Scrapling

- [ ] 3.1 Bumeran adapter: headless `StealthySession`, listener attached before each load, same captures; missing Scrapling reported (D6)
- [ ] 3.2 Indeed adapter: headless `StealthySession`, side-panel clicks in the page action; a sign-in page on a later results page ends the title without a block (D6)
- [ ] 3.3 `providers/bumeran.md` and `providers/indeed.md`: `access: scrapling`, `dependencies: [scrapling]`, no window, updated forbidden lists and terms text
- [ ] 3.4 Tests: existing reader tests pass with their fake browsers; new tests for the Indeed sign-in-on-page-2 rule and the missing-Scrapling message

## 4. Agentic web search

- [ ] 4.1 `providers/agentic-search.md`: Get on Board in "Sites you never read here"

## 5. Real check and wrap-up

- [ ] 5.1 Real checks in a temporary home with the fictional persona: Get on Board (one title), Bumeran (one title), Indeed (one title), each imported with readings
- [ ] 5.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-getonbrd --strict`
