## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between LinkedIn requests,
including between separate calls of the reader in the same run, SHALL read at
most 3 result pages per target title, and SHALL open a posting's page at most
once per job id per run, only for postings published inside the run's window
and not already stored by an earlier run. It SHALL stop all LinkedIn requests
for the rest of the run on the first throttling response or redirect to a
login or sign-up page, and record the provider as blocked with what happened.
It SHALL also stop, with reason `error`, when the network fails, and when the
same title problem occurs on two titles in a row. A title problem (a search
page with job ids but no readable cards, or two postings in a row in a title
whose page has no description) SHALL end only that title: the postings
already read for it are kept, the reader's summary states the problem, the
provider is not recorded as failed, and the next title is read normally. A
title that read at least one results page cleanly resets the count; a title
with no results does not. Postings already imported in that run are kept,
and any later call of the reader in a run where LinkedIn stopped SHALL be
refused. A call of the reader SHALL also be refused, without sending any
request, while another call for the same run is still running.

#### Scenario: Throttled mid-run
- **WHEN** LinkedIn answers HTTP 429 while the second title is being searched
- **THEN** no further LinkedIn request is sent in that run, the provider is recorded as blocked, and the postings from the first title remain

#### Scenario: Login redirect
- **WHEN** a request is redirected to a login or sign-up page
- **THEN** the provider stops and is recorded as blocked, without following the redirect

#### Scenario: Calling again after a block
- **WHEN** the reader is called for another title in a run where LinkedIn was blocked
- **THEN** it sends no request and answers that LinkedIn is stopped for this run

#### Scenario: One title's results page changed
- **WHEN** the search page of the second title has job ids but no readable cards, and the first title was read cleanly
- **THEN** the second title ends with its postings so far, the summary states the problem, LinkedIn is not recorded as failed, and the third title is read normally

#### Scenario: The same problem on two titles in a row
- **WHEN** the search pages of two consecutive titles both have job ids but no readable cards
- **THEN** LinkedIn stops for the run with reason `error`, the detail names both titles, and later calls are refused

#### Scenario: Network failure
- **WHEN** a LinkedIn request fails at the network level
- **THEN** LinkedIn stops for the run with reason `error`, as before

#### Scenario: Posting already stored
- **WHEN** the guest search lists a posting that an earlier run already stored
- **THEN** its page is not opened again and the posting is recorded as seen in this run

#### Scenario: Calls in parallel
- **WHEN** the reader is called for a second title while the call for the first title of the same run is still running
- **THEN** the second call is refused without sending any request, and the agent is told to read the titles one at a time

#### Scenario: Pacing across calls
- **WHEN** the reader is called for the next title right after the previous call ended
- **THEN** its first request is sent at least 5 seconds after the last request of the previous call

### Requirement: Posting fields from the posting page
For each posting the provider SHALL record LinkedIn's numeric job id as the
external id, the canonical `linkedin.com/jobs/view/<id>/` link, the title,
company, and location as shown, the publication date the site states, and the
complete description from the posting page as plain text that keeps its
paragraphs and list items, without summarizing or translating it. Seniority
and contract type SHALL be taken from the posting page's criteria when
present. A salary SHALL be recorded only when the posting states one. A
posting whose page cannot be read, or has no description, SHALL NOT be
imported and SHALL be listed in the reader's summary with its job id, link,
and reason; the title SHALL continue with its other postings.

#### Scenario: Complete posting
- **WHEN** a posting's list entry and its page are read
- **THEN** the posting carries the job id, canonical link, title, company, location, publication date, complete description, seniority, and contract type

#### Scenario: Posting page unavailable
- **WHEN** a posting's page cannot be read but its list entry was
- **THEN** the posting is not imported, and the reader's summary lists its job id and link with the reason so the agent can tell the user

#### Scenario: One posting without a description
- **WHEN** one posting page of a title has no description and the next posting page has one
- **THEN** the first posting is listed as unreadable with the reason, the second is drafted, and LinkedIn does not stop
