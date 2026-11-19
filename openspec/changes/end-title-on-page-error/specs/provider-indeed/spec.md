## MODIFIED Requirements

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
