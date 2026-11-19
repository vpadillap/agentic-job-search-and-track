## 1. Groups

- [x] 1.1 Migration: `search_groups`, `search_runs.group_id` (one group per existing run) (D1)
- [x] 1.2 `jt run start`: join today's group, `--group`, `--new-group`; `group` in the answer (D2)
- [x] 1.3 Group summary and postings (D4); tests: same day, next day, `--group`, `--new-group`, demo apart, summary sums

## 2. Panel and skill

- [x] 2.1 API `group` parameter; Search tab: group selector, merged summary with its runs, postings once; en/es (D4)
- [x] 2.2 Browser test: two runs of one day on one page
- [x] 2.3 `job-search` skill: the once-per-conversation question for later days (D3); eval request

## 3. Retroactive offer

- [x] 3.1 Offer `group-searches-by-day` in `core/offers.py` (D5); tests: applies, groups by day per season, demo apart, empty groups removed

## 4. Wrap-up

- [x] 4.1 Real check in a temporary home: two runs today, one yesterday, the offer (done 2026-11-19 through the real CLI: three runs on separate pages, a fourth today joined today's page, the offer applied, grouped today's runs on one page, kept yesterday apart, removed the empty page, and was not listed again)
- [x] 4.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate group-searches-by-day --strict`
