## Why

On Windows, when Python is missing and the agent installs it, there is no
fixed method, so it ends up installing it from PowerShell through the
Microsoft Store (or its "python" app alias). Afterwards `python`/`python3` is
often not on the shell's PATH (the Store alias opens the Store instead of
running Python, or the PATH change needs a new shell or a restart). The
pre-commit privacy guard runs `python3` or `python` from the PATH, so it fails
and commits are blocked (or the guard cannot run at all). The owner wants the
guard to work regardless, for example by using the Python inside the
project's `.venv`, and setup to install Python on Windows in a fixed,
reliable way.

## Study (first section; nothing is built before it)

On this Windows machine and a clean user profile where possible, recorded as a
table:

1. What `python`, `python3`, and `py` resolve to in Git Bash (the shell git
   hooks run in), PowerShell, and cmd: real interpreters, the Store app-alias
   stubs (`%LOCALAPPDATA%\Microsoft\WindowsApps\python*.exe`), or nothing; what
   each does when run (exit code, opens the Store).
2. The install routes and where each puts Python and whether the current
   shell sees it without a restart: `winget install Python.Python.3.13`,
   the Python install manager (`py install`), the Store package, the
   python.org installer with "Add to PATH".
3. Whether the hook can always use the project's `.venv` interpreter
   (`.venv/Scripts/python.exe`), and what to do before the `.venv` exists.

## What Changes (expected; revised after the study)

- **The privacy guard runs with the project's own Python first**:
  `.githooks/pre-commit` tries `.venv/Scripts/python.exe` (Windows) or
  `.venv/bin/python`, then the `py` launcher, then a `python3`/`python` that
  really runs (a Store alias stub does not count), and if none works it fails
  with a message that says how to fix it instead of an obscure shell error.
- `jt doctor` checks that the guard can find a working Python and names the
  fix.
- `/setup` step 1 on Windows: a fixed install route chosen from the study
  (expected: `winget install --id Python.Python.3.13 --scope user`, never the
  Store), then using the installed interpreter by its full path for the rest of
  the session (no restart needed), creating `.venv` with it.
- README troubleshooting row for "the privacy guard cannot find Python".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `user-workspace`: the privacy guard runs whenever a commit is made,
  including on Windows without Python on the PATH.
- `setup-onboarding`: Python is installed on Windows by a fixed route.

## Impact

- `.githooks/pre-commit`, `core/doctor.py` (guard check), `.claude/skills/
  setup/SKILL.md`, README; tests for the hook's interpreter choice (a fake
  `.venv` and PATH) and the doctor check.
