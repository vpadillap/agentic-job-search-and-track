## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL
open each posting at most once per run and never for a posting stored by an
earlier run or published outside the run's window. HTTP 429 and a security
check that is not passed ("Security | Glassdoor", "Just a moment…",
"Un momento…") SHALL be handled by the provider-throttling policy, for
searches and for salary pages: waiting and repeating the load, then a
cool-down after which the same run resumes. It SHALL stop all Glassdoor work
for the rest of the run, record Glassdoor as blocked, and refuse later calls
on HTTP 403, a Cloudflare block page ("Attention Required"), or a sign-in
wall. It SHALL skip a posting whose page has no readable description, and
SHALL stop with an error after three such postings in a row or when a page
no longer matches what the reader expects. Postings already read are kept.

#### Scenario: Throttled mid-run
- **WHEN** Glassdoor keeps answering 429 after the retries while the second title is searched
- **THEN** no further Glassdoor page is opened until the cool-down ends, the first title's postings remain, and the second title resumes in the same run after the cool-down

#### Scenario: Blocked mid-run
- **WHEN** Glassdoor shows a sign-in wall that does not close while the second title is searched
- **THEN** no further Glassdoor page is opened in that run, Glassdoor is recorded as blocked, and the first title's postings remain

#### Scenario: Throttled salary page
- **WHEN** a salary page answers 429 and keeps doing so after the retries
- **THEN** the salary reader answers that it was throttled, with the time it may be tried again, and records no evidence

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** its page is not opened and it is recorded as seen

#### Scenario: Posting without a description
- **WHEN** a posting's page has no readable description
- **THEN** that posting is skipped with a note and the reader continues with the next one
