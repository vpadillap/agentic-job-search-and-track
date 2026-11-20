## MODIFIED Requirements

### Requirement: First-pass filter with reasons
The search SHALL exclude postings that clearly violate a hard constraint of the
profile or an active rule, SHALL record the reason for each exclusion, and
SHALL keep ambiguous postings with a visible flag instead of excluding them.

A posting that does not say it is remote, and whose title and description do
not let the agent conclude that it is fully remote, SHALL be treated as having
some on-site presence for filtering; its captured work mode stays not stated,
with its flag. When the profile accepts remote only, such a posting SHALL be
excluded with the reason "work mode" and a detail saying it does not state
that it is remote.

For a posting that is onsite, hybrid, or treated as having on-site presence,
the agent SHALL read where the work is done (the posting's location and, when
it names the workplace, its description) and SHALL exclude it with the reason
"location" when that place is clearly outside every place in the profile's
accepted locations. Places SHALL be compared by meaning, not by text: a
district or neighbourhood belongs to its city, and a region or province that
shares a city's name is not that city. When the place cannot be told (only the
country, no place at all) or lies inside a saved city but outside the
districts the user listed, the posting SHALL be kept with a flag. A posting
that is remote SHALL NOT be excluded for its location.

A posting the user restored from the filtered-out list SHALL NOT be filtered
out again, by this run or any later one.

#### Scenario: Wrong work mode
- **WHEN** a posting is onsite-only and the profile accepts remote only
- **THEN** it is stored as filtered out with the reason "work mode"

#### Scenario: Ambiguous seniority
- **WHEN** a posting's seniority appears lower than the user's but is not stated clearly
- **THEN** it stays in the results with a flag describing the doubt

#### Scenario: Work mode not stated
- **WHEN** neither the title nor the description of a posting says where the work is done, and the profile accepts remote only
- **THEN** the posting is filtered out with the reason "work mode" and a detail saying it does not state that it is remote, and its work mode stays not stated

#### Scenario: Remote concluded from the description
- **WHEN** a posting has no work-mode field but its description says the team works 100% from home, and the profile accepts remote only
- **THEN** the posting is read as remote and stays in the results

#### Scenario: Another city
- **WHEN** the profile accepts onsite and hybrid in "Lima" and a posting without a stated work mode is located in "Arequipa, Arequipa"
- **THEN** it is filtered out with the reason "location" and a detail naming Arequipa

#### Scenario: District of the saved city
- **WHEN** the profile accepts hybrid in "Lima" and a hybrid posting is located in "San Isidro, Lima"
- **THEN** it stays in the results without a location flag

#### Scenario: Region with the city's name
- **WHEN** the profile accepts onsite in "Lima" and an onsite posting is located in "Huaral, Lima"
- **THEN** it is filtered out with the reason "location"

#### Scenario: Place cannot be told
- **WHEN** the profile accepts hybrid in "Lima" and a hybrid posting shows only "Perú" and its description names no workplace
- **THEN** it stays in the results with a flag saying the city is not stated

#### Scenario: Another district of the saved city
- **WHEN** the profile accepts hybrid in "Miraflores" and "San Isidro" and a hybrid posting is located in "Surco, Lima"
- **THEN** it stays in the results with a flag saying the district is not among the user's

#### Scenario: Remote posting in another city
- **WHEN** the profile accepts remote and onsite in "Lima" and a posting that says it is fully remote is located in "Chiclayo"
- **THEN** it is not filtered out for its location

#### Scenario: Restored posting
- **WHEN** the user restored a posting that had been filtered out for its location, and it is then scored
- **THEN** it is not filtered out again, and an attempt to filter it is refused
