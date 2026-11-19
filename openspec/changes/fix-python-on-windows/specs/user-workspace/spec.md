## ADDED Requirements

### Requirement: The privacy guard finds a working Python
The privacy guard SHALL run with the project's own Python when the project's
environment exists, and otherwise with any Python that really runs; a stub
that does not run Python SHALL NOT be used. When no working Python is found,
the guard SHALL block the commit with a message that says how to fix it.

#### Scenario: Windows without Python on the PATH
- **WHEN** a commit is made on Windows, the project's environment exists, and `python` on the PATH is the Store alias
- **THEN** the guard runs with the project's environment and checks the commit

#### Scenario: No Python at all
- **WHEN** a commit is made and no working Python is found
- **THEN** the commit is blocked with a message saying how to get Python or run setup
