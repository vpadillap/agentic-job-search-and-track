## 1. Profile data

- [x] 1.1 Migration: profile fields, target titles with states, base resume history, setup step progress
- [x] 1.2 Profile service: create version, read active, change title state
- [x] 1.3 CLI: `jobtracker profile show|set|title`
- [x] 1.4 Tests for every `profile` scenario

## 2. Resume intake

- [x] 2.1 CLI: `jobtracker resume import <file>` (copy unchanged, version previous, extract text)
- [x] 2.2 Empty-extraction detection with a clear error code
- [x] 2.3 Record that open postings need rescoring when the base resume changes (per-posting pending items are derived in `add-job-search`)
- [x] 2.4 Tests with fixture resumes (text PDF, DOCX, image-only PDF)

## 3. Privacy registration

- [x] 3.1 CLI: `jobtracker privacy terms add` writing `.private-terms`
- [x] 3.2 Test that setup leaves no tracked-file changes

## 4. Skill aliases

- [x] 4.1 Write alias templates in `i18n/skill-aliases/es/` for the six commands
- [x] 4.2 CLI: `jobtracker skills sync` (install for Spanish, remove otherwise)
- [x] 4.3 Expose installed command names through the context bundle and API
- [x] 4.4 Tests for every `skill-localization` scenario

## 5. Setup skill

- [x] 5.1 Write `.claude/skills/setup/SKILL.md` following the step order in design S1
- [x] 5.2 Questionnaire reference file (questions, allowed values, defaults) in both languages
- [x] 5.3 Target-title research procedure (sources, how to present proposals)
- [x] 5.4 Provider selection step driven by provider front matter
- [x] 5.5 Guided tour text in English and Spanish
- [x] 5.6 Dry-run the skill end to end with the fictional persona and a temporary home
- [x] 5.7 Apply the dry-run findings (design S7) and re-run the documented commands

## 6. Documentation

- [x] 6.1 Write the full README: what it is, requirements, quick start, every command with examples, privacy model, troubleshooting
- [x] 6.2 Add the Spanish README section
- [x] 6.3 Check README commands against the implemented CLI and skills
