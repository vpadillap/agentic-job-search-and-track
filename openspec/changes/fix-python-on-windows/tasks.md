## 1. Study (short; documented behavior and simulated cases, no reinstall here)

- [ ] 1.1 Documented behavior of the Store aliases, the Python install manager, winget, and the python.org installer (where Python lands, whether an open shell sees it), with sources and dates
- [ ] 1.2 Simulated cases for the hook: a failing `python` stub on the PATH, no Python, a project `.venv`
- [ ] 1.3 Results in the proposal and design (D2, D3 confirmed or revised); owner approves before section 2

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
