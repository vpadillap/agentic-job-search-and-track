## 1. Update commands

- [x] 1.1 `core/update.py`: `check` (fetch, behind/ahead, fast-forward, tracked changes, new providers, schema versions) and `finish` (reinstall, migrate, skills sync, providers install, doctor), idempotent (D2, D3)
- [x] 1.2 CLI `jt update check|finish`
- [x] 1.3 Tests on a temporary git repository: behind, up to date, ahead, diverged, dirty tracked file, untracked user data untouched; finish twice

## 2. One-time offers

- [x] 2.1 Migration: `offers` table; `core/offers.py` registry, list, accept, decline (D4)
- [x] 2.2 CLI `jt offers list|accept|decline`
- [x] 2.3 Tests with a fictional offer: applies or not, accepted once, declined once, never presented again

## 3. Skill and docs

- [x] 3.1 `.claude/skills/update/SKILL.md` (D1, D5) and alias `i18n/skill-aliases/es/actualizar/`; command list; `/setup` presents pending offers
- [x] 3.2 Skill eval set (plain requests, en/es) and skill tests
- [x] 3.3 README (en/es): "Updating"

## 4. Wrap-up

- [x] 4.1 Real check: a temporary clone one commit behind, updated through the skill's steps, user data unchanged (done 2026-11-19: a clone one commit behind a local upstream, workspace initialized; check → pull → finish passed all five steps in ~6 s with the venv+pip route; checksums of every file in the private home identical before and after)
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-self-update --strict`
