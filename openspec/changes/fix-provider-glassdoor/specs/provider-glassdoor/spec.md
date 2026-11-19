## ADDED Requirements

### Requirement: Search results come from the page's data, with fallbacks
The reader SHALL take a search's results from the page's own embedded data
when it is present, otherwise from the page's JSON-LD list of postings,
otherwise from the posting cards, otherwise from links to posting pages. It
SHALL never count a posting in the "Similar jobs" section as a result. When
the page's data lists no results, the page shows Glassdoor's "limited or no
results" notice, or the site reports 0 results, the reader SHALL end that
title as having no results, without an error.

#### Scenario: Cards renamed, data intact
- **WHEN** a search page's cards no longer have the expected markup but its embedded data lists 3 postings
- **THEN** the reader reads those 3 postings

#### Scenario: Only similar jobs
- **WHEN** a search page says "1 job" in its title, its data lists no postings, and it shows 5 cards under "Similar jobs"
- **THEN** the title ends with no results, no posting is opened, and Glassdoor goes on with the next title

## MODIFIED Requirements

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
wall, and SHALL stop with an error when the browser fails. A search page from
which no results can be read, and which does not show that there are none,
SHALL be loaded once more; if it still cannot be read, only that title SHALL
end, with a note naming the capture. It SHALL skip a posting whose page has
no readable description, and SHALL end only that title after two such
postings in a row. A "Show more jobs" response that does not parse SHALL be
counted and its cards still read. Problems with a title SHALL NOT stop
Glassdoor: every title of the run SHALL be tried. When this title and every
earlier title of the run that read something ended with the same kind of
problem (two at least), the reader SHALL report that the site may have
changed, without stopping. Postings already read are kept.

#### Scenario: Throttled mid-run
- **WHEN** Glassdoor keeps answering 429 after the retries while the second title is searched
- **THEN** no further Glassdoor page is opened until the cool-down ends, the first title's postings remain, and the second title resumes in the same run after the cool-down

#### Scenario: Blocked mid-run
- **WHEN** Glassdoor shows a sign-in wall that does not close while the second title is searched
- **THEN** no further Glassdoor page is opened in that run, Glassdoor is recorded as blocked, and the first title's postings remain

#### Scenario: Throttled salary page
- **WHEN** a salary page answers 429 and keeps doing so after the retries
- **THEN** the salary reader answers that it was throttled, with the time it may be tried again, and records no evidence

#### Scenario: Unreadable search page
- **WHEN** the first title's search page has no results the reader can read and no sign that there are none, also when loaded a second time
- **THEN** that title ends with a note naming the capture, Glassdoor is not stopped, and the next title is searched

#### Scenario: Search page readable on the second load
- **WHEN** a search page cannot be read the first time and can the second time
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: Every title is tried
- **WHEN** two titles of a run end with unreadable search pages, with a title that had no results between them
- **THEN** Glassdoor is not stopped, the next title is still searched, and the summary says the site may have changed

#### Scenario: Two postings without a description in a row
- **WHEN** a title's second and third postings have no readable description
- **THEN** that title ends with the first posting kept, and the next title is searched

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** its page is not opened and it is recorded as seen

#### Scenario: Posting without a description
- **WHEN** a posting's page has no readable description
- **THEN** that posting is skipped with a note and the reader continues with the next one

### Requirement: Salary reports as evidence
The Glassdoor provider SHALL read the salary page for a title and country
logged out and SHALL return one salary evidence draft with the source, link,
the most likely range (25th to 75th percentile), currency, period, sample
size, and date, taken from the page's structured data. It SHALL NOT store the
evidence by itself, SHALL NOT take figures from the page's prose, and SHALL
report no data when the structured data is missing. It SHALL accept up to
three titles, try them in order until one has data, and list every page it
tried. It SHALL wait at least 20 seconds between salary pages, also across
calls. When a salary page is still refused after the provider-throttling
waits (429 or a security check), or answers 403, it SHALL
record a salary cool-down of at least what the site's `Retry-After` asks and
at least 15 minutes, doubling for each further refusal up to 60 minutes
(longer only when `Retry-After` asks), reset after a page that loads; until
the cool-down ends it SHALL open no salary page and SHALL answer that it is
throttled, with the time it may be tried again. It SHALL NOT use proxies, a
changed browser identity, or the user's account to get past a refusal.

#### Scenario: Salary page with data
- **WHEN** the agent asks for Glassdoor salaries for a title in Peru and the page has its salary distribution
- **THEN** it receives a draft with the 25th–75th percentile range, currency PEN, period, sample size, link, and date, and stores it only after checking comparability

#### Scenario: Salary page without data
- **WHEN** the salary page has no salary distribution
- **THEN** the result says there is no Glassdoor data and no figure is produced

#### Scenario: Spanish title first, English equivalent second
- **WHEN** the agent asks with "Jefe de Marca" and then "Brand Manager", and only the second page has data
- **THEN** both pages are tried 20 seconds apart, the evidence comes from the second, and the result lists both pages

#### Scenario: Throttled salary page
- **WHEN** a salary page answers 429 with `Retry-After: 1800`, longer than a wait within a call
- **THEN** the answer says Glassdoor is throttled until 30 minutes later, no further title is tried, no evidence is produced, and a salary call before that time opens no page

#### Scenario: Cool-down grows and resets
- **WHEN** salary pages are refused twice in a row without `Retry-After`, and later a page loads
- **THEN** the cool-downs are 15 and then 30 minutes, and the next refusal after the page that loaded is 15 minutes again
