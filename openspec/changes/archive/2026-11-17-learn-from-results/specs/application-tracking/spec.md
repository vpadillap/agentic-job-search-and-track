## MODIFIED Requirements

### Requirement: Application details
The user SHALL be able to record the date they applied, the monthly salary they
asked for, the monthly salary they were offered, the channel, a contact,
notes, and the date of the next step.

#### Scenario: Recording the asked salary
- **WHEN** the user enters the salary they asked for
- **THEN** it is stored with its currency and shown next to the suggested salary

#### Scenario: Recording the offered salary
- **WHEN** the user enters the salary the company offered
- **THEN** it is stored with its currency and basis, shown next to the asked and suggested salaries, recorded in the history, and given to the agent

### Requirement: History
The system SHALL record every change to an application with its date,
including the moment the application first gets an applied date. The facts
at the time of applying SHALL be derived from that history and the current
data, without a separate copy: the score and the salary suggestion are the
versions that were current at that moment (or the first ones, when the
posting was scored only later); the resume sent, cover letter, channel,
applied date, and asked and offered salaries are the current ones.

#### Scenario: Timeline
- **WHEN** the user opens an application's history
- **THEN** it lists when it was found, when documents were produced or uploaded, when it first got an applied date, and each status change by the full names of the statuses

#### Scenario: Snapshot at application time
- **WHEN** a posting is rescored and its salary suggestion revised after the user applied
- **THEN** its facts at application time still give the score and the suggested salary that were current when the application first got its applied date, derived from their stored versions

#### Scenario: Sent resume uploaded after applying
- **WHEN** the user marks an application Applied and uploads the resume they sent a day later
- **THEN** the application counts as sent with that resume

#### Scenario: Existing applications keep their date of applying
- **WHEN** a workspace with applications from before this change is migrated
- **THEN** each application that had facts recorded at application time keeps that moment in its history, and its score at application time is unchanged
