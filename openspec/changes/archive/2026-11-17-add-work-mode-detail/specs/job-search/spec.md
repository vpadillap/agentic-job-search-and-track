## MODIFIED Requirements

### Requirement: First-pass filter with reasons
The search SHALL exclude postings that clearly violate a hard constraint of the
profile or an active rule, SHALL record the reason for each exclusion, and
SHALL keep ambiguous postings with a visible flag instead of excluding them. A
posting whose work mode is not stated SHALL NOT be excluded for its work mode.

#### Scenario: Wrong work mode
- **WHEN** a posting is onsite-only and the profile accepts remote only
- **THEN** it is stored as filtered out with the reason "work mode"

#### Scenario: Ambiguous seniority
- **WHEN** a posting's seniority appears lower than the user's but is not stated clearly
- **THEN** it stays in the results with a flag describing the doubt

#### Scenario: Work mode not stated
- **WHEN** neither the title nor the description of a posting says where the work is done, and the profile accepts remote only
- **THEN** the posting stays in the results with a flag saying the work mode is not stated

### Requirement: Verbatim capture
The search SHALL store each posting's description exactly as published, its
link, and its publication date as an absolute date. It SHALL also store the
posting's work mode (remote, hybrid, or onsite) and, when the posting says
more about the arrangement, a work-mode detail in the posting's language, both
as read by the agent from the title and the complete description; neither is
guessed when the posting does not state it.

#### Scenario: Relative date
- **WHEN** a site shows "2 days ago" for a posting
- **THEN** the stored publication date is the corresponding calendar date

#### Scenario: Hybrid with days on site
- **WHEN** a Spanish posting says the role is hybrid with two days a week at the office
- **THEN** the posting is stored with work mode hybrid and a Spanish detail stating two days a week on site

#### Scenario: Arrangement beyond the mode
- **WHEN** a remote posting mentions shortened Fridays in summer
- **THEN** the posting is stored as remote with a detail that mentions the shortened summer Fridays
