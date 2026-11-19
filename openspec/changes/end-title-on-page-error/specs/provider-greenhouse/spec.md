## MODIFIED Requirements

### Requirement: Verbatim drafts and pacing
For each posting the reader SHALL record the posting id, its link, title,
company, location, publication date, the complete description as plain text,
and the form questions; SHALL wait at least 5 seconds between requests; SHALL
read each posting at most once per run and never one stored by an earlier
run; and SHALL stop Greenhouse for the run when the API refuses requests,
when three requests in a row fail without any answer, or when the same title
problem occurs on two titles in a row. Three answers in a row that are not
the expected JSON, when at least one of them was an answer, SHALL be a title
problem: it ends only that title's remaining boards and postings, keeps the
postings already read and the boards remembered, states the problem in the
reader's summary, and leaves Greenhouse open for the next title. A title that
read at least one board or posting cleanly resets the count; a title with
nothing to read does not.

#### Scenario: API refuses requests
- **WHEN** the API answers 403 or 429
- **THEN** Greenhouse is recorded as blocked for the run and the postings already read are kept

#### Scenario: Unreadable answers for one title
- **WHEN** three answers in a row for the second title are not the expected JSON and the first title was read cleanly
- **THEN** the second title ends with its postings so far, the boards found are still remembered, Greenhouse is not recorded as failed, and the third title is read normally

#### Scenario: The same problem on two titles in a row
- **WHEN** two consecutive titles each end with three unreadable answers in a row
- **THEN** Greenhouse stops for the run with reason `error`, the detail names both titles, and later calls are refused

#### Scenario: Network down
- **WHEN** three requests in a row fail without any answer
- **THEN** Greenhouse stops for the run with reason `error`
