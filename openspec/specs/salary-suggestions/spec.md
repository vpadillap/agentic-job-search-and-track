# salary-suggestions Specification

## Purpose
Defines the monthly salary recommendation for a posting and the evidence
standard it must meet, so the user never receives an invented figure.

## Requirements

### Requirement: Evidence-gated suggestions
The system SHALL store a salary suggestion only when it is supported by at
least two pieces of comparable evidence, each with a source and a link.

#### Scenario: One source only
- **WHEN** a suggestion is submitted with a single piece of evidence
- **THEN** it is rejected and the posting shows that there is no reliable data

#### Scenario: Two comparable sources
- **WHEN** a suggestion is submitted with two comparable, linked pieces of evidence
- **THEN** the suggestion is stored with its amount, range, and confidence

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
The system SHALL reuse stored evidence for postings with the same company,
role, and location for a limited period instead of researching again.

#### Scenario: Second posting at the same company
- **WHEN** a new posting matches recent stored evidence for the same company and role
- **THEN** the suggestion is produced from the stored evidence
