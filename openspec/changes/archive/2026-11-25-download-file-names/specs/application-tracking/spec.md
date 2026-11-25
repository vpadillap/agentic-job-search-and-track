## ADDED Requirements

### Requirement: What removing an application deletes
Removing an application SHALL drop its status, tags, details, form answers,
and document records, SHALL record the removal in the posting's history, and
SHALL delete the application's folder in the private home with every file in
it; nothing outside that folder SHALL be deleted. Its job id SHALL never be
given to another application.

#### Scenario: Files deleted with the application
- **WHEN** J0007 has a tailored resume and a cover letter in its folder and the user removes J0007
- **THEN** the folder of J0007 and its files no longer exist, and the folders of other applications and the base resumes are unchanged

#### Scenario: Tracking a removed posting again
- **WHEN** the user removed J0007 and later tracks the same posting again
- **THEN** it gets a new job id, not J0007, and starts with the initial status
