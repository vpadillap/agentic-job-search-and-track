# profile Specification

## Purpose
Defines the versioned profile that describes the user's base resume, job needs,
and target titles, which every search, score, and document is based on.

## Requirements

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

#### Scenario: Deciding on several titles at once
- **WHEN** the states of several titles are set together
- **THEN** exactly one new profile version is created

#### Scenario: Removing a mistyped title
- **WHEN** a title is removed from the profile
- **THEN** it no longer appears in any state

### Requirement: Facts confirmed by the user
The profile SHALL be able to hold facts about the user that are not on the
resume and that the user confirmed, and these SHALL count as part of the
profile for the purpose of what documents may state.

#### Scenario: Skill not on the resume
- **WHEN** the user confirms a skill that the resume does not mention
- **THEN** it is stored with the profile as an additional fact

### Requirement: Base resume history
The system SHALL keep every base resume the user has provided and SHALL mark
open postings for rescoring when the base resume changes.

#### Scenario: Updated base resume
- **WHEN** the user provides a new base resume
- **THEN** the previous file is kept under a versioned name and the system records that open postings need a rescore from that moment

### Requirement: Profile is readable by agents and the panel
The system SHALL expose the active profile, including title states and the
base resume location, in a machine-readable form.

#### Scenario: Reading the profile
- **WHEN** the active profile is requested
- **THEN** the response contains the version number, job needs, titles with their states, and the base resume path
