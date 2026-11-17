---
name: panel
description: Starts the local Job Tracker panel in the background (if it is not already running) and gives its address, or stops it. Checks whether the port is free and proposes another one when it is busy.
---

# Panel

The panel is a local web page (only this computer can open it) that shows and
edits the job-search data. It never runs the agent.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(use `python3` if `python` is not available). Below, `jt` means
`python scripts/jt.py`. In the checks below, `python` means the same
interpreter.

Talk to the user in the panel language (`jt context` → `language`). The user
may ask to start (the default when no argument is given) or to stop.

## Start

1. `jt context`. If `initialized` is false, say setup is needed first (`/setup`)
   and stop. If `panel.interface_ready` is false, say the panel interface is
   not included in this version and stop.
2. Take the address from `panel.url` (host and port).
3. **Already running?** Ask the panel itself:

   `python -c "import urllib.request; print(urllib.request.urlopen('<url>/api/health', timeout=2).read().decode())"`

   If it answers with `"ok": true`, the panel is already running: give the
   user the address and stop.
4. **Port busy?** If the health check failed, check whether something else
   holds the port:

   `python -c "import socket; s = socket.socket(); print(s.connect_ex(('<host>', <port>)))"`

   `0` means the port is taken by another program. Find a free one by trying
   the next ports (port + 1, + 2, …) with the same check until it prints a
   non-zero number. Propose it to the user ("Port 8000 is used by another
   program; shall I use 8001?"). If they accept, ask whether to keep it for
   next time; if yes, `jt config set port <new>`.
5. Start the panel **in the background** (it keeps running while you go on):
   `jt panel` (or `jt panel --port <new>` when using another port only this
   time). Wait a moment and repeat the health check of step 3 on the address
   actually used.
6. Give the user the address to open in the browser, and say: "It keeps
   running in the background. Ask me to stop the panel when you are done."
   If the health check still fails, show the panel's error output and stop.

## Stop

1. If you started the panel in this conversation as a background task, stop
   that task.
2. Otherwise find the process that listens on the panel's port and, after the
   user confirms, end it:
   - Windows (PowerShell):
     `Get-NetTCPConnection -LocalPort <port> -State Listen | Select-Object -ExpandProperty OwningProcess`
     then `Stop-Process -Id <pid>`.
   - macOS/Linux: `lsof -ti tcp:<port> -sTCP:LISTEN` then `kill <pid>`.
   Only end a process whose command line is the Job Tracker panel
   (`jt.py panel` or `jobtracker panel`); if it is something else, tell the
   user and do not touch it.
3. Confirm with the health check of step 3 above that it no longer answers.
