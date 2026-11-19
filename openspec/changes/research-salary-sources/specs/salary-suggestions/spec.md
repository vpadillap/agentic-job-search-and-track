## ADDED Requirements

### Requirement: Every salary source is tried before "no reliable data"
Before recording that a posting has no reliable salary data, the agent SHALL
try every salary source available to the user (the posting itself, enabled
salary providers, and comparable published salaries in the user's stored
postings) and SHALL record which ones it checked and why each did not count.

#### Scenario: One source short
- **WHEN** only one comparable source is found for a posting after trying every available source
- **THEN** the posting shows "no reliable data" with the list of sources checked and the reason each did not count

#### Scenario: Stored postings complete the evidence
- **WHEN** a salary provider gives one comparable source and the user's stored postings hold a comparable published salary
- **THEN** both are stored as evidence and a suggestion is made from them
