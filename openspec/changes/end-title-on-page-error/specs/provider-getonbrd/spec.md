## ADDED Requirements

### Requirement: Stop conditions per title
The reader SHALL stop Get on Board for the rest of the run, record it as
failed, and refuse later calls when the API answers 403 or 429 (reason
`blocked`), when three requests in a row fail without any answer (reason
`error`), or when the same title problem occurs on two titles in a row
(reason `error`, naming both titles). Three answers in a row that are not
the expected JSON, when at least one of them was an answer, SHALL be a title
problem: it ends only that title, keeps the postings already read for it,
states the problem in the reader's summary, and leaves Get on Board open for
the next title. A title that read at least one results page cleanly resets
the count; a title with no results does not. A search with no results is not
an error.

#### Scenario: Unreadable answers for one title
- **WHEN** three answers in a row for the second title are not the expected JSON and the first title was read cleanly
- **THEN** the second title ends with its postings so far, the summary states the problem, Get on Board is not recorded as failed, and the third title is read normally

#### Scenario: The same problem on two titles in a row
- **WHEN** two consecutive titles each end with three unreadable answers in a row
- **THEN** Get on Board stops for the run with reason `error`, the detail names both titles, and later calls are refused

#### Scenario: Network down
- **WHEN** three requests in a row fail without any answer
- **THEN** Get on Board stops for the run with reason `error`

#### Scenario: API refuses requests
- **WHEN** the API answers 403 or 429
- **THEN** Get on Board is recorded as blocked for the run and the postings already read are kept
