Code already in the working tree (from before the 2026-11-17 revision) is noted
per task; a task is checked only when it matches the revised design and is
tested.

## 1. Insights (descriptive)

- [x] 1.1 Resolution logic and outcome definitions from snapshots and events (`insights.outcomes`, written)
- [x] 1.2 Headline indicators with counts and period selection (`insights.summary`, written)
- [x] 1.3 Segment breakdowns with smoothed rates, intervals, and minimum-case marking (`insights.breakdown`, `stats.py`, written)
- [x] 1.4 Add posting language as a dimension; work mode from the posting's current value with a "not stated" group
- [x] 1.5 Dismissals by reason and trait, and user corrections of work-mode readings per provider, as learning inputs
- [x] 1.6 `jobtracker insights summary|breakdown` and matching API
- [x] 1.7 Tests for every `outcome-insights` scenario with synthetic histories

## 2. Full history for the agent

- [x] 2.1 Write `learning/history.jsonl` in the private home: every application with its outcome so far, every dismissal with its reason, every correction
- [x] 2.2 Similarity order for `--posting <id>` (title, skills, language, work mode); never truncated
- [x] 2.3 Add the `learning/` folder to `docs/workspace-layout.md`
- [x] 2.4 Tests for the "Full history for the agent" scenarios

## 3. Rules and lessons

- [x] 3.1 Migration `0011_learning.sql`: lesson candidate key and cases, applied date, influence records, analyses, experiments (written; renumbered after `0010_work_mode_detail`)
- [x] 3.2 `jobtracker rules propose|apply|ignore|revert`; system rules protected (`learning.propose/apply/ignore/revert`, written)
- [x] 3.3 Effects list per design L4: replace `title_priority` and `provider_priority` with `title_state` (profile change on apply); remove the search hooks already added in `search.start_run`
- [x] 3.4 Effects wired into scoring (weights), documents (resume emphasis), salary answers (cap), tracking thresholds, and the Search board's default score filter
- [x] 3.5 Influence recording on scores, suggestions, documents, and answers (written); `rule_effect` comparison (written)
- [x] 3.6 Lesson candidates from outcomes (written), dismissals, corrections, and validated weights
- [x] 3.7 Tests for every `rules-and-lessons` scenario

## 4. Learning refresh and levels

- [x] 4.1 Level computation with thresholds in one module (`learning.level`, written); level history per refresh
- [x] 4.2 `jobtracker learning refresh [--posting <id>]`: insights, level, refit only after 10 new resolved outcomes, history file, effects, candidates
- [x] 4.3 Level, effects, and last refresh in the context bundle and API (context partly written)
- [x] 4.4 Tests for level transitions up and down and for refit gating

## 5. Prediction and rubric retraining

- [x] 5.1 Features from snapshots plus the posting's current work mode and language; no work-mode detail (`predict.py`, written; to adjust)
- [x] 5.2 Regularized logistic regression with recency weighting; walk-forward validation, pass criteria, calibration (written)
- [x] 5.3 `jobtracker predict show`; per-posting estimate with range and top factors (estimate written)
- [x] 5.4 History score component from the estimate; neutral otherwise (written in scoring)
- [x] 5.5 Automatic withdrawal when validation fails; learning reset
- [x] 5.6 Weights candidate from the validated model (bounded, only on a change of 5+ points); applying marks open postings for rescoring
- [x] 5.7 Fit-to-you model from track and dismiss decisions: features before the decision, gate (30 decisions, 8 of each), back-test, refit after 10 new decisions
- [x] 5.8 Fit label in the Search board (sortable) and in the refresh output for the agent; never in the score or the search
- [x] 5.9 Tests for every `outcome-prediction` scenario (including fit) and the rubric retraining scenarios, with synthetic data with and without signal

## 6. Recommendations

- [x] 6.1 Apply-next ranking (written)
- [x] 6.2 Salary ask guidance bounded by evidence (written)
- [x] 6.3 Resume emphasis and gap report grounded in the user's resumes (written)
- [x] 6.4 Follow-up and no-response timing from response times (written)
- [x] 6.5 Experiments: propose, accept, track, conclude (written)
- [x] 6.6 `jobtracker recommend|experiments` commands and API
- [x] 6.7 Tests for every `recommendations` scenario

## 7. Skills

- [x] 7.1 `/job-search`: refresh step after filtering and before scoring; read the history and cite similar cases and applied rules in score notes
- [x] 7.2 Fix the resume reference format in `.claude/skills/job-search/scoring-guide.md` (send the pending item's `resume` object as is)
- [x] 7.3 `/prepare-documents`: refresh step before tailoring; use effects and the history; cite applied rules
- [x] 7.4 Write `.claude/skills/analyze-results/SKILL.md` as the optional deeper review: candidates and history, confounding, wording, qualitative reading of work-mode details, experiments
- [x] 7.5 Analysis guide reference: what the agent may and may not conclude, wording of evidence
- [x] 7.6 Spanish alias `analizar-resultados` (template exists in `i18n/skill-aliases/es/`; verify it installs once the skill is built)
- [x] 7.7 Dry-run the refresh inside `/job-search` scoring and `/prepare-documents` with the fictional persona

## 8. Learning board and demo

- [x] 8.1 Level banner with next-level requirements, decisions still needed for the fit estimate, and last refresh
- [x] 8.2 Indicators, period selector, four breakdown panels
- [x] 8.3 Lessons list with Apply, Ignore, Revert
- [x] 8.4 Prediction track record and recommendations sections, shown only at their levels
- [x] 8.5 Interview-chance column and detail on the Search and Applications boards at level 2+
- [x] 8.6 `demo seed --learning <level>`: fictional history reaching each level; fix the demo score note listing a skill as both matched and missing
- [x] 8.7 Browser tests for every `learning-board` scenario against each demo level
