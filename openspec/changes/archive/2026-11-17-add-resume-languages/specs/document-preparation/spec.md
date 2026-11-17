## ADDED Requirements

### Requirement: Tailoring starts from the matching language
A tailored resume SHALL start from the user's base resume in the posting's
language when one exists, and SHALL otherwise start from the main base resume
and be translated. Each tailored resume SHALL record the base resume it came
from.

#### Scenario: Base resume in the posting's language
- **WHEN** a resume is tailored for a Spanish posting and the user has a Spanish base resume
- **THEN** the tailored resume is made from the Spanish base resume and no translation is needed

#### Scenario: No base resume in the posting's language
- **WHEN** a resume is tailored for a Portuguese posting and the user has only English and Spanish base resumes
- **THEN** it is made from the main base resume and marked as needing translation

#### Scenario: Comparison
- **WHEN** the user opens the comparison of a tailored resume
- **THEN** it is compared with the base resume it came from
