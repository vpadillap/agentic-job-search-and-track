## 1. Profile data

- [ ] 1.1 Migration: profile fields, target titles with states, base resume history, setup step progress
- [ ] 1.2 Profile service: create version, read active, change title state
- [ ] 1.3 CLI: `jobtracker profile show|set|title`
- [ ] 1.4 Tests for every `profile` scenario

## 2. Resume intake

- [ ] 2.1 CLI: `jobtracker resume import <file>` (copy unchanged, version previous, extract text)
- [ ] 2.2 Empty-extraction detection with a clear error code
- [ ] 2.3 Enqueue rescoring when the base resume changes
- [ ] 2.4 Tests with fixture resumes (text PDF, DOCX, image-only PDF)

## 3. Privacy registration

- [ ] 3.1 CLI: `jobtracker privacy terms add` writing `.private-terms`
- [ ] 3.2 Test that setup leaves no tracked-file changes

## 4. Skill aliases

- [ ] 4.1 Write alias templates in `i18n/skill-aliases/es/` for the six commands
- [ ] 4.2 CLI: `jobtracker skills sync` (install for Spanish, remove otherwise)
- [ ] 4.3 Expose installed command names through the context bundle and API
- [ ] 4.4 Tests for every `skill-localization` scenario

## 5. Setup skill

- [ ] 5.1 Write `.claude/skills/setup/SKILL.md` following the step order in design S1
- [ ] 5.2 Questionnaire reference file (questions, allowed values, defaults) in both languages
- [ ] 5.3 Target-title research procedure (sources, how to present proposals)
- [ ] 5.4 Provider selection step driven by provider front matter
- [ ] 5.5 Guided tour text in English and Spanish
- [ ] 5.6 Dry-run the skill end to end with the fictional persona and a temporary home

## 6. Documentation

- [ ] 6.1 Write the full README: what it is, requirements, quick start, every command with examples, privacy model, troubleshooting
- [ ] 6.2 Add the Spanish README section
- [ ] 6.3 Check README commands against the implemented CLI and skills
