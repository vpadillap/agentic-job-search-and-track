## Context

`search_runs` holds one row per run (started_at, providers, capture folder);
`run_results` links postings to runs. The board shows `latest_run_id` by
default and lists runs for the selector; demo runs exist (`is_demo`).

## Goals / Non-Goals

**Goals:** one page per day of searching; the user decides whether later days
join; past runs regrouped only with the user's yes.

**Non-Goals:** merging capture folders; changing what a run imports or how
duplicates are decided.

## Decisions

### D1. Groups

Table `search_groups (id, season_id, started_at, is_demo)` (the page title is derived from its runs' days, so no label is stored); `search_runs.group_id`
(not null after the migration: each existing run gets its own group, so the
panel is unchanged until the user accepts the offer). The "day" is the local
date of `started_at`.

### D2. Joining

`jt run start` without options: if the season's latest group has a run on
today's local date, join it; otherwise create a group. `--group <id>` joins
that group (same season, not demo); `--new-group` always creates one. The
answer includes `group` (id, runs, first and last day).

### D3. The agent's question

The `job-search` skill: the agent keeps the run ids it started in this
conversation; when the latest one is on an earlier day than today, it asks
once per conversation ("Add today's search to the one from <day>, or keep it
separate?") and passes `--group` or `--new-group`.

### D4. Board

`/api/search?group=<id>` (default: latest group). Summary: counts summed
across runs, providers merged (a provider's status is the worst of its runs;
found and new summed), the list of runs with their time and titles. Table:
postings of the group's runs, each once, with the newest run's outcome.
Selector: groups by date or date range, with the number of searches.

### D5. Retroactive offer

Offer id `group-searches-by-day`: applies when two or more runs share a local
day in different groups. Accepting regroups runs by local day within each
season (demo runs kept apart) and deletes groups left empty. It only joins pages, never splits one the user joined across days.

## Risks / Trade-offs

- [A group with many runs is long] → Same table with filters; the summary
  lists each run.
