## 1. Documents data and CLI

- [ ] 1.1 Migration: document kind, version, language, change summary, support list, applied rules; answers with origin and alternatives
- [ ] 1.2 `jobtracker documents register|list|path` with versioned naming
- [ ] 1.3 Text diff of a proposed resume against the base resume
- [ ] 1.4 Rescore trigger when a proposed resume is registered
- [ ] 1.5 Tests for versioning, immutability of the base resume, and diff

## 2. Resume tailoring tooling

- [ ] 2.1 DOCX in-place text editing helper (copy base, replace runs, keep formatting)
- [ ] 2.2 Optional DOCX→PDF conversion with detection of available converters
- [ ] 2.3 Layout sanity check (page count before and after)
- [ ] 2.4 Tests with fixture resumes

## 3. Form answers

- [ ] 3.1 `jobtracker answers set|list|alternative` preserving user edits
- [ ] 3.2 Panel: edit, copy, origin labels, pick alternative
- [ ] 3.3 Tests for every `form-answers` scenario

## 4. Pending work

- [ ] 4.1 Derivation of pending items in `jobtracker pending` and the API
- [ ] 4.2 Panel header count and pending list with the batch command
- [ ] 4.3 Tests for every `pending-work` scenario

## 5. Skills

- [ ] 5.1 Write `.claude/skills/prepare-documents/SKILL.md` (pending, ids, all-without-resume modes)
- [ ] 5.2 Tailoring guide reference: truthfulness rule, change levels, consent handling, support list
- [ ] 5.3 Cover letter guide reference: when to write, structure, length
- [ ] 5.4 Write `.claude/skills/form-answers/SKILL.md` with the grounding rules
- [ ] 5.5 Spanish aliases `preparar-documentos` and `formulario`
- [ ] 5.6 End-to-end batch with the fictional persona; review output against every `document-preparation` scenario

## 6. Panel

- [ ] 6.1 Documents column states and document cards in the application detail
- [ ] 6.2 Change summary and comparison view
- [ ] 6.3 Browser tests for document and answer interactions
