## ADDED Requirements

### Requirement: Stop conditions per title
The reader SHALL stop Get on Board for the rest of the run, record it as
failed, and refuse later calls only when the API answers 403 (reason
`blocked`) or when three requests in a row fail without any answer (reason
`error`); HTTP 429 SHALL follow the provider-throttling policy. A search with no results SHALL mean no postings for that title and
nothing else. An answer that is not the expected JSON SHALL be requested once
more after the pacing wait before it counts as unreadable. Three unreadable
answers in a row, when at least one of them was an answer, SHALL be a title
problem: it ends only that title, keeps the postings already read for it,
states the problem in the reader's summary, and leaves Get on Board open for
the next title. Title problems SHALL NOT stop the provider, however many
titles have them; when the same problem has ended every title that read
anything in the run (two at least), the summary SHALL say the site may have
changed.

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and the next title is read normally

#### Scenario: Answer readable on retry
- **WHEN** an answer is not the expected JSON and the same request sent again after the pacing wait is
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: Unreadable answers for one title
- **WHEN** three answers in a row for a title stay unreadable after their retries
- **THEN** that title ends with its postings so far, the summary states the problem, Get on Board is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with unreadable answers
- **THEN** every title is still tried, Get on Board is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Network down
- **WHEN** three requests in a row fail without any answer
- **THEN** Get on Board stops for the run with reason `error`

#### Scenario: API refuses requests
- **WHEN** the API answers 403
- **THEN** Get on Board is recorded as blocked for the run and the postings already read are kept
