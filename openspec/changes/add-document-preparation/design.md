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
`resume-proposed-v<N>.docx`, convert to PDF when a converter is available.
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

## Risks / Trade-offs

- [Agent embellishes] → M1 support list, change summary, diff view, and the
  user reviews before sending.
- [DOCX in-place edits break formatting in complex layouts] → verify by
  rendering to PDF and comparing page count; fall back to asking the user.
- [No PDF converter installed] → deliver DOCX and say so.
- [Large batches are slow] → ordered by score, resumable, per-item report.
