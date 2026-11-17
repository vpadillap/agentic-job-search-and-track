## ADDED Requirements

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
