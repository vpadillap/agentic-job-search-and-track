## Purpose

Defines the alignment score between a posting and the user's profile, how it is
explained, and when it changes.

## ADDED Requirements

### Requirement: Score with explained components
Every scored posting SHALL have a total from 0 to 100 that is the sum of
component scores for target title, skills, seniority, conditions, and history,
each with a short explanation.

#### Scenario: Stored breakdown
- **WHEN** a posting is scored
- **THEN** the total equals the sum of its component points and every component has a note

#### Scenario: Inconsistent submission
- **WHEN** a score is submitted whose component points exceed a component's maximum
- **THEN** the score is rejected and nothing is stored

### Requirement: Skills evidence
The skills component SHALL list which required skills were found in the user's
resume and which were not.

#### Scenario: Missing skill
- **WHEN** a posting asks for a skill absent from the resume
- **THEN** the skills note names it as missing

### Requirement: Score history
The system SHALL keep earlier scores when a posting is rescored, SHALL record
which resume each score was judged against, and SHALL preserve the score that
was current when the user applied.

#### Scenario: Rescore after a resume change
- **WHEN** a posting is rescored against a different resume
- **THEN** the new score is current, the old score remains in history, and the change is shown to the user

### Requirement: Versioned weights
Component maximums SHALL be versioned, and every score SHALL record the weights
version it used.

#### Scenario: Weights change
- **WHEN** component weights are changed
- **THEN** existing scores keep their original version and new scores use the new one
