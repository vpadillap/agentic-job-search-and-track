## Purpose

Defines the prescriptive advice the system gives once predictions have proven
reliable: what to apply to next, what to ask for, what to emphasize, when to
follow up, and what to test.

## ADDED Requirements

### Requirement: Recommendations require sustained reliable prediction
The system SHALL offer recommendations only after predictions have passed
validation in two consecutive analyses.

#### Scenario: First successful validation
- **WHEN** predictions pass validation for the first time
- **THEN** estimates are shown but recommendations are not yet offered

### Requirement: Apply-next ranking
The system SHALL rank tracked postings not yet applied to by their estimated
interview chance and present the order with the reason for each position.

#### Scenario: Ranked list
- **WHEN** the user has six postings to apply to and recommendations are active
- **THEN** they are listed from most to least promising with each one's estimate

### Requirement: Salary ask guidance stays within evidence
Guidance on how much to ask SHALL stay within the evidence-based range of the
posting's salary suggestion and SHALL NOT be given for postings without
reliable salary data.

#### Scenario: No salary data
- **WHEN** a posting has no reliable salary data
- **THEN** no ask guidance is given for it

#### Scenario: History shows high asks stall
- **WHEN** the user's applications asking well above the suggestion have not progressed
- **THEN** the guidance recommends an ask at or near the suggestion and cites those cases

### Requirement: Resume emphasis is grounded
Recommendations on what to emphasize in a resume SHALL only name content that
exists in the user's base resume.

#### Scenario: Frequent term not in the resume
- **WHEN** a skill is common in postings that led to interviews but absent from the base resume
- **THEN** it is reported as a gap and not recommended as an emphasis

### Requirement: Follow-up timing
The system SHALL recommend when to follow up and when to consider an
application unanswered, based on the user's observed response times.

#### Scenario: Responses arrive within three weeks
- **WHEN** no past response arrived later than 19 days after applying
- **THEN** the recommended no-response threshold is close to that period

### Requirement: Experiments for open questions
When the data cannot distinguish two options, the system SHALL be able to
propose a simple experiment, track it once the user accepts, and report the
result.

#### Scenario: Cover letter or not
- **WHEN** applications with and without a cover letter show no clear difference
- **THEN** an experiment alternating the two over upcoming similar applications is proposed

#### Scenario: Experiment completed
- **WHEN** an accepted experiment reaches its planned number of applications
- **THEN** its result is reported with counts and, if clear, a lesson is proposed

### Requirement: Recommendations are explained and optional
Every recommendation SHALL state the evidence it rests on, that it reflects
patterns in the user's own data, and SHALL require no action.

#### Scenario: Viewing a recommendation
- **WHEN** the user reads a recommendation
- **THEN** the supporting counts are shown with it
