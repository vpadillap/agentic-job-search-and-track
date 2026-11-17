## REMOVED Requirements

### Requirement: Main base resume
**Reason**: The project owner decided each resume is the source for its own language; no resume ranks above the others.
**Migration**: Scoring and tailoring use the resume in the posting's language; `resume main` is removed.

## MODIFIED Requirements

### Requirement: Language of an earlier base resume
A base resume imported before languages were recorded SHALL keep working, and
the user SHALL be able to state its language later.

#### Scenario: Existing workspace
- **WHEN** a workspace with one base resume and no recorded language is used
- **THEN** that resume is used for every posting, its language is reported as unknown, and stating its language keeps its files unchanged

## ADDED Requirements

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
