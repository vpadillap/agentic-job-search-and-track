## MODIFIED Requirements

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

## ADDED Requirements

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
