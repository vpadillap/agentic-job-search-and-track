## Context

`.githooks/pre-commit` is a POSIX shell script (git runs it with Git Bash on
Windows) that runs `python3` if it works, else `python`, on
`scripts/check_private.py` (standard library only). `scripts/jt.py` already
prefers the project's `.venv`. `/setup` step 1 tells the user to get Python
when the `python` check fails, but gives no Windows route.

## Goals / Non-Goals

**Goals:** the guard runs on every commit on Windows, macOS, and Linux; a
Windows user without Python ends setup with a working Python and `.venv` in
the same session.

**Non-Goals:** managing several Python versions; changing what the guard
checks.

## Decisions

### D1. Study first

The install route and the hook's fallbacks are decided from the study's table
(proposal). D2 and D3 are the expected shape.

### D2. Interpreter order in the hook (expected)

1. `$root/.venv/Scripts/python.exe`, then `$root/.venv/bin/python`;
2. `py -3` (the Windows launcher);
3. `python3`, then `python`, each only if `-c "import sys"` succeeds (the Store
   alias stub fails it or opens the Store; the check runs it with a short
   timeout and no window);
4. none: print "The privacy guard needs Python. Run /setup (it creates
   .venv), or install Python 3.11+." and exit 1 (the commit is blocked, as
   today, but with a clear reason).

### D3. Setup on Windows (expected)

`winget install --id Python.Python.3.13 --scope user --silent`, then find the
interpreter at its known path (`%LOCALAPPDATA%\Programs\Python\Python313\
python.exe`), use that path for `python -m venv .venv`, and from then on use
`.venv\Scripts\python.exe`. If winget is missing: the python.org installer
with "Add to PATH". Never the Store.

## Risks / Trade-offs

- [The study finds the Store route unavoidable on some machines] → The hook
  still works through `.venv` once setup created it.
