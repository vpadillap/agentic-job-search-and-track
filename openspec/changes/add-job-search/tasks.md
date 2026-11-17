## 1. Providers

- [ ] 1.1 Provider file parser and validator; `jobtracker providers list|validate|enable|disable`
- [ ] 1.2 Per-user provider state and per-provider dependency checks in `doctor`
- [ ] 1.3 Write and hand-verify `providers/linkedin.md`
- [ ] 1.4 Write and hand-verify `providers/indeed.md` (jobs and salary)
- [ ] 1.5 Write and hand-verify `providers/bumeran.md`
- [ ] 1.6 Write and hand-verify `providers/computrabajo.md`
- [ ] 1.7 Write and hand-verify `providers/glassdoor.md` (salary, live walk)
- [ ] 1.8 Tests for every `provider-recipes` scenario

## 2. Run and import

- [ ] 2.1 `jobtracker run start|finish|show` with raw-capture folder
- [ ] 2.2 `jobtracker postings import` with normalization, date conversion, and both de-duplication keys
- [ ] 2.3 Already-seen, dismissed, and tracked detection; alternate source links
- [ ] 2.4 `jobtracker postings filter` to record exclusions with reasons and flags
- [ ] 2.5 Form-question storage with the posting
- [ ] 2.6 Tests for every `job-search` scenario using recorded fixture captures

## 3. Scoring

- [ ] 3.1 Migration: weights versions, scores history
- [ ] 3.2 `jobtracker score set|show` with validation against active weights
- [ ] 3.3 Neutral history component until the learning loop supplies it
- [ ] 3.4 Rescore queue entries when the judged resume changes
- [ ] 3.5 Tests for every `posting-scoring` scenario

## 4. Salary

- [ ] 4.1 Migration: salary evidence, suggestions, research log
- [ ] 4.2 `jobtracker salary evidence add`, `salary set`, `salary none` with the comparability and two-source rules
- [ ] 4.3 Median, range, and confidence calculation; monthly normalization
- [ ] 4.4 Evidence cache lookup by company, role, and location
- [ ] 4.5 Tests for every `salary-suggestions` scenario

## 5. Skill

- [ ] 5.1 Write `.claude/skills/job-search/SKILL.md` following the pipeline in design J1
- [ ] 5.2 Scoring guide (how to judge each component, examples) as a skill reference file
- [ ] 5.3 Salary research guide (what counts as comparable, what to record) as a skill reference file
- [ ] 5.4 Spanish alias `buscar-empleos`
- [ ] 5.5 End-to-end run with the fictional persona against live providers; confirm the Search board matches the run report
