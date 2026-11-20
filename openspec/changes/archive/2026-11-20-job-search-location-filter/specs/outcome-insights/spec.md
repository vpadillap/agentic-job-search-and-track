## ADDED Requirements

### Requirement: Restored postings in the history
The history given to the agent SHALL include every posting the user restored
from the filtered-out list, as a correction of the filter, with the reason and
detail it had been filtered out for, the site, and the date of the restore.

#### Scenario: Restore recorded
- **WHEN** the user restores a posting filtered out for "location" with the detail "Onsite in Arequipa"
- **THEN** the next history given to the agent lists it as a filter correction with that reason and detail
