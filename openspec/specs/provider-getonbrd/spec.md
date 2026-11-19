# provider-getonbrd Specification

## Purpose
TBD - created by archiving change add-provider-getonbrd. Update Purpose after archive.

## Requirements

### Requirement: Route chosen by a study
The Get on Board provider SHALL read Get on Board only by the route the owner
chose from this change's study, as stated in `providers/getonbrd.md`, and
SHALL NOT use a route the file marks as not working or forbidden.

#### Scenario: Searching Get on Board
- **WHEN** a search runs with Get on Board enabled
- **THEN** every Get on Board result comes from the route stated in the provider file

### Requirement: Logged out and read-only
The provider SHALL read Get on Board without the user's account and SHALL
NOT apply, save, follow, or change anything on the site.

#### Scenario: Posting with an application form
- **WHEN** a posting offers an application form
- **THEN** the form is not started, filled, or submitted

### Requirement: Verbatim postings with their stated salary
For each posting the provider SHALL record the site's own id, its link, the
title, company, location or remote scope, the publication date when the site
states it, and the complete description verbatim; a salary the posting
states SHALL be kept as a hint for the agent's reading.

#### Scenario: Posting with a salary range
- **WHEN** a posting states a salary range
- **THEN** its record carries the range as the site states it, for the agent to read as the published salary

### Requirement: Remote postings valid for the user's country
A Get on Board search for a title SHALL include the postings in the user's
country, the remote postings open to that country, and the postings remote
from anywhere, and SHALL leave out remote postings limited to other countries.

#### Scenario: Remote from anywhere
- **WHEN** a posting is remote with no country limit and the user's country is PE
- **THEN** it is read for the user, although the site's country filter leaves it out

#### Scenario: Remote limited to another country
- **WHEN** a posting is remote only for Chile and the user's country is PE
- **THEN** it is not read

### Requirement: Not read by the agentic web search
Once Get on Board has its own provider, the agentic web search SHALL NOT read
it, whether the Get on Board provider is enabled or not.

#### Scenario: Web search finds a Get on Board posting
- **WHEN** the agentic web search finds a posting on getonbrd.com
- **THEN** it does not read or import it

### Requirement: The agent installs what an enabled provider needs
Before a search, the agent SHALL install any missing dependency of an enabled
provider into the project's environment, tell the user what it installed, and
search the provider; it SHALL skip the provider only when the installation
fails, saying why. The user SHALL NOT have to install anything by hand.

#### Scenario: Update that needs a new tool
- **WHEN** an update makes an enabled provider need a tool that is not installed
- **THEN** the next search installs it, says so in one line, and searches the provider as usual

#### Scenario: Installation fails
- **WHEN** installing a provider's tool fails
- **THEN** that provider is skipped with the reason and the other providers are searched

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
