## MODIFIED Requirements

### Requirement: Verbatim drafts and pacing
For each posting the reader SHALL record the posting id, its link, title,
company, location, publication date, the complete description as plain text,
and the form questions; SHALL wait at least 5 seconds between requests; SHALL
read each posting at most once per run and never one stored by an earlier
run; SHALL handle HTTP 429 by the provider-throttling policy (waiting,
honouring `Retry-After`, then a cool-down after which the same run resumes);
and SHALL stop Greenhouse for the run when the API answers 403.

#### Scenario: API refuses requests
- **WHEN** the API answers 403
- **THEN** Greenhouse is recorded as blocked for the run and the postings already read are kept

#### Scenario: API throttles requests
- **WHEN** the API answers 429 with `Retry-After: 30` and the repeat succeeds
- **THEN** the repeat is sent no sooner than 30 seconds later and the reader goes on with the board
