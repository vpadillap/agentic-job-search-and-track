## 1. Precondition

- [ ] 1.1 Every other change of this batch is merged into `main` (or explicitly dropped by the owner) (D1)

## 2. Documents

- [ ] 2.1 README (en/es): title, status, job sites from `jt providers list` (D2), commands and plain requests, adding and contributing a job site, Contributing section
- [ ] 2.2 `CONTRIBUTING.md` (new): setup incl. Playwright Chromium, OpenSpec workflow, privacy, providers, checks before a PR
- [ ] 2.3 `AGENTS.md`: status, repository map, contributor setup
- [ ] 2.4 `docs/workspace-layout.md`, `providers/README.md`, `design/` checked against the code; `docs/backlog.md` cleaned

## 3. Tests and wrap-up

- [ ] 3.1 Tests: README commands exist as skills (D3); every provider file is listed in the README (D2)
- [ ] 3.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate update-docs-for-release --strict`
