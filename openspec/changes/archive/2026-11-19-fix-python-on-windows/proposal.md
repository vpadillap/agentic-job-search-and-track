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

## Study (short; first section)

The owner's machine is a development machine with a working global Python, so
it cannot show what a fresh Windows user meets. The study is short and does
not reinstall anything here:

1. **Documented behavior** of each route, from the official sources (dates
   recorded): the Store's `python`/`python3` app-execution aliases (stubs in
   `%LOCALAPPDATA%\Microsoft\WindowsApps` that open the Store), the Python
   install manager (`py install`), `winget install Python.Python.3.13
   --scope user`, and the python.org installer; where each puts Python and
   whether an already-open shell sees it.
2. **Simulated cases** for the hook, in tests and in a scratch folder: a PATH
   whose `python` is a stub that fails, a PATH with no Python, and a project
   `.venv`; the hook must pick the right interpreter in each.
3. A real commit on this machine with `python` removed from the hook's PATH
   (the `.venv` interpreter must be used).

### Study results (2026-11-19)

| Finding | Source |
|---|---|
| Python's recommended Windows route is now the **Python install manager** (`py install`), per-user; adding `%LocalAppData%\Python\bin` to PATH is optional. The classic python.org installer "is deprecated since 3.14 and will not be produced for Python 3.16 or later" | docs.python.org/3/using/windows.html |
| The Store's `python.exe`/`python3.exe` app-execution aliases in `%LocalAppData%\Microsoft\WindowsApps` open the Store (no arguments) or print "Python was not found" and fail (exit 9009) when no Python is installed; they come first in PATH | bugs.python.org issue 41327; Microsoft Q&A |
| A PATH change made by an installer is seen only by **new** terminals | docs.python.org (same page); Windows behavior |
| `winget` offers `Python.Python.3.13` (3.13.17) and `Python.PythonInstallManager` | `winget search`, this machine |
| On this machine, `python`, `python3`, and `py` resolve first to the WindowsApps aliases (backed by the install manager, so they work); from Git Bash, the shell git hooks run in, each runs Python | `Get-Command`, Git Bash, this machine |
| Simulated: a `python3` that fails like the Store alias, then a real `python` → the old hook stopped at the alias's failure; the new hook skips it. No Python on PATH but a project `.venv` → the new hook runs the guard with `.venv` | tests in `tests/test_privacy_guard.py` |
| Real: the hook with no Python at all on PATH (only git and the shell), in this repository → ran the guard with `.venv`, exit 0 | this machine |

D2 is confirmed. D3 is confirmed with the route below; the install manager is
the long-term route, but the classic `Python.Python.3.13` package installs to a
fixed, known path, which is what lets the agent use it by full path in the same
session.

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
