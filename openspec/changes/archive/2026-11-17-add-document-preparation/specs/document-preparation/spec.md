## Purpose

Defines the tailored resumes and cover letters the agent proposes for tracked
applications, the limits it must respect, and how the user reviews them.

## ADDED Requirements

### Requirement: Tailored resume per application
The agent SHALL be able to produce a proposed resume adapted to a tracked
posting for one application, a chosen set, or every tracked application that
lacks one.

#### Scenario: All applications without a resume
- **WHEN** the user asks for resumes for all tracked applications that have none
- **THEN** each of those applications gets a proposed resume and applications that already had one are untouched

### Requirement: Truthful content
A proposed resume or cover letter SHALL NOT state experience, skills,
employers, dates, or results that are absent from the user's base resume and
profile.

#### Scenario: Required skill the user lacks
- **WHEN** a posting requires a skill that is not in the user's resume or profile
- **THEN** the proposed resume does not claim it and the gap is reported to the user

### Requirement: Layout is preserved by default
The agent SHALL change only content by default and SHALL obtain the user's
consent before changing a resume's layout or structure. Granted or refused
consent SHALL be remembered.

#### Scenario: No consent on record
- **WHEN** tailoring would require a layout change and no consent is recorded
- **THEN** the agent asks the user before making it

#### Scenario: Standing refusal
- **WHEN** the user has said never to change the resume's design
- **THEN** proposed resumes keep the base layout and the agent does not ask again

### Requirement: Base resume is never modified
Producing documents SHALL NOT alter the user's base resume or any earlier
proposed version.

#### Scenario: Second tailoring
- **WHEN** a resume is proposed for an application that already has one
- **THEN** a new version is added and the earlier version and the base resume are unchanged

### Requirement: Change summary and comparison
Every proposed resume SHALL carry a summary of what was changed and why, and
the user SHALL be able to view the differences from the base resume.

#### Scenario: Reviewing changes
- **WHEN** the user opens the comparison for a proposed resume
- **THEN** the changed passages are shown against the base resume

### Requirement: Cover letter where needed
The agent SHALL propose a cover letter when the posting or its form asks for
one or a user rule calls for it, and SHALL otherwise mark it as not required.

#### Scenario: Not requested
- **WHEN** a posting does not ask for a cover letter and no rule requires one
- **THEN** no cover letter is written and the application shows it as not required

### Requirement: Posting language
Documents SHALL be written in the language of the posting, regardless of the
panel language.

#### Scenario: English posting, Spanish panel
- **WHEN** documents are prepared for a posting written in English while the panel is in Spanish
- **THEN** the resume and cover letter are in English

### Requirement: Rescore after tailoring
When a proposed resume is stored the application SHALL be rescored against it.

#### Scenario: Tailored resume stored
- **WHEN** a proposed resume is registered for an application
- **THEN** the application shows a score judged against that resume
