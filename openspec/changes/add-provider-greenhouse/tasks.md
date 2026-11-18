## 1. Study (scratch scripts only; nothing in the repo but this change's text)

- [x] 1.1 Candidate job search logged out: plain HTTP, headless, visible Chromium; URL, filters, result data, posting text
- [x] 1.2 If it needs a sign-in: the same search through Claude in Chrome in the user's own Chrome (user signs in themselves); what can be read and what the user must do
- [x] 1.3 Company boards and the public Job Board API: real requests; fields, form questions, limits; how companies would be found
- [x] 1.4 Terms of use of each route
- [ ] 1.5 Write the results table into the proposal and design (D2+); owner chooses the route before section 2

## 2. Implementation (shape depends on 1.5)

- [ ] 2.1 Reader `core/readers/greenhouse.py` and registry entry, or a step-by-step recipe for the extension route
- [ ] 2.2 Tests with fictional pages or responses: drafts, window, seen, form questions, blocked, changed page, no results; skip without the user present when the route needs a login

## 3. Provider file

- [ ] 3.1 `providers/greenhouse.md`: `regions: [global]`, access, `requires_login`/`live_walk` as decided, dependencies, recipe, fields, form questions, terms, stop conditions, pitfalls

## 4. Real check and wrap-up

- [ ] 4.1 Real check: one title through the chosen route; import in a temporary home
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-greenhouse --strict`
