## 1. Study (scratch scripts only; nothing in the repo but this change's text)

- [x] 1.1 Public structured data: API or embedded data for searches and postings; filters, paging, description (every address verified with a real request)
- [x] 1.2 Pages: search and posting pages over plain HTTP, headless, visible browser; checks or sign-in walls
- [x] 1.3 Fields: id, link, title, company, location and remote scope, date, salary, seniority, description; application questions without applying
- [x] 1.4 Coverage: countries served, how a posting states its country or remote scope; global or local
- [x] 1.5 Terms of use and robots.txt
- [x] 1.7 Scrapling for Get on Board: time and results against the other routes
- [x] 1.8 Scrapling on Indeed, Bumeran, LinkedIn (study only): time, postings, descriptions, blocks, window; results recorded for the owner
- [x] 1.6 Results in the proposal and design (D3–D7); owner's decisions of 2026-11-18 recorded
- [x] 1.9 Owner approves the design before section 2 (2026-11-18)
- [x] 1.10 Indeed's second-page wall (owner's request): ways to get more than one page of postings per title logged out (other sort order, shorter windows, cities, remote filter, feeds), each as the first load of a fresh session; unique postings against the 15 of one page

## 2. Get on Board reader

- [ ] 2.1 `core/readers/getonbrd.py`: two searches per title (country, `remote=true`), merge, paging, title match shared with Greenhouse, window, cap, drafts with sections as plain text and hints (D3, D4); stop rules (D5); registry entry
- [ ] 2.2 Tests with a fake getter and fictional API answers: drafts, both searches merged, remote from anywhere kept, other titles dropped, window, seen, duplicate, paging, cap, no country, blocked, bad JSON, no results
- [ ] 2.3 `providers/getonbrd.md`: `regions: [global]`, `access: http`, recipe, fields, terms (including the 24-hour clause as personal use), stop conditions, pitfalls

## 3. Bumeran and Indeed on Scrapling

- [ ] 3.1 Bumeran adapter: headless `StealthySession`, listener attached before each load, same captures; missing Scrapling reported (D6)
- [ ] 3.2 Indeed adapter: headless `StealthySession`, side-panel clicks in the page action; several first pages per title, each in a fresh session (relevance, date, last day, city, remote, 3 days), stop at the cap (60), the site's total, or two variants without new postings; a sign-in or security page after the first variant ends the title without a block (D6)
- [ ] 3.3 `providers/bumeran.md` and `providers/indeed.md`: `access: scrapling`, `dependencies: [scrapling]`, no window, updated forbidden lists and terms text
- [ ] 3.4 Tests: existing reader tests pass with their fake browsers; new tests for the Indeed variants (order, stop rules, no repeats) and the sign-in rule and the missing-Scrapling message

## 4. Dependencies installed by the agent

- [ ] 4.0 `jt providers install <id>` / `--enabled`: installs a provider's missing dependencies into the project's Python and reports the doctor check (D8)
- [ ] 4.0a `/job-search`: before searching, installs missing dependencies of enabled providers and tells the user; skips only if the install fails. `/setup` step 8 uses the same command
- [ ] 4.0b Tests: install command with a fake runner (known dependency, unknown dependency, failure), skill texts

## 4b. Agentic web search

- [ ] 4.1 `providers/agentic-search.md`: Get on Board in "Sites you never read here"

## 5. Real check and wrap-up

- [ ] 5.1 Real checks in a temporary home with the fictional persona: Get on Board (one title), Bumeran (one title), Indeed (one title), each imported with readings
- [ ] 5.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-getonbrd --strict`
