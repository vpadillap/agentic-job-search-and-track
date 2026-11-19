# provider-linkedin Specification

## Purpose
Defines how the agent searches and reads LinkedIn job postings: logged out,
through LinkedIn's guest search and its public posting pages only, with
conservative pacing, and without ever touching the user's LinkedIn account.

## Requirements

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

### Requirement: Only the filters LinkedIn offers visitors
The provider SHALL send only the parameters LinkedIn offers logged-out
visitors: keywords, location, posting age, and paging. Posting age SHALL use
the smallest of LinkedIn's windows (24 hours, past week, past month) that
covers the run's window; postings older than the run's window are dropped at
import. Work mode and contract type SHALL NOT be sent as filters, because
LinkedIn ignores them for visitors; they are read from each posting instead.

#### Scenario: Seven-day window
- **WHEN** a run uses a 7-day window
- **THEN** each LinkedIn search requests the past week

#### Scenario: Three-day window
- **WHEN** a run uses a 3-day window
- **THEN** each LinkedIn search requests the past week, and postings published more than 3 days ago are not stored

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between LinkedIn requests,
including between separate calls of the reader in the same run, SHALL read at
most 3 result pages per target title, and SHALL open a posting's page at most
once per job id per run, only for postings published inside the run's window
and not already stored by an earlier run. A throttling response (HTTP 429 or
999) SHALL be handled by the provider-throttling policy: waiting and repeating
the request, then a cool-down after which the same run resumes. It SHALL stop
all LinkedIn requests for the rest of the run on a redirect (never followed)
or a sign-in page instead of results, and record the provider as blocked with
what happened. Postings already imported in that run are kept, and any later
call of the reader in that run SHALL be refused. A call of the reader SHALL
also be refused, without sending any request, while another call for the same
run is still running. It SHALL also stop, with reason `error`, when the
network fails. A search page with no results SHALL mean no postings for that
title and nothing else. A search page with job ids but no readable cards SHALL
be loaded once more after the pacing wait; if it is still unreadable, or if
two postings in a row in a title have no description, that is a title problem:
it SHALL end only that title, keep the postings already read for it, state the
problem in the reader's summary, leave the provider unrecorded as failed, and
let the next title be read normally. Title problems SHALL NOT stop the
provider, however many titles have them. When the same problem has ended every
title that read anything in the run (two at least), the summary SHALL say the
site may have changed.

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

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and LinkedIn goes on with the next title

#### Scenario: Unreadable results page read on retry
- **WHEN** a title's search page has job ids but no readable cards, and the same page loaded again after the pacing wait has them
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: One title's results page stays unreadable
- **WHEN** a title's search page has job ids but no readable cards, also on the retry
- **THEN** that title ends with its postings so far, the summary states the problem, LinkedIn is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with the same title problem
- **THEN** every title is still tried, LinkedIn is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Network failure
- **WHEN** a LinkedIn request fails at the network level
- **THEN** LinkedIn stops for the run with reason `error`, as before

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

### Requirement: Work mode read by the agent
The agent SHALL determine each posting's work mode (onsite, remote, hybrid) by
reading its title and complete description, and SHALL record, in the
posting's language, how the posting describes the arrangement when it says
more than the mode (for example, days on site per week or shortened Fridays).
When neither the title nor the description states the work mode, it SHALL be
left empty and the posting flagged as "work mode not stated"; it SHALL NOT be
guessed from the company, the location, or the search.

#### Scenario: Hybrid with details
- **WHEN** a description says the role is hybrid with two days a week at the office
- **THEN** the posting's work mode is hybrid and its work-mode detail states the two days a week at the office

#### Scenario: Not stated
- **WHEN** neither the title nor the description mentions where the work is done
- **THEN** the work mode is empty, the posting carries a "work mode not stated" flag, and it is not excluded for its work mode

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that LinkedIn's terms prohibit automated access
for logged-out visitors as well as members, that LinkedIn's robots.txt
disallows the guest search, and that the realistic consequence is throttling
or blocking of the user's IP address, so the user can decide whether to
enable it.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/linkedin.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it

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
