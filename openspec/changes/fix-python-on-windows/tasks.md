## 1. Study (scratch only)

- [ ] 1.1 What `python`, `python3`, `py` resolve to and do in Git Bash, PowerShell, and cmd on this machine (real interpreter, Store alias stub, nothing)
- [ ] 1.2 Install routes on Windows (winget, Python install manager, Store, python.org installer): where Python lands and whether the current shell sees it without a restart
- [ ] 1.3 The hook with the project's `.venv` interpreter, and before `.venv` exists
- [ ] 1.4 Results table in the proposal and design (D2, D3 confirmed or revised); owner approves before section 2

## 2. Privacy guard

- [ ] 2.1 `.githooks/pre-commit`: interpreter order (D2), a working-Python check for each candidate, clear failure message
- [ ] 2.2 `jt doctor`: the guard can find a working Python, with the fix
- [ ] 2.3 Tests: the hook's choice with a fake `.venv`, a fake stub on the PATH, and none

## 3. Setup and docs

- [ ] 3.1 `/setup` step 1 on Windows: the fixed install route (D3), full path, `.venv` in the same session
- [ ] 3.2 README (en/es) troubleshooting row

## 4. Wrap-up

- [ ] 4.1 Real check on this machine: a commit through the hook with `python` not on the PATH
- [ ] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate fix-python-on-windows --strict`
