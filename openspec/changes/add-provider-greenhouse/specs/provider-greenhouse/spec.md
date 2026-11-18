## ADDED Requirements

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
read each posting at most once per run and never one stored by an earlier
run; and SHALL stop Greenhouse for the run when the API refuses requests.

#### Scenario: API refuses requests
- **WHEN** the API answers 403 or 429
- **THEN** Greenhouse is recorded as blocked for the run and the postings already read are kept
