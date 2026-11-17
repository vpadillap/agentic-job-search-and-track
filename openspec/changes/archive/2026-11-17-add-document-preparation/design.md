## Context

Implements D16 and the document parts of D7 and D11 of
`define-foundation-architecture`. The agent writes; the CLI stores, versions,
diffs, and enforces what can be checked mechanically.

## Goals / Non-Goals

**Goals:** truthful documents; the user's layout preserved by default; one
command for everything pending; every document explained by a change summary.

**Non-Goals:** auto-apply; template design; interview prep.

## Decisions

### M1. Truthfulness rule

Tailoring may reorder, select, rephrase, and emphasize what the base resume and
profile already contain. It may not add employers, titles, dates, degrees,
skills, or metrics that are not there. When a posting asks for something the
user lacks, the document does not claim it; the gap is listed for the user.
Form answers follow the same rule, and an answer the agent cannot support is
left as a question for the user rather than guessed.
*Enforcement:* the skill requires the agent to list each added skill term with
the base-resume line supporting it; the CLI stores that list with the document
and the panel shows it.

### M2. Change levels and consent

- Light (default, no consent needed): summary, order of bullet points and
  skills, wording within existing bullets.
- Medium (consent once, stored as a user rule): adding or removing sections
  that exist in the base resume, changing length.
- Heavy (consent each time unless a rule says otherwise): layout, template,
  structure, rebuilding from extracted text.

Active rules are read first; a request that would exceed the allowed level
stops and asks.

### M3. Format path

DOCX base: copy the base, edit text in place, save as
`resume-proposed-v<N>.docx`. The result is delivered as DOCX: the user opens
it in Word, adjusts it, and saves it as PDF if an application asks for one.
PDF-only base: ask for the editable source; otherwise heavy-level consent to
rebuild. The original base file is never modified.

### M4. Cover letters only when useful

A cover letter is produced when the posting or its form asks for one, or an
active user rule says when to write one. Otherwise the slot is marked "not
required". Stored as Markdown; the panel offers open and copy.

### M5. Language

Documents and answers are written in the language of the posting. If the base
resume is in another language the tailored resume is a translation plus
tailoring, which is flagged in the change summary.

### M6. Form answers

One answer per stored question, with an origin (agent, edited by user) and an
optional basis note (for example "based on the suggested salary"). Salary
questions use the stored suggestion and any active salary rule; with no
reliable data the answer is left for the user. User edits are never overwritten;
regeneration creates an alternative the user can pick.

### M7. Pending work and batch

Pending items are derived from data, not stored as tasks: tracked application
in the to-apply stage without a tailored resume; cover letter required and
missing; unanswered form questions; rescore needed. `/prepare-documents
pending` processes them all, most promising application first, reports per
application, and continues past individual failures. After a tailored resume is
registered the application is rescored against it.

### M8. Learning hooks

Each document records which lessons and rules were applied when it was written,
so the learning loop can compare outcomes by resume kind and by rule.

### M9. Decisions made while implementing

- `python-docx` is a regular dependency (the proposal listed it as optional),
  so `/setup` installs it like `pypdf`; without it the CLI reports
  `missing_dependency`.
- Whether an application needs a cover letter is stored on the application
  (`required`, `not_required`, or not decided). Not decided counts as pending,
  so the batch always settles it; registering a letter marks it required.
- A tailored resume adds a `rescore` pending item (resume kind `tailored`);
  the pending list keeps one rescore per posting, against the most specific
  resume (sent, then tailored, then base).
- DOCX tailoring supports two edits: replace text inside one paragraph
  (keeping the formatting of the run where it starts) and move a paragraph.
  Edits apply all or nothing. The layout check compares paragraph count and
  text length with the base resume.
- No PDF conversion (decided by the project owner, 2026-11-17): resumes are
  delivered as DOCX for the user to review in Word and save as PDF
  themselves. This replaces task 2.2's converter detection and the page-count
  part of task 2.3.

### M10. Changes made after the end-to-end run

The batch was run end to end by a separate agent with the fictional persona.
It met the document-preparation scenarios and left nothing pending, and led
to these fixes:

- The CLI read JSON piped on standard input with the console's code page
  (cp1252 on Windows), corrupting accented text. It now always reads UTF-8.
- The skills now say where the posting text is, that registering a resume
  adds the rescore item, that a rescore changes only what the resume affects,
  how to handle translated resumes, and to read a document before registering
  it (a registered version cannot be removed).

Found but out of scope (recorded in `docs/backlog.md`): withdrawing a
registered version, an inconsistent demo score note, and the resume reference
format shown in the job-search scoring guide.

## Risks / Trade-offs

- [Agent embellishes] → M1 support list, change summary, diff view, and the
  user reviews before sending.
- [DOCX in-place edits break formatting in complex layouts] → verify by
  comparing paragraph count and text length, and the user reviews the DOCX
  in Word before sending it.
- [Large batches are slow] → ordered by score, resumable, per-item report.
