## 1. Database

- [x] 1.1 `0013_learn_from_results.sql`: offered salary columns, `applied` events from snapshots, drop `application_snapshots`; undo in `tests/migrations.py`
- [x] 1.2 Migration test: a v12 database with snapshots keeps each application's moment of applying and score at application time

## 2. Tracking

- [x] 2.1 `applied` event the first time an application gets an applied date (status or by hand); remove `_snapshot`, `_update_snapshot`, `snapshot` (D1)
- [x] 2.2 `applications.at_application` derived from history and current data (D2); `scoring.at_application` uses it; `tracking.untrack` without snapshots
- [x] 2.3 Offered salary detail field: validation, event, application object (D3)
- [x] 2.4 Tests: offered salary, score at application after a rescore, sent resume uploaded after applying, history shows the `applied` event

## 3. Learning

- [x] 3.1 `insights.outcomes` without the snapshot join (applied date), `at_application`, offered salary counts as offer, statuses and path by full name in a language (D4, D5)
- [x] 3.2 `insights.summary` offered-salary comparison (D4)
- [x] 3.3 `predict` and `refresh.write_history` read `at_application`; history records carry status names, ended, path, and offered salary (D5, D6)
- [x] 3.4 Demos: base demo sets the date of applying in its `applied` events (and records one offered salary); learning demo registers tailored resumes, backdates `applied` events, records some offered salaries (D6)
- [x] 3.5 Tests: learning tests pass; new tests for the status path by name (es), offer by offered salary with a custom status, median offered vs asked

## 4. Panel

- [x] 4.1 Applications board: offered salary in the details form and under asked/suggested in the table; suggested salary from `at_application`; history text for `applied`
- [x] 4.2 Learning board: offered-versus-asked line on the offers card
- [x] 4.3 Locales en/es; browser tests for the offered salary and the offers line

## 5. Skills and docs

- [x] 5.1 `analyze-results` skill and analysis guide: history fields (status names, path, offered salary, facts at application time)
- [x] 5.2 `docs/backlog.md`: remove the entry; `docs/workspace-layout.md` if it names snapshots

## 6. Wrap-up

- [x] 6.1 `ruff check .`, full `pytest` (browser included), privacy guard, `openspec validate learn-from-results --strict`
