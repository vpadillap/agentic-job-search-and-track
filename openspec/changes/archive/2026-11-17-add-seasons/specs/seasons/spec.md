## Purpose

Defines search campaigns ("seasons"), so a user can start over with a new or
updated profile after a long pause or a change of direction without losing
history or what was learned.

## ADDED Requirements

### Requirement: One active season
The system SHALL have exactly one active season at a time, and searches,
tracked applications, and insights SHALL refer to the active season by default.

#### Scenario: Default views
- **WHEN** a second season is active
- **THEN** the boards list only applications from the second season unless the user opens an earlier one

### Requirement: Starting a new season
The user SHALL be able to start a new season, which closes the current one and
creates a new profile using the previous answers as defaults.

#### Scenario: New season with an updated resume
- **WHEN** the user starts a new season and provides a new resume
- **THEN** the new season's profile uses the new resume and the earlier season keeps its own profile and resume

### Requirement: Earlier seasons remain available
Applications and results of earlier seasons SHALL remain viewable, and the user
SHALL still be able to record a late outcome on them.

#### Scenario: Late reply
- **WHEN** an employer replies to an application from an earlier season
- **THEN** the user can open that season and update the application's status

### Requirement: Choice of what carries over
When starting a new season the user SHALL choose whether learned lessons are
kept or reset; preferences the user stated SHALL be kept in both cases.

#### Scenario: Keeping learning
- **WHEN** the user keeps learning
- **THEN** applied lessons remain active and are marked as coming from an earlier season

#### Scenario: Resetting learning
- **WHEN** the user resets learning
- **THEN** learned lessons no longer affect the agent, predictions are withdrawn, and the user's stated preferences still apply

### Requirement: Open applications are not lost
When a new season starts with applications still in progress, the user SHALL
decide whether each continues in the new season.

#### Scenario: Interview in progress
- **WHEN** a new season starts while one application is at the interview stage and the user chooses to carry it over
- **THEN** it appears in the new season with its full history

### Requirement: Full reset without deletion
The user SHALL be able to request a completely clean start, which SHALL require
explicit confirmation, SHALL preserve all previous data in an archive, and
SHALL leave an empty, initialized workspace.

#### Scenario: Confirmed full reset
- **WHEN** the user confirms a full reset
- **THEN** the previous data is in a dated archive folder and setup is required again

#### Scenario: Unconfirmed full reset
- **WHEN** the user does not confirm
- **THEN** nothing is changed

### Requirement: Export
The user SHALL be able to export their applications, history, and rules to
common file formats inside their private home.

#### Scenario: Export before restart
- **WHEN** the user requests an export
- **THEN** the exported files are created in the exports folder of the private home
