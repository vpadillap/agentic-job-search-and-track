# provider-glassdoor Specification

## Purpose
TBD - created by archiving change add-provider-glassdoor. Update Purpose after archive.

## Requirements

### Requirement: Logged out, through the reader only
The Glassdoor provider SHALL read Glassdoor only through the system's
Glassdoor reader, which uses a stealth browser session with no cookies, no
account, and no sign-in, created for each call and discarded after it. It
SHALL NOT use the user's browser, session, or Glassdoor account, so no account
of the user is ever at risk. Because no account is involved, the reader MAY
work around the site's automated checks. It SHALL NOT call the site's internal
endpoints directly; more results are loaded only through the page's own
"Show more jobs" button.

#### Scenario: Normal search
- **WHEN** a search runs with Glassdoor enabled
- **THEN** the reader opens a new session with no cookies, and every Glassdoor result comes from the search page, its "Show more jobs" results, and the postings' own pages

#### Scenario: Requests only through the reader
- **WHEN** the agent searches Glassdoor
- **THEN** it runs the reader command and does not open Glassdoor by any other means

### Requirement: As many postings as the site lists, up to a cap
The reader SHALL load more results through the page's "Show more jobs" button
until the site shows no more or the provider file's cap is reached, and SHALL
report the site's total and how many postings were listed.

#### Scenario: More results than the first page
- **WHEN** a title has 152 results and the cap is 150
- **THEN** the reader keeps loading more results until the button disappears or 150 are listed, and the run report shows both numbers

### Requirement: Country of the search
The reader SHALL search in the profile's country using a Glassdoor country id
from the provider file's table, from the user's saved setting, or from a
Glassdoor search URL the user pasted, which it SHALL save so the user gives it
once. It SHALL NOT guess an id.

#### Scenario: Country not in the table
- **WHEN** the profile's country has no Glassdoor id in the provider file or the user's settings
- **THEN** the reader reports that it needs one Glassdoor search URL, the agent asks the user, and the id from that URL is used and saved for later runs

### Requirement: Sign-up prompts are dismissed, never answered
When Glassdoor shows a sign-up or sign-in prompt over the page, the reader
SHALL close it without choosing any sign-in option. If it cannot be closed,
the reader SHALL treat it as a sign-in wall.

#### Scenario: Modal after loading more results
- **WHEN** the "Never Miss an Opportunity" modal appears
- **THEN** the reader closes it and continues

#### Scenario: Prompt that cannot be closed
- **WHEN** a sign-in prompt stays open after the reader tries to close it
- **THEN** Glassdoor is recorded as blocked and no further Glassdoor page is opened in that run

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL
open each posting at most once per run and never for a posting stored by an
earlier run or published outside the run's window. HTTP 429 and a security
check that is not passed ("Security | Glassdoor", "Just a moment…",
"Un momento…") SHALL be handled by the provider-throttling policy, for
searches and for salary pages: waiting and repeating the load, then a
cool-down after which the same run resumes. It SHALL stop all Glassdoor work
for the rest of the run, record Glassdoor as blocked, and refuse later calls
on HTTP 403, a Cloudflare block page ("Attention Required"), or a sign-in
wall. It SHALL skip a posting whose page has no readable description, and
SHALL stop with an error after three such postings in a row or when a page
no longer matches what the reader expects. Postings already read are kept.

#### Scenario: Throttled mid-run
- **WHEN** Glassdoor keeps answering 429 after the retries while the second title is searched
- **THEN** no further Glassdoor page is opened until the cool-down ends, the first title's postings remain, and the second title resumes in the same run after the cool-down

#### Scenario: Blocked mid-run
- **WHEN** Glassdoor shows a sign-in wall that does not close while the second title is searched
- **THEN** no further Glassdoor page is opened in that run, Glassdoor is recorded as blocked, and the first title's postings remain

#### Scenario: Throttled salary page
- **WHEN** a salary page answers 429 and keeps doing so after the retries
- **THEN** the salary reader answers that it was throttled, with the time it may be tried again, and records no evidence

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** its page is not opened and it is recorded as seen

#### Scenario: Posting without a description
- **WHEN** a posting's page has no readable description
- **THEN** that posting is skipped with a note and the reader continues with the next one

### Requirement: Posting fields
For each posting the reader SHALL record Glassdoor's listing id as the
external id, the posting's link, the title, company, and location as given,
the publication date, and the complete description from the posting's own
structured data as plain text. Attributes, employment type, and a salary the
posting states SHALL be kept as hints for the agent's reading. Work mode,
contract type, language, flags, and a stated salary SHALL be the agent's
reading of the title and description.

#### Scenario: Complete posting
- **WHEN** a new posting's page is read
- **THEN** its draft carries the listing id, link, title, company, location, publication date, and complete description

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

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that Glassdoor's terms forbid automated access
without permission, that the reader is automated access that gets past the
site's automated checks although it uses no account, and that the realistic
consequence is that Glassdoor blocks the user's IP address for a while.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/glassdoor.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it
