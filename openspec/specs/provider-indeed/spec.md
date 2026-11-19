# provider-indeed Specification

## Purpose
Defines how Indeed job postings are searched and read: logged out, through
an ordinary visible browser driven by the system's Indeed reader, with
conservative pacing, and without ever touching the user's Indeed account.

## Requirements

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL open
each job id at most once per run and never for a posting stored by an earlier
run or published outside the run's window. HTTP 429 and a security check that
does not clear ("Security Check", "Verificación de seguridad", "Just a
moment…") SHALL be handled by the provider-throttling policy: waiting and
repeating the load, then a cool-down after which the same run resumes. It
SHALL stop all Indeed work for the rest of the run, record Indeed as blocked,
and refuse later calls on HTTP 403, a block page ("Blocked"), or a sign-in
page. Postings already read are kept. It SHALL stop with reason `error` when
the browser fails. A search page with no results SHALL mean no postings for
that title and nothing else. When the first page of a title has no job-card
data, the reader SHALL load it once more after the pacing wait; if it still
has none, or if two chosen postings in a row in a title show no description
panel, that is a title problem: it SHALL end only that title, keep the
postings already read for it, state the problem in the reader's summary, leave
Indeed unrecorded as failed, and let the next title be read normally. A single
posting without a description panel SHALL be listed as unreadable and the
title SHALL continue. Title problems SHALL NOT stop the provider, however many
titles have them. When the same problem has ended every title that read
anything in the run (two at least), the summary SHALL say the site may have
changed.

#### Scenario: Throttled mid-run
- **WHEN** Indeed keeps showing a security check after the retries while the second title is searched
- **THEN** no further Indeed page is opened until the cool-down ends, the first title's postings remain, and the second title resumes in the same run after the cool-down

#### Scenario: Blocked mid-run
- **WHEN** Indeed shows a block page while the second title is searched
- **THEN** no further Indeed page is opened in that run, Indeed is recorded as blocked, and the first title's postings remain

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** it is not clicked and is recorded as seen

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and Indeed goes on with the next title

#### Scenario: Card data back on retry
- **WHEN** the first page of a title has no job-card data and the same page loaded again after the pacing wait has it
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: One title without card data
- **WHEN** the first page of a title has no job-card data, also on the retry
- **THEN** that title ends with its postings so far, the summary states the problem, Indeed is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with the same title problem
- **THEN** every title is still tried, Indeed is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: One posting without a description panel
- **WHEN** one chosen posting shows no description panel and the next one does
- **THEN** the first is listed as unreadable, the second is drafted, and the title continues

#### Scenario: Browser failure
- **WHEN** the browser itself fails while a title is read
- **THEN** Indeed stops for the run with reason `error`, as before

### Requirement: Posting fields
For each posting the reader SHALL record Indeed's job id as the external id, a
link to the posting, the title, company, and location as given, the
publication date, and the complete description from the side panel as plain
text. Job types and a salary shown on the card SHALL be kept for the agent's
reading. Work mode, its detail, language, flags, and a stated salary SHALL be
the agent's reading of the title and the complete description.

#### Scenario: Complete posting
- **WHEN** a posting's card is read and its side panel opened
- **THEN** its draft carries the job id, link, title, company, location, publication date, and complete description

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that Indeed's terms forbid automated access
without permission, that the reader is automated access that gets past
Indeed's automated checks although it uses no account, and that the realistic
consequence is that Indeed blocks the user's IP address for a while.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/indeed.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it

### Requirement: Logged-out headless session only
The Indeed provider SHALL read Indeed only through the system's Indeed reader,
which drives a headless stealth browser session (Scrapling) with no cookies,
no account, and no sign-in. It SHALL use only Indeed's search page and the
posting side panel that page shows. It SHALL NOT use the user's browser,
session, or Indeed account, and SHALL NOT open posting pages. Because no
account is involved, the session MAY get past Indeed's automated checks; no
browser window opens.

#### Scenario: Normal search
- **WHEN** a search runs with Indeed enabled
- **THEN** the reader opens a fresh headless session with no cookies, no window opens, and every Indeed result comes from the search page and its side panel

#### Scenario: Requests only through the reader
- **WHEN** the agent searches Indeed
- **THEN** it runs the reader command and does not open Indeed by any other means

#### Scenario: A further results page asks to sign in
- **WHEN** a later results page of a title shows a sign-in or security page instead of results
- **THEN** the reader ends that title with the postings already read, says so in its summary, does not record Indeed as blocked, and the next titles are still read
