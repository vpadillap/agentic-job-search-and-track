## 1. Study (scratch scripts only; nothing in the repo but this change's text)

- [x] 1.1 Candidate job search logged out: plain HTTP, headless, visible Chromium; URL, filters, result data, posting text
- [x] 1.2 If it needs a sign-in: the same search through Claude in Chrome in the user's own Chrome (user signs in themselves); what can be read and what the user must do
- [x] 1.3 Company boards and the public Job Board API: real requests; fields, form questions, limits; how companies would be found
- [x] 1.4 Terms of use of each route
- [x] 1.5 Write the results table into the proposal and design (D1–D9); owner chose the route: public API, boards from the signed-in search when the user is present, web discovery otherwise (2026-11-18)

## 2. Reader

- [x] 2.1 `core/readers/greenhouse.py`: link parsing (posting and board links, three hosts), API reads with an injectable `get`, title match (D3), country match (D5), window, cap, drafts with form questions (D6), board capture reused in the run
- [x] 2.2 Remembered boards and place words in `provider-settings/greenhouse.json` (D4, D5); `--found` and `--place-words` on `jt providers read`
- [x] 2.3 Stop rules (D9); registry entry `greenhouse`
- [x] 2.4 Tests with a fake `get` and fictional boards: found postings, board filtering (title, country, remote region, window), questions mapping, remembered boards (added, rechecked, 404 dropped), unknown country and saved place words, cap, seen and duplicates, pacing, blocked, bad JSON, ignored links

## 3. Provider file

- [x] 3.1 `providers/greenhouse.md`: `regions: [global]`, `access: http`, no login, `max_results_per_query: 100`, `## Countries` place words (PE), signed-in search recipe (D7), web discovery recipe (D8), fields, form questions, terms (public API), stop conditions, pitfalls

## 4. Real check and wrap-up

- [x] 4.1 Real check in a temporary home with the fictional persona: web discovery for one title, then the reader; import with readings
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-greenhouse --strict`
