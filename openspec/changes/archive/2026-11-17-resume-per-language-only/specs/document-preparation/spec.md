## MODIFIED Requirements

### Requirement: Tailoring starts from the matching language
A tailored resume SHALL start from the user's base resume in the posting's
language. When the user has none in that language, tailoring SHALL fail with an
error naming the language. Each tailored resume SHALL record the base resume it
came from.

#### Scenario: Base resume in the posting's language
- **WHEN** a resume is tailored for a Spanish posting and the user has a Spanish base resume
- **THEN** the tailored resume is made from the Spanish base resume and no translation is needed

#### Scenario: No base resume in the posting's language
- **WHEN** a resume is tailored for a Portuguese posting and the user has only English and Spanish base resumes
- **THEN** nothing is written and the error names Portuguese

#### Scenario: Comparison
- **WHEN** the user opens the comparison of a tailored resume
- **THEN** it is compared with the base resume it came from
