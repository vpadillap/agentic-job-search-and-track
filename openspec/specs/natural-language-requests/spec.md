# natural-language-requests Specification

## Purpose
TBD - created by archiving change improve-skill-invocation. Update Purpose after archive.

## Requirements

### Requirement: Plain requests reach the right skill
Each user skill SHALL describe when to use it with the plain requests that
should load it, in English and Spanish, so that a request such as "do a job
search" or "completa los documentos de la postulación J0007" loads the
matching skill without the user typing a command. Commands SHALL keep working.

#### Scenario: Plain request for a search
- **WHEN** the user writes "do a job search for this week"
- **THEN** the agent loads the job-search skill with a 7-day window

#### Scenario: Plain request in Spanish for documents
- **WHEN** the user writes "completa los documentos faltantes de la J0007"
- **THEN** the agent loads the prepare-documents skill for application J0007

#### Scenario: Question that is not a task
- **WHEN** the user asks what a cover letter is
- **THEN** the agent answers without starting the document skill

### Requirement: Missing details are asked
When a plain request lacks a value a skill needs and the skill has no
default for it, the agent SHALL ask for that value before starting, and SHALL
use the skill's defaults for everything else.

#### Scenario: Ambiguous application
- **WHEN** the user asks to prepare the documents "for my application at the bank" and two tracked applications match
- **THEN** the agent asks which one, naming both, before preparing anything

### Requirement: Trigger evals
Each user skill SHALL have a set of example requests that must load it and
near-misses that must not, in English and Spanish, using fictional content
only.

#### Scenario: Eval set present
- **WHEN** the skill tests run
- **THEN** every user skill has an eval set with positive and near-miss requests in both languages
