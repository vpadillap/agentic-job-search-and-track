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

### Requirement: Base resumes per language
The user SHALL be able to provide a base resume for each language they have
one in, stating its language, and the system SHALL keep one current base
resume per language with its own version history.

#### Scenario: Second language
- **WHEN** the user imports a Spanish resume while an English base resume exists
- **THEN** both are current base resumes, each with its language, and the English one is unchanged

#### Scenario: New version of one language
- **WHEN** the user imports a new Spanish resume while a Spanish base resume exists
- **THEN** the earlier Spanish one is kept as a previous version and the English one is unchanged

### Requirement: Main base resume
Exactly one current base resume SHALL be the main one, used for scoring and as
the source for translation. The first one imported SHALL be the main one until
the user chooses another.

#### Scenario: Choosing the main resume
- **WHEN** the user makes the Spanish base resume the main one
- **THEN** the Spanish one is main and the English one is not

#### Scenario: Rescoring
- **WHEN** a new version of a base resume that is not the main one is imported
- **THEN** no rescoring is requested

### Requirement: Language of an earlier base resume
A base resume imported before languages were recorded SHALL keep working as the
main one, and the user SHALL be able to state its language later.

#### Scenario: Existing workspace
- **WHEN** a workspace with one base resume and no recorded language is used
- **THEN** that resume is the main one, its language is reported as unknown, and stating its language keeps its files unchanged
