# provider-greenhouse Specification

## Purpose
TBD - created by archiving change add-provider-greenhouse. Update Purpose after archive.

## Requirements

### Requirement: Postings read through the public Job Board API
The Greenhouse provider SHALL read postings and their application-form
questions only through Greenhouse's public Job Board API, without signing in,
and SHALL NOT submit, save, or change anything on Greenhouse.

#### Scenario: Reading a company board
- **WHEN** the reader is given a Greenhouse board for a title
- **THEN** it reads that board's current postings through the public API and keeps those that match the title, the user's country, and the run's window

#### Scenario: Posting with form questions
- **WHEN** a kept posting has application-form questions
- **THEN** the questions are captured with the posting and nothing is submitted

### Requirement: Companies found by the signed-in search or by web search
The agent SHALL find Greenhouse postings and boards through the MyGreenhouse
candidate search in the user's own browser only when the user said in the
conversation that they are present and signed in; otherwise it SHALL find
boards by web search over Greenhouse's board addresses. The agent SHALL NOT
type credentials, SHALL NOT read or store the signed-in user's account data,
and SHALL NOT apply, save jobs, or set alerts in the user's account.

#### Scenario: User present and signed in
- **WHEN** the user says they are present and signed in to MyGreenhouse in their Chrome
- **THEN** the agent searches the title in the user's country there, collects the posting links, and the reader reads those postings through the public API

#### Scenario: Unattended run
- **WHEN** the user is not present
- **THEN** the agent finds boards by web search and the run continues without the user

#### Scenario: Sign-in page during the signed-in search
- **WHEN** MyGreenhouse asks to sign in
- **THEN** the agent does not sign in and uses web search instead

### Requirement: Boards are remembered
The reader SHALL remember, per user, every board it read with postings in the
user's country, SHALL recheck remembered boards in later runs, and SHALL drop
a board that no longer exists.

#### Scenario: Later run
- **WHEN** a run searches a title and earlier runs found boards with postings in the user's country
- **THEN** those boards are read again through the API even if this run's discovery did not find them

#### Scenario: Board gone
- **WHEN** a remembered board answers that it does not exist
- **THEN** it is removed from the remembered boards and the run continues

### Requirement: Country and title of board postings
The reader SHALL keep a board posting only when its title contains the
searched title's words (seniority words aside) and its location is in the
user's country or is remote for the user's region, using place words from the
provider file or given once by the user; it SHALL NOT guess place words for a
country it does not know.

#### Scenario: Country not known
- **WHEN** the profile's country has no place words in the provider file or the user's settings
- **THEN** the reader asks for them through the agent and saves the words the user gives

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
