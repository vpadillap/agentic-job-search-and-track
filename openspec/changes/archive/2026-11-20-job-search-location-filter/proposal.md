## Why

A user who chose Lima got postings in Arequipa and Chiclayo. The postings
carry their city (Bumeran, LinkedIn, Computrabajo, and the others show it),
and the profile has the user's cities, but the first-pass filter lets them
through: a posting whose work mode is not stated is never excluded, and the
location check only applies to postings that say onsite or hybrid. In Peru
many postings never state the work mode, so most of them escape the check.

Making the filter stricter means it will sometimes be wrong, and today a
filtered-out posting cannot be brought back: the panel only lists it with
its reason. And on a page with several searches of the same day, a site's
chip keeps showing an earlier failure ("Bumeran failed: missing tool") even
after a later search read it fine, because the page shows each site's worst
result instead of its latest one, and never says when the site last worked.

## What Changes

**Location and work mode in the first-pass filter**

- A posting that never says it is remote, and whose title and description do
  not let the agent conclude it is fully remote, is treated as having some
  on-site presence for filtering. Its captured `work_mode` stays `null` with
  the "work mode not stated" flag (capture never invents).
- **BREAKING** (behavior): when the profile accepts remote only, such a
  posting is now filtered out with reason `work_mode` and a detail saying
  it does not state that it is remote. Before, it was always kept.
- The location check applies to onsite, hybrid, and not-stated postings: the
  agent reads where the work is done (the posting's location field, and the
  description when it names the workplace) and filters it out with reason
  `location` when that place is clearly outside every place the user saved.
- Places are compared by meaning, not by text: a district belongs to its
  city (saved "Lima", posting "San Isidro" → inside); a region sharing a
  city's name is not the city ("Huaral, Lima" is not Lima).
- When it cannot tell (only the country, no place, or another district of a
  saved city), the posting is kept with a flag. A remote posting is never
  filtered for location.

**Restoring a filtered-out posting**

- In the filtered-out list each posting gets a "Restore" action (also
  `jt postings restore`). It returns to the results as a new posting, with
  no score yet, and the filter never excludes it again.
- Filtered-out postings cost nothing: they are not scored, priced, or
  prepared. A restored posting waits for its score as a pending item
  ("Score to calculate"), done by the same one command that completes
  everything pending; during a running search the search scores it.
- A restore is a correction of the agent's filter: the history given to the
  agent lists it with the reason it had, so later searches can learn from it.

**Site chips on a page with several searches**

- Each site's chip shows its latest result on the page, not the worst one,
  and the time it was last searched ("Bumeran · 12 · 15:40"). A failure is
  shown only if it is the site's latest result on that page. Found postings
  are still added up across the page's searches.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `job-search`: the first-pass filter's location and work-mode rules, and
  that a restored posting is never filtered again.
- `search-results-board`: restoring from the filtered-out list; site chips
  show each site's latest result and when it was last searched.
- `pending-work`: restored postings without a score are pending items.
- `outcome-insights`: the history given to the agent includes restored
  postings as corrections of the filter.

## Non-goals

- A stored list of districts per city, a geocoding service, or any new
  dependency: the agent resolves places.
- Changing the setup questionnaire (which places are asked and when) or the
  captured `work_mode` values.
- Remote-scope checks (company country or region).
- Restoring postings the user dismissed (that already exists as undo).
- The provider list in the Profile & agent tab (its last-status column is
  out of scope).

## Impact

- Skills: `.claude/skills/job-search/batch-worker.md` (filter rules; a
  restored posting is never filtered), `scoring-guide.md` (`conditions` with
  a place doubt), `.claude/skills/prepare-documents/SKILL.md` (pending
  `score` item).
- `src/jobtracker/core/search.py` (restore; filter refuses restored
  postings; `postings list` marks restored ones; group summary takes each
  site's latest result with `last_searched_at`), `core/board.py` (pending
  `score` items), `core/insights.py` (filter corrections in the history),
  `cli/main.py` (`postings restore`), `web/app.py` (restore endpoint).
- Panel: `boards/search.js` (Restore action, chips), `api.js`, locales
  en/es, pending-item label.
- Tests: search, board/API, CLI, insights, pending, skill, browser.
- `CHANGELOG.md`.
