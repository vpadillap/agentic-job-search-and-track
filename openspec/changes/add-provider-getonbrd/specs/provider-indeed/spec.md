## RENAMED Requirements

- FROM: `### Requirement: Logged-out visible browser only`
- TO: `### Requirement: Logged-out headless session only`

## MODIFIED Requirements

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
- **WHEN** a later results page of a title shows a sign-in page instead of results
- **THEN** the reader ends that title with the postings already read, says so in its summary, and does not record Indeed as blocked

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that Indeed's terms forbid automated access
without permission, that the reader is automated access that gets past
Indeed's automated checks although it uses no account, and that the realistic
consequence is that Indeed blocks the user's IP address for a while.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/indeed.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it
