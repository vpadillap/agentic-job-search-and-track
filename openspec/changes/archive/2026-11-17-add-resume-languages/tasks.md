## 1. Data

- [x] 1.1 Migration: `language` and `is_main` on base resumes (existing current one becomes main), `base_resume_id` on documents
- [x] 1.2 Import per language: files `resume-base-<lang>.*`, history per language, rescoring only for the main one
- [x] 1.3 CLI: `resume import --language`, `resume list`, `resume main <code>`, `resume language <code>`; context lists every base resume
- [x] 1.4 Tests for every scenario in the `profile` delta

## 2. Tailoring

- [x] 2.1 `documents tailor` picks the base by posting language (`--base` override), reports `translate`, records `base_resume_id`
- [x] 2.2 `documents diff` compares against the recorded base resume
- [x] 2.3 Panel: the proposed-resume card names the base resume it came from (en/es)
- [x] 2.4 Tests for every scenario in the `document-preparation` delta

## 3. Skills and docs

- [x] 3.1 `/setup` resume step: ask for other language versions and import each with its language; ask the language of an existing unknown one
- [x] 3.2 Tailoring guide and prepare-documents skill: use the base in the posting's language first; translate only when `translate` is true
- [x] 3.3 `docs/workspace-layout.md` and README: base resumes per language
