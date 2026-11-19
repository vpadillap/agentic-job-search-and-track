## 1. Baseline

- [x] 1.1 Eval sets per user skill under `tests/skill-evals/` (positive and near-miss, en/es, fictional)
- [x] 1.2 Run the trigger evals with `skill-creator` on the current descriptions; record results in the design

## 2. Descriptions and argument gathering

- [x] 2.1 Rewrite each user skill's description with `skill-creator` (D2), including the Spanish alias skills
- [x] 2.2 Add the "plain request" section to each skill (D3)
- [x] 2.3 Rerun the evals; iterate until positives load and near-misses do not; record results in the design

## 3. Routing and tests

- [x] 3.1 `AGENTS.md` user-mode routing table (D4)
- [x] 3.2 Skill tests: every user skill has the section and an eval set; descriptions name both languages

## 4. Wrap-up

- [x] 4.1 Manual check: three plain requests in a temporary home (a search, documents for one id, an analysis) reach the right skill
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate improve-skill-invocation --strict`
