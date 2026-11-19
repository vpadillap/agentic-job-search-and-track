## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between opening Bumeran pages,
including between separate calls of the reader in the same run, SHALL read at
most 2 result pages per target title, and SHALL open a posting's page at most
once per posting per run, only for postings published inside the run's window
and not already stored by an earlier run. HTTP 429 on a page or on the site
data, and a Cloudflare challenge page ("Just a moment…") that is not passed,
SHALL be handled by the provider-throttling policy: waiting and repeating the
page, then a cool-down after which the same run resumes. It SHALL stop all
Bumeran requests for the rest of the run on HTTP 403 or a Cloudflare block
page ("Attention Required", "Access denied"), and record the provider as
blocked with what happened. Postings already imported in that run are kept,
and any later call of the reader in that run SHALL be refused. A call SHALL
also be refused, without opening any page, while another call for the same
run is still running.

#### Scenario: Challenge mid-run
- **WHEN** Bumeran keeps showing a challenge page after the retries while the second title is being read
- **THEN** no further Bumeran page is opened until the cool-down ends, the postings from the first title remain, and the second title resumes in the same run after the cool-down

#### Scenario: Block page mid-run
- **WHEN** Bumeran shows a Cloudflare "Attention Required" page
- **THEN** no further Bumeran page is opened in that run and the provider is recorded as blocked

#### Scenario: Calling again after a block
- **WHEN** the reader is called for another title in a run where Bumeran was blocked
- **THEN** it opens no page and answers that Bumeran is stopped for this run

#### Scenario: Posting already stored
- **WHEN** the results list a posting that an earlier run already stored
- **THEN** its page is not opened again and the posting is recorded as seen in this run

#### Scenario: Calls in parallel
- **WHEN** the reader is called for a second title while the call for the first title of the same run is still running
- **THEN** the second call is refused without opening any page, and the agent is told to read the titles one at a time

#### Scenario: Pacing across calls
- **WHEN** the reader is called for the next title right after the previous call ended
- **THEN** its first page is opened at least 5 seconds after the last page of the previous call
