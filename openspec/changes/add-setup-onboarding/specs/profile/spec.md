## Purpose

Defines the versioned profile that describes the user's base resume, job needs,
and target titles, which every search, score, and document is based on.

## ADDED Requirements

### Requirement: Versioned profile
The system SHALL keep the profile as numbered versions within a season, SHALL
create a new version for every change, and SHALL keep earlier versions
readable.

#### Scenario: Changing a job need
- **WHEN** the user changes the accepted work modes
- **THEN** a new profile version becomes active and the previous version is still retrievable

### Requirement: Target title states
Each target title SHALL have exactly one state: included, excluded, suggested,
or under review. Only included titles are searched; excluded titles are used as
negative signals.

#### Scenario: Excluding a title
- **WHEN** the user excludes a title that was included
- **THEN** later searches do not query that title and postings matching it are flagged

### Requirement: Base resume history
The system SHALL keep every base resume the user has provided and SHALL mark
open postings for rescoring when the base resume changes.

#### Scenario: Updated base resume
- **WHEN** the user provides a new base resume
- **THEN** the previous file is kept under a versioned name and every open posting appears in the pending work as needing a rescore

### Requirement: Profile is readable by agents and the panel
The system SHALL expose the active profile, including title states and the
base resume location, in a machine-readable form.

#### Scenario: Reading the profile
- **WHEN** the active profile is requested
- **THEN** the response contains the version number, job needs, titles with their states, and the base resume path
