## 1. Documents data and CLI

- [x] 1.1 Migration: document kind, version, language, change summary, support list, applied rules; answers with origin and alternatives
- [x] 1.2 `jobtracker documents register|list|path` with versioned naming
- [x] 1.3 Text diff of a proposed resume against the base resume
- [x] 1.4 Rescore trigger when a proposed resume is registered
- [x] 1.5 Tests for versioning, immutability of the base resume, and diff

## 2. Resume tailoring tooling

- [x] 2.1 DOCX in-place text editing helper (copy base, replace runs, keep formatting)
- [x] 2.2 ~~Optional DOCX→PDF conversion~~ Dropped by the project owner: resumes are delivered as DOCX (design M9)
- [x] 2.3 Layout sanity check (paragraph count and text length before and after)
- [x] 2.4 Tests with fixture resumes

## 3. Form answers

- [x] 3.1 `jobtracker answers set|list|alternative` preserving user edits
- [x] 3.2 Panel: edit, copy, origin labels, pick alternative
- [x] 3.3 Tests for every `form-answers` scenario

## 4. Pending work

- [x] 4.1 Derivation of pending items in `jobtracker pending` and the API
- [x] 4.2 Panel header count and pending list with the batch command
- [x] 4.3 Tests for every `pending-work` scenario

## 5. Skills

- [x] 5.1 Write `.claude/skills/prepare-documents/SKILL.md` (pending, ids, all-without-resume modes)
- [x] 5.2 Tailoring guide reference: truthfulness rule, change levels, consent handling, support list
- [x] 5.3 Cover letter guide reference: when to write, structure, length
- [x] 5.4 Write `.claude/skills/form-answers/SKILL.md` with the grounding rules
- [x] 5.5 Spanish aliases `preparar-documentos` and `formulario` (template exists in `i18n/skill-aliases/es/`; verify it installs once the skill is built)
- [x] 5.6 End-to-end batch with the fictional persona; review output against every `document-preparation` scenario

## 6. Panel

- [x] 6.1 Documents column states and document cards in the application detail
- [x] 6.2 Change summary and comparison view
- [x] 6.3 Browser tests for document and answer interactions
