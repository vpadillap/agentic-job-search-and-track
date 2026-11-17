## 1. Insights (descriptive)

- [ ] 1.1 Resolution logic and outcome definitions from snapshots and events
- [ ] 1.2 Headline indicators with counts and period selection
- [ ] 1.3 Segment breakdowns with smoothed rates, intervals, and minimum-case marking
- [ ] 1.4 `jobtracker insights summary|breakdown` and matching API
- [ ] 1.5 Tests for every `outcome-insights` scenario with synthetic histories

## 2. Rules and lessons

- [ ] 2.1 Migration: rule effects, lesson evidence, influence records, analysis log
- [ ] 2.2 `jobtracker rules list|add|propose|apply|ignore|revert`; system rules protected
- [ ] 2.3 Structured effects wired into search defaults, title priority, thresholds, salary cap, resume emphasis, weights
- [ ] 2.4 Influence recording on results, scores, documents, and suggestions
- [ ] 2.5 Lesson candidate generation (`jobtracker insights lessons`)
- [ ] 2.6 Tests for every `rules-and-lessons` scenario

## 3. Maturity levels

- [ ] 3.1 Level computation with thresholds in one module; level history
- [ ] 3.2 Level and next-level requirements in the context bundle and API
- [ ] 3.3 Tests for level transitions up and down

## 4. Prediction

- [ ] 4.1 Feature extraction and binning from application snapshots
- [ ] 4.2 Regularized logistic regression in pure Python with recency weighting
- [ ] 4.3 Walk-forward validation, pass criteria, calibration table
- [ ] 4.4 `jobtracker predict fit|show`; per-posting estimate with range and top factors
- [ ] 4.5 History score component from the estimate; neutral otherwise
- [ ] 4.6 Automatic withdrawal when validation fails; learning reset
- [ ] 4.7 Tests for every `outcome-prediction` scenario, including synthetic data with and without signal

## 5. Recommendations

- [ ] 5.1 Apply-next ranking
- [ ] 5.2 Salary ask guidance bounded by evidence
- [ ] 5.3 Resume emphasis and gap report grounded in the base resume
- [ ] 5.4 Follow-up and no-response timing from response times
- [ ] 5.5 Experiments: propose, accept, track, conclude
- [ ] 5.6 Tests for every `recommendations` scenario

## 6. Skill

- [ ] 6.1 Write `.claude/skills/analyze-results/SKILL.md`: read insights and candidates, review for confounding, word lessons, store proposals, refit and validate, report
- [ ] 6.2 Analysis guide reference: what the agent may and may not conclude, wording of evidence
- [ ] 6.3 Spanish alias `analizar-resultados` (template exists in `i18n/skill-aliases/es/`; verify it installs once the skill is built)
- [ ] 6.4 Update search, scoring, and document skills to cite the rules they applied
- [ ] 6.5 Run the analysis on seeded histories at each maturity level and review the output

## 7. Learning board

- [ ] 7.1 Level banner with next-level requirements
- [ ] 7.2 Indicators, period selector, four breakdown panels
- [ ] 7.3 Lessons list with Apply, Ignore, Revert
- [ ] 7.4 Prediction track record and recommendations sections, shown only at their levels
- [ ] 7.5 Interview-chance column and detail on the Search and Applications boards at level 2+
- [ ] 7.6 Browser tests for every `learning-board` scenario
