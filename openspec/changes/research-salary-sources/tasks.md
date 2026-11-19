## 1. Study (scratch scripts only; real requests, logged out)

- [ ] 1.1 Salary sites for Peru (Indeed salaries, Computrabajo, Bumeran, Payscale, Talent.com, SalaryExpert, Levels.fyi, others found): what each gives, how it is read, sample, recency, level, currency, terms
- [ ] 1.2 Official and survey data (labour ministry occupational data, statistics, published salary surveys) with dates
- [ ] 1.3 Published salaries in stored postings: how many are comparable for a title, level, and country
- [ ] 1.4 Integration options against `jt salary evidence add` and the comparability checks
- [ ] 1.5 Results table in the proposal and design (D3+); owner chooses sources and integration before section 2

## 2. Implementation (shape depends on 1.5)

- [ ] 2.1 Provider files (`kind: salary` or `both`) and salary readers for the chosen sources, with tests on fictional pages
- [ ] 2.2 Evidence from stored postings, if chosen, with tests
- [ ] 2.3 Salary guide: order of sources, what to record when none counts

## 3. Wrap-up

- [ ] 3.1 Real check: one posting researched through every chosen source in a temporary home
- [ ] 3.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate research-salary-sources --strict`
