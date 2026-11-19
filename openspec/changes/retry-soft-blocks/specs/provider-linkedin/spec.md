## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between LinkedIn requests,
including between separate calls of the reader in the same run, SHALL read at
most 3 result pages per target title, and SHALL open a posting's page at most
once per job id per run, only for postings published inside the run's window
and not already stored by an earlier run. A throttling response (HTTP 429 or
999) SHALL be handled by the provider-throttling policy: waiting and
repeating the request, then a cool-down after which the same run resumes. It
SHALL stop all LinkedIn requests for the rest of the run on a redirect (never
followed) or a sign-in page instead of results, and record the provider as
blocked with what happened. Postings already imported in that run are kept,
and any later call of the reader in that run SHALL be refused. A call of the
reader SHALL also be refused, without sending any request, while another call
for the same run is still running.

#### Scenario: Throttled mid-run
- **WHEN** LinkedIn answers HTTP 429 while the second title is being searched and keeps answering 429 after the retries
- **THEN** no further LinkedIn request is sent until the cool-down ends, the postings from the first title remain, and the second title resumes in the same run after the cool-down

#### Scenario: Throttle that clears
- **WHEN** LinkedIn answers HTTP 429 once and the repeated request after the wait succeeds
- **THEN** the reader goes on with the title without a cool-down

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
