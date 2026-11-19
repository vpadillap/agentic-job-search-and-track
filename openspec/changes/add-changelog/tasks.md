## 1. Changelog

- [ ] 1.1 `CHANGELOG.md` with the format (D1) and backfilled entries for the changes already merged, from their proposals
- [ ] 1.2 `AGENTS.md` and `CONTRIBUTING.md`: every merge adds its entry and updates the docs it affects; part of the archive step
- [ ] 1.3 CI check on pull requests (D3), with a test of its script

## 2. Update

- [ ] 2.1 `core/update.py`: parse entries; `check` returns `changes` not in the local file (D2); tests
- [ ] 2.2 `/update` skill: answer "is it worth it" from `changes`; after `finish`, offer new job sites and the search (D4); eval requests
- [ ] 2.3 README (en/es): the changelog and what `/update` tells you

## 3. Wrap-up

- [ ] 3.1 Real check: a clone one entry behind; `check` lists it; the skill's offer path
- [ ] 3.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-changelog --strict`
