## ADDED Requirements

### Requirement: One editable mark for a missing work mode
A posting without a work mode SHALL show a single mark for it: the work-mode
chip, styled as a warning, which opens the work-mode editor. A flag whose
whole text only says the work mode is not stated (in English or Spanish)
SHALL NOT be shown, and later imports SHALL NOT store it; flags that say more
SHALL stay. Once a work mode is set, the chip SHALL look like the other
conditions.

#### Scenario: Missing work mode shown once
- **WHEN** a posting has no work mode and its flags include "Modalidad de trabajo no indicada"
- **THEN** the row shows only the warning-styled work-mode chip for it, and activating the chip opens the work-mode editor

#### Scenario: Warning goes away once set
- **WHEN** the user sets that posting's work mode to hybrid
- **THEN** the chip shows hybrid in the normal style and no "not stated" mark remains

#### Scenario: Flags that say more stay
- **WHEN** a posting's flags include "La modalidad solo la indica Bumeran; la descripción no la menciona"
- **THEN** that flag is still shown
