## 1. Resume choice and scoring

- [x] 1.1 Migration 0009: drop the main flag and its index
- [x] 1.2 `choose_base`: posting language → that resume; none → `no_resume_for_language`; unknown language → the only resume or `posting_language_unknown`
- [x] 1.3 Remove `resume main` and the main notion from resume, profile, context, CLI, and the panel text
- [x] 1.4 `score set` records the resume in the posting's language; stale scores only for the replaced language
- [x] 1.5 Tests for every `profile` delta scenario

## 2. Translated drafts

- [x] 2.1 `resume translate --from --to -`: draft DOCX in the profile folder, same design, base untouched
- [x] 2.2 `resume import --translated-from <code>` recorded in the import event and shown in `resume list`
- [x] 2.3 Tests for the draft scenario and the `document-preparation` delta

## 3. Skills and docs

- [x] 3.1 `/setup`: ask the languages to apply in; per language upload or translated draft reviewed in Word
- [x] 3.2 Job search skill and scoring guide: score against the posting-language resume; on `no_resume_for_language`, ask once per run (upload or translate)
- [x] 3.3 Prepare-documents skill and tailoring guide: no silent translation; same ask on the error
- [x] 3.4 README and workspace layout: no main resume; drafts
