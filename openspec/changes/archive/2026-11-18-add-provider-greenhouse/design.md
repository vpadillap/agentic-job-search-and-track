## Context

See the proposal's study log. Greenhouse has no public search across
companies, but every company board has a public, documented Job Board API
(`boards-api.greenhouse.io/v1/boards/<board>/jobs`), which gives each current
posting with its complete description and, per posting, the application-form
questions. What the API needs is the board name. The owner chose (2026-11-18)
to find board names in two ways, depending on whether the user is present:

- **Signed-in search**, when the user says they are present and signed in to
  MyGreenhouse in their own Chrome: the agent uses Claude in Chrome on
  `my.greenhouse.io/jobs/search` (every company, filtered by country).
- **Web discovery** otherwise: web search over Greenhouse's board addresses.

Either way, the reader reads postings only through the public API.

## Goals / Non-Goals

**Goals:** Greenhouse postings in the user's country with complete
descriptions and form questions; unattended runs keep working; companies
found once are rechecked in later runs.

**Non-Goals:** signing in for the user, or storing credentials or cookies;
applying, saving jobs, or setting alerts in MyGreenhouse; reading or storing
the signed-in user's account data shown by MyGreenhouse; companies' private
boards; the agentic-search provider's company memory (a separate change).

## Decisions

### D1. A plain-HTTP reader over the public API

`readers/greenhouse.py`, standard library only (`urllib`), with an injectable
`get(url) -> (status, body)`. `providers/greenhouse.md`: `access: http`,
`dependencies: []`, `requires_login: false`, `live_walk: false` (the
signed-in search is an optional step of the recipe, not a requirement).
At least 5 seconds between requests, one call at a time per run, a posting
stored by an earlier run is not read again (shared `readers/common.py`).

```
jt providers read greenhouse <run_id> --title "<title>" [--found <file>]
```

`--found` is a JSON list of links the agent found for this title: posting
links (`https://job-boards.greenhouse.io/<board>/jobs/<id>`, also the
`boards.greenhouse.io` and `job-boards.eu.greenhouse.io` forms) and board
links (`…greenhouse.io/<board>`). Anything else is ignored and listed in the
summary.

### D2. Which postings are read

1. **Postings found by the signed-in search** (links with a job id): read
   with `GET …/boards/<board>/jobs/<id>?questions=true`. They come from
   Greenhouse's own search for this title and country, so no title filter is
   applied; the location and window checks below still apply.
2. **Boards**: every board in `--found` plus every board remembered for this
   user (D4): `GET …/boards/<board>/jobs?content=true` once per board per
   run (a later title in the same run reuses the saved capture). A posting is kept when its title matches (D3), its location matches
   the user's country (D5), and its `first_published` is inside the run's
   window. Each kept posting's questions are read with
   `…/jobs/<id>?questions=true`.

At most `max_results_per_query` (100) postings per title; the summary says
when the cap was reached. A board that answers 404 is recorded as gone and
dropped from the remembered list.

### D3. Title match for board postings

Lowercase, accents removed, words split on non-letters. Seniority and grade
words are ignored (`senior, sr, junior, jr, semi, mid, lead, principal,
staff, i, ii, iii, iv`). A posting matches when it contains every remaining
word of the searched title: "Senior Data Engineer" matches "Data Engineer
II" and "Lead Data Engineer, AWS", not "Data Analyst". The agent's usual
filter step does the rest.

### D4. Remembered boards

`<home>/provider-settings/greenhouse.json`:
`{"boards": {"<board>": {"company": …, "titles": […], "found_via":
"signed-in search" | "web search" | "user", "first_seen": date,
"last_checked": date}}}`. The reader adds every board it reads with
postings in the user's country, updates `last_checked`, and drops boards
that answer 404. The user can ask the agent to add a company they care about
(a board name or any Greenhouse link): the agent passes it in `--found`.

### D5. Country match

The provider file's `## Countries` table (a lookup for this global
provider, as for Glassdoor): country code, the place words that mark a
posting as in that country (`Peru; Perú; Lima; Arequipa; Trujillo`), and the
regional words that mark a remote posting open to it (`LATAM; Latin America;
South America; Americas`). A posting matches when its `location.name` or an
office name contains a place word, or contains "remote"/"anywhere" together
with a regional word. A country not in the table: the reader answers
`missing_country`, and the agent asks the user for the place words once and
passes them with `--place-words "Chile; Santiago; Valparaíso"`, which are saved
in the same settings file.

### D6. Drafts

`external_id` = the posting id; `url` = `absolute_url` (the company's own
careers page when it has one); `title`; `company` = `company_name`;
`location` = `location.name`; `country` = the profile's country;
`posted_at` = `first_published`'s date (`updated_at` when missing);
`description` = `content` (HTML entities decoded) as plain text, as in the
Glassdoor reader; `form_questions` = each question's `label` as `text`,
`required`, and its kind from the first field's type (`input_text` → text,
`textarea` → long_text, `input_file` → file, `multi_value_single_select` →
choice, `multi_value_multi_select` → multi_choice, with the values' labels as
`options`); hints `site_language` (`language`), `site_departments`,
`site_offices`. Work mode, contract type, and salary are the agent's reading.

### D7. The signed-in search (recipe, agent with Claude in Chrome)

Only when the user said in this conversation that they are present and signed
in to MyGreenhouse in their own Chrome. The agent never types credentials;
if the page asks to sign in, it skips this step and uses web discovery.

1. A new tab: `https://my.greenhouse.io/jobs/search?query=<title>&location=<Country>&location_type=country&country_short_name=<CC>`.
2. Scroll the list to its end, at a person's pace (a few seconds per scroll).
3. Open each card, copy the link under the posting's title
   (`job-boards.greenhouse.io/<board>/jobs/<id>`), close it with Escape, a
   few seconds apart. Never press Apply, the bell (alerts), or save.
4. Close the tab; write the links to a file in the capture folder; run the
   reader with `--found`.

The page's data includes the user's name and email: never read, copy, or
store it.

### D8. Web discovery (recipe, agent with its web search tool)

For each title: `site:job-boards.greenhouse.io "<title>" <country or main
city>` and the same for `boards.greenhouse.io` and
`job-boards.eu.greenhouse.io`; collect the result links that match D1's
forms; run the reader with `--found`. Old results are harmless: the API
returns only current postings.

### D9. Stop rules

Blocked: 403 or 429 from the API. Error: a response that is not the expected
JSON, or three board failures in a row (other than 404). A board that
answers 404 is not an error.

## Risks / Trade-offs

- [Web discovery misses companies search engines have not indexed] → The
  signed-in search when the user is present; remembered boards.
- [The signed-in search uses the user's MyGreenhouse account] → Read-only, at
  a person's pace, only with the user present; never apply, save, or set
  alerts; the account's data is never read.
- [Many remembered boards make calls slower] → One request per board per
  title; boards that disappear are dropped.
- [Country words are approximate] → The agent's filter step still checks the
  location; the words are a table the user can extend.

## Migration Plan

None: no schema change; Greenhouse starts switched off.
