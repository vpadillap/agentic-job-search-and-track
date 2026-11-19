## 1. Data for the analysis

- [x] 1.1 Migration: `company_profiles`; evidence scope, role family, and level; set-aside reasons; the suggestion's note, inputs with weights, and counts by kind (D1, D2, D2b)
- [x] 1.2 `jt companies profile`: record or update a company's profile with its source (D2)
- [x] 1.3 `jt salary lookup`: offered, history (offers and published salaries with profiles), fresh evidence for the company and market keys, what was checked (D1, D3)
- [x] 1.4 `jt salary set`: the note, inputs with weights, set-aside reports; the evidence rule per kind of source (D2b)
- [x] 1.5 Keys and reuse: title family, market key (30 days), company key (60 days), "no data" per key and source (D3)
- [x] 1.6 Tests: lookup gathers everything; one history source accepted; one market source rejected; two market accepted; outlier recorded; market evidence reused at another company; "no data" not searched again; profiles stored with their source; existing suggestions still shown

## 2. Skill, rules, and panel

- [x] 2.1 Salary guide and `job-search` skill: gather with lookup, group a run's postings by key, search only what is missing, analyse (same company first, else similar companies), write the note; company profiles from the posting or a linked source
- [x] 2.2 `AGENTS.md` rule 3 reworded (D2b)
- [x] 2.3 Search board: offered and suggested ranges with counts by kind, the note as tooltip and in the detail, every input with its reference; en/es (D4); browser test

## 3. More salary sources (study, then the owner chooses)

- [x] 3.1 Study, logged out with real requests: Indeed salaries, Computrabajo, Bumeran, Payscale, Talent.com, SalaryExpert, Levels.fyi, official occupational data, published surveys; company-level or market, sample, recency, level, currency, terms (D5)
- [x] 3.2 Results table in the proposal; the owner chose Indeed salaries and Computrabajo salaries (2026-11-19), and asked to study more global sources: the project is not only for Peru
- [x] 3.3 Global study: Indeed salaries and Computrabajo salaries in every country they serve (address per country, currency, period, sample); other sources with global or multi-country coverage; results table in the proposal
- [x] 3.4 Provider files (`kind: salary`) and salary readers for Indeed salaries and Computrabajo salaries, every country they serve, period taken from structured data; tests on fictional pages; a real check per reader in at least two countries
- [ ] 3.5 Further global sources the study recommends (Payscale, Talent.com), after the owner chooses

## 3b. Currency

- [x] 3b.1 Salary guide: the suggestion's currency is the posting's published one; otherwise how this employer pays for this country (local currency for local employers; often USD for foreign employers hiring remotely); the note says so when it is not the local currency
- [x] 3b.2 Application form: the currency of asked and offered salary starts from the application's own figures, then the posting's published or suggested currency, then the profile's minimum salary currency, never a fixed one; any ISO code can be typed; tested on the hint (the form only reads it)

## 4. Wrap-up

- [x] 4.1 Real check in a temporary home: a run with two postings of the same role at different companies (market researched once), offers in the history from similar companies, the note in the panel
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate rework-salary-research --strict`
