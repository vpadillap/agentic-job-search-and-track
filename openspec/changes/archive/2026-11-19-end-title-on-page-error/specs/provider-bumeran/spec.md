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
also be refused, without opening any page, while another call for the same run
is still running. It SHALL also stop, with reason `error`, when the browser
cannot load a page. A search with no results SHALL mean no postings for that
title and nothing else. When a search page sends no readable data in time, its
results have no ids, or a later results page is not the page asked for, the
reader SHALL load that page once more after the pacing wait; if it is still
wrong, or if two postings in a row in a title send no posting data, that is a
title problem: it SHALL end only that title, keep the postings already read
for it, state the problem in the reader's summary, leave Bumeran unrecorded as
failed, and let the next title be read normally. A single result without an id
SHALL be skipped and counted, and a single posting without data SHALL be
listed as unreadable; the title SHALL continue. Title problems SHALL NOT stop
the provider, however many titles have them. When the same problem has ended
every title that read anything in the run (two at least), the summary SHALL
say the site may have changed.

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

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and Bumeran goes on with the next title

#### Scenario: Search data back on retry
- **WHEN** a title's search page sends no readable data in time and the same page opened again after the pacing wait does
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: One title's search sends no data
- **WHEN** a title's search page sends no readable data in time, also on the retry
- **THEN** that title ends with its postings so far, the summary states the problem, Bumeran is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with the same title problem
- **THEN** every title is still tried, Bumeran is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Second results page is not page 2
- **WHEN** a title's second results page answers with another page number, also on the retry
- **THEN** the postings of the first page are kept, the title ends with the problem stated, and the next title is read
