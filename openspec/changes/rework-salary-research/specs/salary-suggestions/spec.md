## MODIFIED Requirements

### Requirement: Evidence-gated suggestions
The system SHALL store a suggested salary range of one of two kinds, each with
a source and a link per piece of evidence: a **company** suggestion, from
salary references for the same company and a similar role, which MAY rest on
a single source and SHALL then be labelled as one source; or a **market**
suggestion, for similar roles and industries in the same country and level,
which SHALL rest on at least two pieces of comparable evidence. A market
suggestion SHALL be made only when no company reference exists.

#### Scenario: One source only
- **WHEN** a market suggestion is submitted with a single piece of evidence
- **THEN** it is rejected and the posting shows that there is no reliable data

#### Scenario: Two comparable sources
- **WHEN** a market suggestion is submitted with two comparable, linked pieces of evidence
- **THEN** the suggestion is stored with its amount, range, and confidence

#### Scenario: One company reference
- **WHEN** the only salary reference found is one source for the same company and a similar role
- **THEN** a company suggestion is stored and shown as resting on one source

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

### Requirement: The user's own data as salary evidence
Salaries offered to the user (recorded on applications) and salaries published
in the user's stored postings SHALL count as evidence: for the same company,
in the company's earlier offers; for similar companies and similar positions
under the same conditions (country, level, currency, gross or net, work mode),
as market evidence, each with its reference and link, used before web sources
are searched.

#### Scenario: An offer from a similar company
- **WHEN** the user recorded an offer from another company for the same role family and level, in the same country, currency, basis, and work mode
- **THEN** that offer counts as one market source for the new posting, referenced to its application, and only one web source is still needed

#### Scenario: An offer from the same company
- **WHEN** the user recorded an offer from the same company for a similar role
- **THEN** it appears in the company's earlier offers, marked as offered to the user

### Requirement: Three salary figures per posting
For each posting the system SHALL provide, when they exist: the salary the
posting offers (monthly), what the same company offered for similar roles in
the user's stored postings (range, number of postings, latest date), and the
suggested range with its kind and number of sources.

#### Scenario: Company offered before
- **WHEN** the user's stored postings include two earlier postings of the same company for the same role family with published salaries
- **THEN** the posting shows that company's earlier offered range, from two postings, with the latest date

### Requirement: Outliers set aside with a reason
When a salary source shows several reports, the agent SHALL decide which are
representative and MAY set reports aside as outliers; every report set aside
SHALL be recorded with its value and the reason, and shown in the salary
detail.

#### Scenario: One report far from the rest
- **WHEN** a source shows five reports and one is three times the others
- **THEN** the agent may set it aside, and the detail shows that report and why it was set aside
