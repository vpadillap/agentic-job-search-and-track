## ADDED Requirements

### Requirement: Python installed by a fixed route on Windows
When Python is missing on Windows, setup SHALL install it by the route stated
in the setup skill (not the Microsoft Store), SHALL use the installed
interpreter by its full path for the rest of the session so no restart is
needed, and SHALL create the project's environment with it.

#### Scenario: Windows without Python
- **WHEN** setup runs on Windows and no working Python is found
- **THEN** the agent installs Python by the stated route, creates the project's environment with it in the same session, and the environment check passes
