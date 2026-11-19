## ADDED Requirements

### Requirement: Salary column with three figures
The salary cell SHALL show, when they exist, the offered salary, the same
company's earlier offered range, and the suggested range with its kind
(company or market) and number of sources; the salary detail SHALL list every
source with its link, the reports set aside and why, and the dates. When none
exists, it SHALL say that there is no salary data and what was checked.

#### Scenario: All three figures
- **WHEN** a posting offers a range, its company offered before, and a company suggestion rests on one source
- **THEN** the cell shows the three figures and the suggestion is marked as company, one source

#### Scenario: Only a market suggestion
- **WHEN** a posting offers no salary and only a market suggestion from three sources exists
- **THEN** the cell shows the market range marked as market, three sources
