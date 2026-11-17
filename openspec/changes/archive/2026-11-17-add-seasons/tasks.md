## 1. Seasons core

- [x] 1.1 Services: close season, create season, carry over selected applications
- [x] 1.2 Default season scoping for boards, pending work, and insights; earlier-season read mode with status updates
- [x] 1.3 Learning carry-over: mark kept lessons, retire lessons and withdraw the model on reset
- [x] 1.4 Full reset: confirmation token, move home to archive, initialize
- [x] 1.5 `jobtracker season show|new|list` and `jobtracker reset`
- [x] 1.6 `jobtracker export` (JSON and CSV into the exports folder)
- [x] 1.7 Tests for every `seasons` scenario

## 2. Skills

- [x] 2.1 Write `.claude/skills/new-season/SKILL.md`: explain the three restart levels, offer export, handle open applications, rerun profile steps with defaults
- [x] 2.2 Write `.claude/skills/panel/SKILL.md`: start, stop, port handling
- [x] 2.3 Spanish alias `nueva-temporada` (template exists in `i18n/skill-aliases/es/`; verify it installs once the skill is built)
- [x] 2.4 Dry-run each restart level with the fictional persona

## 3. Profile & agent board

- [x] 3.1 Season card with command and earlier-seasons access
- [x] 3.2 Profile card: resume, titles by state, job needs; include/exclude on suggested titles
- [x] 3.3 Pending-work card with the batch command
- [x] 3.4 Command reference from the installed command list
- [x] 3.5 Agent memory card with origins
- [x] 3.6 Providers card with status and switches
- [x] 3.7 Season indicator in the header and on boards when viewing an earlier season
- [x] 3.8 Browser tests for every `profile-agent-board` scenario

## 4. Verification

- [x] 4.1 Compare with board 4 of `design/panel-ux.html` in both languages
- [x] 4.2 Confirm a full reset leaves version control clean and the archive complete
