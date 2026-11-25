## MODIFIED Requirements

### Requirement: Privacy registration
The setup flow SHALL register the user's identifying terms for the privacy
guard and SHALL create all personal files only inside the private home.

The setup flow SHALL also record the user's full name, as it appears on the
resume and confirmed by the user, inside the private home. Recording the name
SHALL register it as a private term in the same step. The user may skip it,
and may change it later with the same command; the new name replaces the
recorded one for later downloads.

#### Scenario: After setup
- **WHEN** setup completes
- **THEN** version control reports no new or modified tracked files and the private terms file exists in the private home

#### Scenario: Recording the full name
- **WHEN** the user confirms "Marisol Quispe Tanaka" as their full name in the privacy step
- **THEN** the name is stored in the private home, it is a registered private term, and a commit containing it is refused by the privacy guard

#### Scenario: Changing the full name
- **WHEN** the user records "Marisol Quispe" after "Marisol Quispe Tanaka" was recorded
- **THEN** later downloads use "Marisol Quispe" and both names stay registered private terms
