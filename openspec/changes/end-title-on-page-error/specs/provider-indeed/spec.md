## MODIFIED Requirements

### Requirement: Pacing and stop conditions
The reader SHALL wait at least 5 seconds between page loads and clicks, also
across calls in the same run; SHALL run one call at a time per run; SHALL
open each job id at most once per run and never for a posting stored by an
earlier run or published outside the run's window. It SHALL stop all Indeed
work for the rest of the run, record Indeed as blocked, and refuse later calls
when the first page of a title is a block page, a security check that does
not clear, or a sign-in page. It SHALL stop with reason `error` when the
browser fails, and when the same title problem occurs on two titles in a row.
A title problem (the first page of a title has no job-card data, or two
chosen postings in a row in a title show no description panel) SHALL end
only that title: the postings already read for it are kept, the reader's
summary states the problem, Indeed is not recorded as failed, and the next
title is read normally. A single posting without a description panel SHALL be
listed as unreadable and the title SHALL continue. A title that read at least
one results page cleanly resets the count; a title with no results does not.
Postings already read are kept.

#### Scenario: Blocked mid-run
- **WHEN** Indeed shows a block page while the second title is searched
- **THEN** no further Indeed page is opened in that run, Indeed is recorded as blocked, and the first title's postings remain

#### Scenario: One title without card data
- **WHEN** the first page of the second title has no job-card data and the first title was read cleanly
- **THEN** the second title ends, the summary states the problem, Indeed is not recorded as failed, and the third title is read normally

#### Scenario: The same problem on two titles in a row
- **WHEN** the first pages of two consecutive titles both have no job-card data
- **THEN** Indeed stops for the run with reason `error`, the detail names both titles, and later calls are refused

#### Scenario: One posting without a description panel
- **WHEN** one chosen posting shows no description panel and the next one does
- **THEN** the first is listed as unreadable, the second is drafted, and the title continues

#### Scenario: Browser failure
- **WHEN** the browser itself fails while a title is read
- **THEN** Indeed stops for the run with reason `error`, as before

#### Scenario: Posting already stored
- **WHEN** the search lists a posting an earlier run stored
- **THEN** it is not clicked and is recorded as seen
