## 1. Three figures and the research order

- [ ] 1.1 Migration: evidence `scope` (company/market), title family and level on evidence, `set_aside` reasons; suggestion `kind` (D1)
- [ ] 1.2 `core/salary.py`: company history from stored postings; company suggestion (one source allowed, labelled) and market suggestion (two or more); set-aside reports recorded (D1, D2)
- [ ] 1.3 Keys and reuse: title family, market key (30 days), company key (60 days), "no data" per key and source (D3); `jt salary lookup` returns the three parts and what was already checked
- [ ] 1.4 Tests: offered, company history, company suggestion with one source, market needs two, outlier recorded, market evidence reused at another company, "no data" not searched again, existing suggestions still shown

## 2. Skill and panel

- [ ] 2.1 Salary guide and `job-search` skill: group a run's postings by key, research each key once, company references before the market, outliers with reasons (D2, D3)
- [ ] 2.2 Search board: three-line salary cell, detail with sources, set-aside reports, and dates; en/es (D4); browser test

## 3. More salary sources (study, then the owner chooses)

- [ ] 3.1 Study, logged out with real requests: Indeed salaries, Computrabajo, Bumeran, Payscale, Talent.com, SalaryExpert, Levels.fyi, official occupational data, published surveys; company-level or market, sample, recency, level, currency, terms (D5)
- [ ] 3.2 Results table in the proposal; owner chooses sources
- [ ] 3.3 Provider files and salary readers for the chosen sources, tests on fictional pages, a real check each

## 4. Wrap-up

- [ ] 4.1 Real check in a temporary home: a run with two postings of the same role at different companies (market researched once), one company with earlier postings
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate rework-salary-research --strict`
