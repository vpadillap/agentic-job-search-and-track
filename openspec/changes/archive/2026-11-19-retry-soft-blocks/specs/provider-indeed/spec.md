## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL
open each job id at most once per run and never for a posting stored by an
earlier run or published outside the run's window. HTTP 429 and a security
check that does not clear ("Security Check", "Verificación de seguridad",
"Just a moment…") SHALL be handled by the provider-throttling policy:
waiting and repeating the load, then a cool-down after which the same run
resumes. It SHALL stop all Indeed work for the rest of the run, record Indeed
as blocked, and refuse later calls on HTTP 403, a block page ("Blocked"), or
a sign-in page. It SHALL stop with an error when a page no longer matches
what the reader expects. Postings already read are kept.

#### Scenario: Throttled mid-run
- **WHEN** Indeed keeps showing a security check after the retries while the second title is searched
- **THEN** no further Indeed page is opened until the cool-down ends, the first title's postings remain, and the second title resumes in the same run after the cool-down

#### Scenario: Blocked mid-run
- **WHEN** Indeed shows a block page while the second title is searched
- **THEN** no further Indeed page is opened in that run, Indeed is recorded as blocked, and the first title's postings remain

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** it is not clicked and is recorded as seen
