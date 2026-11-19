## MODIFIED Requirements

### Requirement: Verbatim drafts and pacing
For each posting the reader SHALL record the posting id, its link, title,
company, location, publication date, the complete description as plain text,
and the form questions; SHALL wait at least 5 seconds between requests; SHALL
read each posting at most once per run and never one stored by an earlier
run; and SHALL stop Greenhouse for the run only when the API refuses
requests or when three requests in a row fail without any answer. A title
with nothing to read SHALL mean no postings for that title and nothing else.
An answer that is not the expected JSON SHALL be requested once more after
the pacing wait before it counts as unreadable. Three unreadable answers in a
row, when at least one of them was an answer, SHALL be a title problem: it
ends only that title's remaining boards and postings, keeps the postings
already read and the boards remembered, states the problem in the reader's
summary, and leaves Greenhouse open for the next title. Title problems SHALL
NOT stop the provider, however many titles have them; when the same problem
has ended every title that read anything in the run (two at least), the
summary SHALL say the site may have changed.

#### Scenario: API refuses requests
- **WHEN** the API answers 403 or 429
- **THEN** Greenhouse is recorded as blocked for the run and the postings already read are kept

#### Scenario: Titles with nothing to read
- **WHEN** three titles in a row find no matching postings
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and the next title is read normally

#### Scenario: Answer readable on retry
- **WHEN** an answer is not the expected JSON and the same request sent again after the pacing wait is
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: Unreadable answers for one title
- **WHEN** three answers in a row for a title stay unreadable after their retries
- **THEN** that title ends with its postings so far, the boards found are still remembered, Greenhouse is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with unreadable answers
- **THEN** every title is still tried, Greenhouse is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Network down
- **WHEN** three requests in a row fail without any answer
- **THEN** Greenhouse stops for the run with reason `error`
