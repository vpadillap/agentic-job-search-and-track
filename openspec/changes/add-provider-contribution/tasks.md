## 1. Private providers

- [ ] 1.1 `core/paths.py`: private providers folder; `docs/workspace-layout.md` updated (D5)
- [ ] 1.2 `core/providers.py`: read both folders, `origin`, id clash, validate both (D1)
- [ ] 1.3 `jt providers read` runs a private reader (`<home>/providers/<id>.py`) after the built-in registry; doctor checks private providers' dependencies (D2)
- [ ] 1.4 Panel: "Private" tag in both job-site lists; en/es
- [ ] 1.5 Tests: listed, validated, enabled, searched, id clash, private reader run with a fictional site, doctor; privacy guard refuses the folder

## 2. Rules and templates

- [ ] 2.1 `providers/CONTRIBUTING.md`: study, access rules, coverage and per-country proof, terms, what "proved" means; linked from `providers/README.md`
- [ ] 2.2 `providers/change-template/` (proposal, spec, tasks) for provider PRs
- [ ] 2.3 `.github/pull_request_template.md` with the new-provider checklist

## 3. Skill

- [ ] 3.1 `.claude/skills/add-provider/SKILL.md`: study with the user, private file from the template, validate, proving search per country, private study record, enable (D3)
- [ ] 3.2 Pull-request offer in the skill (D4): consent, `gh`, fork, branch, copy the file, move reader + tests + dependencies, change folder, checks, `gh pr create`; rewrite of the study table without personal data
- [ ] 3.3 Spanish alias template `i18n/skill-aliases/es/agregar-proveedor`; `jt context` lists the command
- [ ] 3.4 Skill tests in the style of `tests/test_document_skills.py` (required steps and forbidden actions are stated)

## 4. Wrap-up

- [ ] 4.1 Dry run of the workflow with a fictional site in a temporary home (no PR opened)
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-contribution --strict`
