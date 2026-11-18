## ADDED Requirements

### Requirement: Logged-out visible browser only
The Glassdoor provider SHALL read Glassdoor only through the system's
Glassdoor reader, which drives an ordinary visible Chromium with a fresh
profile: no cookies, no account, no sign-in. It SHALL NOT use the user's
browser, session, or Glassdoor account, so no account of the user is ever at
risk. Because no account is involved, the reader MAY work around the site's
automated checks (for example, a new context for each search). The routes the
study found not to work (plain HTTP, a headless browser, the site's internal
endpoints, posting pages, page 2) SHALL NOT be used.

#### Scenario: Normal search
- **WHEN** a search runs with Glassdoor enabled
- **THEN** the reader opens a fresh visible browser with no cookies, and every Glassdoor result comes from the search page and its side panel

#### Scenario: Requests only through the reader
- **WHEN** the agent searches Glassdoor
- **THEN** it runs the reader command and does not open Glassdoor by any other means

### Requirement: One search per fresh browser context
The reader SHALL make at most one search request (one search or salary page
load) per browser context and SHALL open a new context with no cookies for
each further search. It SHALL NOT use page 2 of a search, the site's "show
more" control, or posting pages, and SHALL read at most 30 postings per title
per run, reporting when a title has more.

#### Scenario: Two titles
- **WHEN** a run searches two titles on Glassdoor
- **THEN** each title is loaded as the first page of its own new context

#### Scenario: More than 30 results
- **WHEN** a title's search reports more than 30 results
- **THEN** at most 30 postings are read and the run report says the title was cut off

### Requirement: Country of the search
The reader SHALL search in the profile's country using a Glassdoor country id
from the provider file's table or from a Glassdoor search URL the user
pasted, and SHALL NOT guess an id.

#### Scenario: Country not in the table
- **WHEN** the profile's country has no Glassdoor id in the provider file
- **THEN** the agent asks the user for one Glassdoor search URL from their browser and the reader uses the id in it

### Requirement: Salary reports as evidence
The Glassdoor provider SHALL read the salary page for a title and country
logged out and SHALL return one salary evidence draft with the source, link,
the most likely range (25th to 75th percentile), currency, period, sample
size, and date, taken from the page's structured data. It SHALL NOT store the
evidence by itself, SHALL NOT take figures from the page's prose, and SHALL
report no data when the structured data is missing.

#### Scenario: Salary page with data
- **WHEN** the agent asks for Glassdoor salaries for a title in Peru and the page has its salary distribution
- **THEN** it receives a draft with the 25th–75th percentile range, currency PEN, period, sample size, link, and date, and stores it only after checking comparability

#### Scenario: Salary page without data
- **WHEN** the salary page has no salary distribution
- **THEN** the result says there is no Glassdoor data and no figure is produced

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
