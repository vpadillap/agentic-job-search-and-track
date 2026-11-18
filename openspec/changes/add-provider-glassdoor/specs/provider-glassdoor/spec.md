## ADDED Requirements

### Requirement: Logged-out visible browser only
The Glassdoor provider SHALL read Glassdoor only through the system's
Glassdoor reader, which drives an ordinary visible Chromium with a fresh
profile: no cookies, no account, no sign-in. It SHALL use only Glassdoor's
search page and the posting side panel that page shows. It SHALL NOT use plain
HTTP, a headless browser, the user's browser or session, the site's internal
endpoints, stealth tools, proxies, or anything meant to get around
Glassdoor's checks.

#### Scenario: Normal search
- **WHEN** a search runs with Glassdoor enabled
- **THEN** the reader opens a fresh visible browser with no cookies, and every Glassdoor result comes from the search page and its side panel

#### Scenario: Requests only through the reader
- **WHEN** the agent searches Glassdoor
- **THEN** it runs the reader command and does not open Glassdoor by any other means

### Requirement: Sign-up prompts are dismissed, never answered
When Glassdoor shows a sign-up or sign-in prompt over the page, the reader
SHALL close it without choosing any sign-in option. If it cannot be closed,
the reader SHALL treat it as a sign-in wall.

#### Scenario: Modal after a few postings
- **WHEN** the "Never Miss an Opportunity" modal appears after a click
- **THEN** the reader closes it and continues reading the remaining postings

#### Scenario: Prompt that cannot be closed
- **WHEN** a sign-in prompt stays open after the reader tries to close it
- **THEN** Glassdoor is recorded as blocked and no further Glassdoor page is opened in that run

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL
open each posting at most once per run and never for a posting stored by an
earlier run or published outside the run's window. It SHALL stop all
Glassdoor work for the rest of the run, record Glassdoor as blocked, and
refuse later calls on a block page, a security check that does not clear, or
a sign-in wall. It SHALL stop with an error when a page no longer matches
what the reader expects. Postings already read are kept.

#### Scenario: Blocked mid-run
- **WHEN** Glassdoor shows a security page while the second title is searched
- **THEN** no further Glassdoor page is opened in that run, Glassdoor is recorded as blocked, and the first title's postings remain

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** it is not clicked and is recorded as seen

### Requirement: Posting fields
For each posting the reader SHALL record Glassdoor's listing id as the
external id, a link to the posting, the title, company, and location as
given, the publication date, and the complete description from the side
panel as plain text. Attributes and a salary shown on the card SHALL be kept
for the agent's reading. Work mode, contract type, language, flags, and a
stated salary SHALL be the agent's reading of the title and description.

#### Scenario: Complete posting
- **WHEN** a posting's card is read and its side panel opened
- **THEN** its draft carries the listing id, link, title, company, location, publication date, and complete description

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that Glassdoor's terms forbid automated access
without permission, that the reader is still automated access although it
uses an ordinary browser and no account, and that the realistic consequence
is that Glassdoor blocks the user's IP address for a while.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/glassdoor.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it
