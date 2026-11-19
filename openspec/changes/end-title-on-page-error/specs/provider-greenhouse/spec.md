## MODIFIED Requirements

### Requirement: Verbatim drafts and pacing
For each posting the reader SHALL record the posting id, its link, title,
company, location, publication date, the complete description as plain text,
and the form questions; SHALL wait at least 5 seconds between requests; SHALL
read each posting at most once per run and never one stored by an earlier run;
SHALL handle HTTP 429 by the provider-throttling policy (waiting, honouring
`Retry-After`, then a cool-down after which the same run resumes); and SHALL
stop Greenhouse for the run when the API answers 403. It SHALL also stop
Greenhouse for the run, with reason `error`, when three requests in a row fail
without any answer. A title with nothing to read SHALL mean no postings for
that title and nothing else. An answer that is not the expected JSON SHALL be
requested once more after the pacing wait before it counts as unreadable.
Three unreadable answers in a row, when at least one of them was an answer,
SHALL be a title problem: it ends only that title's remaining boards and
postings, keeps the postings already read and the boards remembered, states
the problem in the reader's summary, and leaves Greenhouse open for the next
title. Title problems SHALL NOT stop the provider, however many titles have
them. When the same problem has ended every title that read anything in the
run (two at least), the summary SHALL say the site may have changed.

#### Scenario: API refuses requests
- **WHEN** the API answers 403
- **THEN** Greenhouse is recorded as blocked for the run and the postings already read are kept

#### Scenario: API throttles requests
- **WHEN** the API answers 429 with `Retry-After: 30` and the repeat succeeds
- **THEN** the repeat is sent no sooner than 30 seconds later and the reader goes on with the board

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and Greenhouse goes on with the next title

#### Scenario: Answer readable on retry
- **WHEN** an answer is not the expected JSON and the same request sent again after the pacing wait is
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: Unreadable answers for one title
- **WHEN** three answers in a row for a title are not the expected JSON, also on the retry
- **THEN** that title ends with its postings so far, the summary states the problem, Greenhouse is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with the same title problem
- **THEN** every title is still tried, Greenhouse is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Network down
- **WHEN** three requests in a row fail without any answer
- **THEN** Greenhouse stops for the run with reason `error`
