## ADDED Requirements

### Requirement: Drafts for the agent's reading
For each target title, the system's LinkedIn reader SHALL write a drafts file
in the run's capture folder with one import record per new posting: the fixed
fields (job id, canonical link, title, company, location, country,
publication date, complete description as plain text, seniority, contract
type) filled in, and the fields that need the agent's reading (work mode,
work-mode detail, language, flags, published salary) left empty. It SHALL
print a short summary with the path of that file and what it did. The agent
SHALL read the drafts and give its reading of each one; it SHALL NOT parse
LinkedIn pages itself.

#### Scenario: One title read
- **WHEN** the agent runs the reader for "Senior Data Engineer" in a run
- **THEN** a drafts file with one record per new posting is written in the run's capture folder, and the summary gives its path and the numbers of pages read, postings found, postings outside the window, postings already seen, and new postings

#### Scenario: The agent only reads
- **WHEN** the drafts file has been written
- **THEN** the agent decides each posting's work mode, detail, language, flags, and stated salary from its title and description, and imports the drafts with those readings without retyping any description

## MODIFIED Requirements

### Requirement: Logged-out access only
The LinkedIn provider SHALL read LinkedIn only over plain HTTP, without
cookies, credentials, or any browser, through two kinds of pages: the guest
job search (`jobs-guest/jobs/api/seeMoreJobPostings/search`) for the list of
postings, and the public posting page (`jobs/view/<id>/`) for each posting.
Every LinkedIn request SHALL be made by the system's LinkedIn reader; the
agent SHALL NOT request LinkedIn pages itself. It SHALL NOT use the user's
LinkedIn session, a browser extension, browser automation, or the
`jobs/search` page, and SHALL NOT fall back to any of them.

#### Scenario: Normal search
- **WHEN** a search runs with LinkedIn enabled
- **THEN** every LinkedIn request goes to the guest search or a public posting page and carries no cookie or authorization header

#### Scenario: Guest search unavailable
- **WHEN** the guest search stops returning postings
- **THEN** LinkedIn is recorded as failed for that run with the reason, and no other access method is tried

#### Scenario: Requests only through the reader
- **WHEN** the agent searches LinkedIn
- **THEN** it runs the reader command and sends no LinkedIn request of its own

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between LinkedIn requests,
including between separate calls of the reader in the same run, SHALL read at
most 3 result pages per target title, and SHALL open a posting's page at most
once per job id per run, only for postings published inside the run's window
and not already stored by an earlier run. It SHALL stop all LinkedIn requests
for the rest of the run on the first throttling response or redirect to a
login or sign-up page, and record the provider as blocked with what happened.
Postings already imported in that run are kept, and any later call of the
reader in that run SHALL be refused. A call of the reader SHALL also be
refused, without sending any request, while another call for the same run is
still running.

#### Scenario: Throttled mid-run
- **WHEN** LinkedIn answers HTTP 429 while the second title is being searched
- **THEN** no further LinkedIn request is sent in that run, the provider is recorded as blocked, and the postings from the first title remain

#### Scenario: Login redirect
- **WHEN** a request is redirected to a login or sign-up page
- **THEN** the provider stops and is recorded as blocked, without following the redirect

#### Scenario: Calling again after a block
- **WHEN** the reader is called for another title in a run where LinkedIn was blocked
- **THEN** it sends no request and answers that LinkedIn is stopped for this run

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
present. A salary SHALL be recorded only when the posting states one.

#### Scenario: Complete posting
- **WHEN** a posting's list entry and its page are read
- **THEN** the posting carries the job id, canonical link, title, company, location, publication date, complete description, seniority, and contract type

#### Scenario: Posting page unavailable
- **WHEN** a posting's page cannot be read but its list entry was
- **THEN** the posting is not imported, and the reader's summary lists its job id and link with the reason so the agent can tell the user
