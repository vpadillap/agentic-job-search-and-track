# salary-suggestions Specification

## Purpose
Defines the monthly salary recommendation for a posting and the evidence
standard it must meet, so the user never receives an invented figure.

## Requirements

### Requirement: Evidence-gated suggestions
The system SHALL store a suggested salary range only with at least one cited
source and a short note, written by the agent, that justifies it. A suggestion
resting on references for the same company or on the user's own history
(salaries offered to the user, salaries published in stored postings) MAY rest
on one source; a suggestion resting only on market evidence SHALL rest on at
least two comparable sources. The suggestion SHALL state how many sources of
each kind support it.

#### Scenario: One source only
- **WHEN** a suggestion is submitted with a single piece of market evidence and nothing else
- **THEN** it is rejected and the posting shows that there is no reliable data

#### Scenario: Two comparable sources
- **WHEN** a suggestion is submitted with two comparable, linked pieces of market evidence and a note
- **THEN** the suggestion is stored with its amount, range, confidence, and note

#### Scenario: One offer from a similar company
- **WHEN** the agent's suggestion rests on one salary offered to the user by a company of similar industry, size, and level, with a note saying so
- **THEN** the suggestion is stored and shown as resting on one source from the user's history

### Requirement: Comparability
Evidence SHALL count as comparable only when it matches the posting's country
and seniority level and is in the same currency, and SHALL record work mode,
industry, and company size so the user can judge it.

#### Scenario: Different country
- **WHEN** evidence refers to another country
- **THEN** it does not count toward the two required sources

#### Scenario: Outdated evidence
- **WHEN** evidence is older than 18 months
- **THEN** it does not count toward the two required sources

### Requirement: Transparent figures
A suggestion SHALL state a monthly amount, its currency, whether it is gross or
net, the observed range, a confidence level, and the list of evidence.

#### Scenario: Viewing a suggestion
- **WHEN** the user opens a posting's salary detail
- **THEN** the amount, range, confidence, and each evidence source with its link are shown

### Requirement: Explicit absence of data
When research finds insufficient evidence the system SHALL record that no
reliable data exists and what was checked, and SHALL NOT derive a figure from
loosely related data.

#### Scenario: Research without results
- **WHEN** salary research for a posting finds no comparable evidence
- **THEN** the posting is marked as having no reliable salary data and no amount is shown anywhere

### Requirement: Evidence reuse
The system SHALL reuse stored evidence instead of researching again: market
evidence for every posting with the same role family, level, country, and
currency for 30 days, whatever the company; company evidence for postings of
the same company, role family, and country for 60 days; and a recorded "no
data" for the same key and source for the same periods.

#### Scenario: Second posting at the same company
- **WHEN** a new posting matches recent stored evidence for the same company and role
- **THEN** the suggestion is produced from the stored evidence

#### Scenario: Same role at another company
- **WHEN** a new posting at another company has the same role family, level, and country as recent market evidence
- **THEN** that market evidence is reused and the market sources are not searched again

#### Scenario: Recently nothing found
- **WHEN** a source found nothing for a key in the reuse period
- **THEN** that source is not searched again for that key

### Requirement: The agent analyses all available data
For each posting the system SHALL give the agent, in one answer and without
searching, everything available: the offered salary, the user's history
(salaries offered to the user and salaries published in stored postings, each
with its company profile, level, country, work mode, and date), and fresh
stored evidence with what was already checked. The agent SHALL search only
what is missing, weigh data from the same company more, otherwise extrapolate
from similar companies (industry, size, type, level), and record which inputs
it used.

#### Scenario: No data from the same company
- **WHEN** the user's history has offers and published salaries only from other companies
- **THEN** the agent uses those of similar companies, says so in the note, and lists them as the inputs used

#### Scenario: Nothing missing
- **WHEN** fresh stored evidence and the user's history are enough for the agent's suggestion
- **THEN** no salary source is searched for that posting

### Requirement: Company profiles
The system SHALL keep for each company the user meets a profile (industry,
size band, type) taken from the posting's text or a linked source, with that
source recorded, or "unknown"; it SHALL NOT come from the model's own
knowledge.

#### Scenario: Profile from a linked source
- **WHEN** the agent records a company's size band from the company's page on a job site
- **THEN** the profile stores the size band with that page's link and is reused for that company's later postings

### Requirement: Outliers set aside with a reason
When a salary source shows several reports, the agent SHALL decide which are
representative and MAY set reports aside as outliers; every report set aside
SHALL be recorded with its value and the reason, and shown in the salary
detail.

#### Scenario: One report far from the rest
- **WHEN** a source shows five reports and one is three times the others
- **THEN** the agent may set it aside, and the detail shows that report and why it was set aside

### Requirement: Salary sources are always available
Salary sources SHALL NOT be switched on or off: a salary-only source SHALL be
refused by the switch, and the salary pages of a job site that is also a
salary source SHALL be usable whether or not its job search is on. For each
posting the system SHALL tell the agent which salary sources serve the
posting's country, whether their tools are ready, and what each already
answered for the posting's keys; the agent SHALL ask the ones that fit.

#### Scenario: A user who never turned anything on
- **WHEN** the agent researches the salary of a posting in a country two salary sources serve
- **THEN** both are listed for that posting and the agent may ask them, without any switch

#### Scenario: Trying to switch a salary source
- **WHEN** the user or the agent tries to turn a salary-only source off
- **THEN** it is refused with a message saying salary sources are always used

#### Scenario: A job site whose search is off
- **WHEN** a job site that is also a salary source has its job search turned off
- **THEN** its salary pages are still listed and usable for salary research
