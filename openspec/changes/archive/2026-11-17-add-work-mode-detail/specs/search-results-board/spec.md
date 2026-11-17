## MODIFIED Requirements

### Requirement: Results table
The board SHALL list each new posting with its alignment score, title, company,
conditions (contract type, work mode with its detail, and location), suggested
monthly salary, publication date, and a link to the original posting on its
source site. The user SHALL be able to set or correct a posting's work mode and
its detail from its row; the change SHALL be saved immediately, kept when later
searches find the posting again, and shown as set by the user.

#### Scenario: Posting without reliable salary data
- **WHEN** a posting has no stored salary suggestion
- **THEN** the salary cell states that there is no reliable data and shows no amount

#### Scenario: Opening the original posting
- **WHEN** the user activates the source link
- **THEN** the original posting opens in a new browser tab

#### Scenario: Work-mode detail shown
- **WHEN** a posting is hybrid with the detail "2 días presencial por semana"
- **THEN** its conditions cell shows the hybrid work mode together with that detail

#### Scenario: User fills in a missing work mode
- **WHEN** a posting has no work mode and the user sets it to remote with the detail "Early Friday" from its row
- **THEN** the row shows remote with that detail, marked as set by the user, and it persists after reload

#### Scenario: User edit survives a later search
- **WHEN** the user corrected a posting's work mode and a later search finds the same posting
- **THEN** the posting keeps the user's work mode and detail
