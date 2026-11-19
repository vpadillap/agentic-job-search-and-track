## 1. Changelog

- [x] 1.1 `CHANGELOG.md` with the format (D1) and backfilled entries for the changes already merged, from their proposals
- [x] 1.2 `AGENTS.md` and `CONTRIBUTING.md`: every merge adds its entry and updates the docs it affects; part of the archive step
- [x] 1.3 CI check on pull requests (D3), with a test of its script

## 2. Update

- [x] 2.1 `core/update.py`: parse entries; `check` returns `changes` not in the local file (D2); tests
- [x] 2.2 `/update` skill: answer "is it worth it" from `changes`; after `finish`, offer new job sites and the search (D4); eval requests
- [x] 2.3 README (en/es): the changelog and what `/update` tells you

## 3. Wrap-up

- [x] 3.1 Real check: a clone one entry behind; `check` lists it (done 2026-11-19 through the real CLI: behind 1, exactly that entry with its provider); the offer path is in the skill
- [x] 3.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-changelog --strict`
