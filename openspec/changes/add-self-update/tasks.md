## 1. Update commands

- [ ] 1.1 `core/update.py`: `check` (fetch, behind/ahead, fast-forward, tracked changes, new providers, schema versions) and `finish` (reinstall, migrate, skills sync, providers install, doctor), idempotent (D2, D3)
- [ ] 1.2 CLI `jt update check|finish`
- [ ] 1.3 Tests on a temporary git repository: behind, up to date, ahead, diverged, dirty tracked file, untracked user data untouched; finish twice

## 2. One-time offers

- [ ] 2.1 Migration: `offers` table; `core/offers.py` registry, list, accept, decline (D4)
- [ ] 2.2 CLI `jt offers list|accept|decline`
- [ ] 2.3 Tests with a fictional offer: applies or not, accepted once, declined once, never presented again

## 3. Skill and docs

- [ ] 3.1 `.claude/skills/update/SKILL.md` (D1, D5) and alias `i18n/skill-aliases/es/actualizar/`; command list; `/setup` presents pending offers
- [ ] 3.2 Skill eval set (plain requests, en/es) and skill tests
- [ ] 3.3 README (en/es): "Updating"

## 4. Wrap-up

- [ ] 4.1 Real check: a temporary clone one commit behind, updated through the skill's steps, user data unchanged
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-self-update --strict`
