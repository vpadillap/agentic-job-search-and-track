## ADDED Requirements

### Requirement: Browsers live where every process can start them
On Windows, the system SHALL keep the browsers that providers need in a
fixed folder outside the user's local application data
(`%USERPROFILE%\.cache\ms-playwright`) for every command it runs and every
command those start, unless the user has already chosen a browser folder.
On other systems it SHALL keep the tools' default folder.

#### Scenario: Agent runs inside a packaged desktop app on Windows
- **WHEN** the agent installs Scrapling's browser from inside an app whose writes to local application data are redirected
- **THEN** the browser is installed in the fixed folder and a reader started later finds it and starts it

#### Scenario: User chose a browser folder
- **WHEN** the user has set `PLAYWRIGHT_BROWSERS_PATH`
- **THEN** the system keeps that folder

#### Scenario: Not Windows
- **WHEN** the system runs on Linux or macOS
- **THEN** the tools' default browser folder is used

### Requirement: A browser tool counts as installed only when it starts
`jt providers install` SHALL treat a browser tool (Scrapling, Playwright) as
installed only when its check starts the browser. When the package is
present but the check fails, it SHALL install the browser again, check
again, and report the tool as repaired; when that fails, it SHALL report
the failure with the check's output.

#### Scenario: Package present, browser does not start
- **WHEN** Scrapling imports but its browser fails to start
- **THEN** the install downloads the browser again without reinstalling the package, checks it, and reports Scrapling as repaired

#### Scenario: Everything works
- **WHEN** Scrapling imports and its browser starts
- **THEN** nothing is installed and Scrapling is reported as already installed

#### Scenario: Repair fails
- **WHEN** the browser still does not start after it is installed again
- **THEN** the provider is reported as failed with the check's output and other providers are searched
