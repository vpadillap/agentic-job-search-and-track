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

### Requirement: Language of an earlier base resume
A base resume imported before languages were recorded SHALL keep working, and
the user SHALL be able to state its language later.

#### Scenario: Existing workspace
- **WHEN** a workspace with one base resume and no recorded language is used
- **THEN** that resume is used for every posting, its language is reported as unknown, and stating its language keeps its files unchanged

### Requirement: Scoring against the resume in the posting's language
A posting SHALL be scored against the user's base resume in the posting's
language, and replacing the resume of a language SHALL make stale only the
scores of postings in that language.

#### Scenario: Two languages
- **WHEN** the user has English and Spanish resumes and a Spanish posting is scored
- **THEN** the score records the Spanish resume

#### Scenario: Replacing one language
- **WHEN** a new Spanish resume is imported
- **THEN** Spanish postings scored against the earlier one need rescoring and English postings do not

### Requirement: No resume in the posting's language
Scoring or tailoring a posting in a language the user has no resume in SHALL
fail with an error naming the language, and nothing SHALL be translated
without the user.

#### Scenario: Portuguese posting
- **WHEN** a Portuguese posting is scored and the user has only English and Spanish resumes
- **THEN** the command fails naming Portuguese and no score is stored

### Requirement: Translated draft for review
The agent SHALL be able to produce a translated draft of one of the user's
resumes, with the same design, that becomes the base resume for that language
only after the user imports it.

#### Scenario: Draft then import
- **WHEN** a Portuguese draft is translated from the English resume and the user imports it
- **THEN** the draft keeps the English resume's formatting, the English resume is unchanged, and the Portuguese resume is recorded as translated from English
