## Why

Each `/job-search` is one run, and the panel's Search tab shows one run at a
time. A user who searches twice on the same day (for example one title more,
or a site that was blocked and retried) sees two separate pages and has to
switch between them. The owner wants searches of the same day on the same
page, and, when the user keeps searching on later days in the same chat, the
agent to offer adding the new search to the earlier one. Existing users should
be offered to group their past searches the same way when they update.

## What Changes

- **Search groups.** Every run belongs to a group. A run started on the same
  local day as the latest group's runs joins that group automatically; a run
  on a later day starts a new group, unless the agent passes `--group <id>` to
  add it to an earlier one. `jt run start` reports the group it joined.
- **Later days in the same chat.** When the agent already ran a search in this
  conversation on an earlier day, it asks the user once: add today's search to
  that one, or keep it separate. The answer decides `--group`.
- **Panel.** The Search tab shows a group: the summary adds up its runs (found,
  new, filtered, per site), the table shows every posting of its runs once,
  and the selector lists groups by date (or date range) with how many searches
  they contain. Each run stays visible inside the group's summary.
- **Retroactive.** A one-time offer (from `add-self-update`): "Group your past
  searches by day?" Accepting puts runs of the same local day into one group;
  nothing else changes. Until then each past run is its own group, so the
  panel looks as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `search-results-board`: the board shows a group of runs, and earlier groups.
- `job-search`: runs are grouped by day, and the agent offers to group later
  days of the same chat.

## Impact

- Migration: `search_groups` table and `search_runs.group_id` (every existing
  run gets its own group); `core/search.py` (start, summary by group); panel
  API and `boards/search.js`; `job-search` skill; the offer registered in
  `core/offers.py`.
- Depends on `add-self-update` for the offer mechanism (implemented after it).
- Tests: same-day join, next-day new group, `--group`, summary of a group,
  board with a group, the offer grouping past runs.
