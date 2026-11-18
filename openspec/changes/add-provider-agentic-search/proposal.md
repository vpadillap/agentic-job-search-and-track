## Why

Job boards miss many openings: companies publish on their own careers pages
and applicant-tracking boards, and some reputable regional or niche sites have
no provider file. The owner wants a provider where the agent searches the web
on its own: it finds reputable job sources and the careers pages of companies
that the first results show are hiring for the user's titles, and reads the
openings those companies publish through their own channels. This provider is
mostly instructions (prompting), not code.

## What Changes

- New provider file `providers/agentic-search.md`: `regions: [global]`,
  `access: web-search`, no login, no reader, no dependencies. Its recipe tells
  the agent, for each included title and the profile's location and work
  mode:
  1. **Discover** with web search: postings for the title on sources that are
     not already enabled providers, and the companies hiring for it.
  2. **Judge sources** with explicit reputation rules: the company's own
     careers page or its applicant-tracking board (Greenhouse, Lever, Workday,
     Ashby, SmartRecruiters, …) are preferred; established job sites are
     allowed; aggregators that copy postings, sites asking for payment or
     personal data to see a posting, and pages without a company name or
     date are not used.
  3. **Expand**: for each company found, open its own careers page and look
     for other openings matching the user's titles.
  4. **Read** each posting from the most direct source (company page over
     copies), copy the description verbatim, record the publication date only
     when the page states it, and record the source URL.
  5. **Stop** at the file's limits (sources, companies, and postings per
     title; time between requests) and never sign in, apply, or fill forms.
- **Run budget.** The file states caps (for example at most 15 companies and
  40 postings per title) so a run stays predictable.
- **What the agent keeps between runs.** Companies found are not stored by
  this change (no new table); a later change may add that if it proves
  useful. Postings already stored are recognised by the existing import
  (seen, duplicates).
- `job-search` skill: one paragraph on providers with `access: web-search`
  (no reader; the agent builds the records itself; the posting's `provider`
  is `agentic-search` and `source_site` names the site it came from).
- Import accepts an optional `source_site` on a posting record so the panel
  can show where an agentic-search posting came from.

## Capabilities

### New Capabilities

- `provider-agentic-search`: how the agent searches the open web for
  postings, which sources it trusts, and its limits.

### Modified Capabilities

- None in requirements; `source_site` is an optional field (documented in the
  job-search skill and the import validation).

## Impact

- `providers/agentic-search.md` (new); `.claude/skills/job-search/SKILL.md`;
  `core/search.py` (optional `source_site`), the Search board shows it next to
  the provider name; locales en/es.
- Tests: the provider file is valid; a posting with `source_site` imports and
  shows it; a posting without a date keeps `posted_at` empty instead of
  guessing.
- A real check with one title, reported to the owner with the sources the
  agent chose and why.
