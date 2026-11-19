# provider-indeed Specification

## Purpose
Defines how Indeed job postings are searched and read: logged out, through
an ordinary visible browser driven by the system's Indeed reader, with
conservative pacing, and without ever touching the user's Indeed account.

## Requirements

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
