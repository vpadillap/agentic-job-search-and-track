## 1. Database

- [x] 1.1 Add `0012_status_ends.sql`: `statuses.ends`, filled for built-in ending keys and for custom statuses in closed stages, then remove `statuses.stage` (D1)
- [x] 1.2 Migration test: a v11 database with custom statuses in every stage migrates with the right `ends` and no `stage` column; old `status_changed` events still read

## 2. Tracking core

- [x] 2.1 `core/applications.py`: drop `STAGES`, `APPLIED_STAGES`, `OPEN_STAGES`; status objects carry `name_en`, `name_es`, `ends`; `list_statuses` orders by position, id; `create_status(name, ends)`; `set_status(..., ends=None)` for inline creation
- [x] 2.2 Applied date and snapshot: fill `applied_on` for the built-in keys of D2 only; take the snapshot the first time `applied_on` is set, from `set_status` or `update_details` (D3)
- [x] 2.3 Next step, attention, funnel (list per status), `list_applications(status=…, hide_ended=…)`, and the application object (`ended`, no `stage`) per D4–D6
- [x] 2.4 History: new `status_changed` events store ids and names; `history()` returns `from_name`/`to_name` in the requested language, resolving old events by key or stored name (D6)
- [x] 2.5 `core/tracking.py` (`application()` without stage, `--applied` when there is no applied date), `core/board.py` (open counter, rescore, pending documents), `core/demo.py` (the custom "Position frozen" status ends)

## 3. CLI and API

- [x] 3.1 CLI: `applications list --status/--hide-ended`, `applications set-status --ends`, `applications statuses create --ends yes|no` (required); no `--stage` anywhere
- [x] 3.2 API: `ends` replaces `stage` in the status and create-status requests; responses carry the new funnel and status objects
- [x] 3.3 Tests for tracking, board, CLI, and API rewritten to statuses and `ends`; scenarios of the delta specs covered

## 4. Panel

- [x] 4.1 Applications board: one count card per status in use (full name, count, filter by status); ended applications hidden by default with the count and status names; show-ended toggle; a selected ending card lists its applications; sort by status list order (D5)
- [x] 4.2 Status chip and list without stage colors (`ended` muted); new-status form with name and "The application ended with this status"; missing-resume and documents hints use "no applied date and not ended"
- [x] 4.3 Search board: the "tracked, applied" label uses the applied date
- [x] 4.4 Locales en/es: remove `stage.*` and `status.stage`; add the ended texts (hidden note, toggle, checkbox)
- [x] 4.5 Browser tests: cards per status, card filter, ended hidden and shown, custom status created as ending, sort by status

## 5. Learning (minimal, last)

- [x] 5.1 `core/insights.py`: `_progress(key, ends)` per D2; `outcomes()` reads `ends` and resolves each event's status; the outcome record has `ended` instead of `stage`
- [x] 5.2 `core/recommend.py`: "apply next" uses no applied date and not ended
- [x] 5.3 Learning tests pass unchanged in meaning; adjust only those that set stages, and the collecting-level demo size (D7)

## 6. Docs and wrap-up

- [x] 6.1 `.claude/skills/prepare-documents/SKILL.md` (`all` lists applications without an applied date that have not ended), README, and `docs/backlog.md` (remove the statuses entry)
- [x] 6.2 `ruff check .`, full `pytest` (browser tests included), privacy guard, `openspec validate remove-status-stages --strict`
