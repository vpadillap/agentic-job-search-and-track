## Why

<One paragraph: which job site this adds, for whom (global, or which
countries), and why it matters for job seekers there.>

The study (<date>), with real requests, logged out unless stated:

| Route | Result |
|---|---|
| Plain HTTP | <status and what came back> |
| Headless browser | <…> |
| Visible browser, fresh profile | <…> |
| <Chosen route> | <what it returns: postings per page, description, dates, form questions> |

Proving runs (no personal data: generic titles and counts only):

| Country | Date | Title searched | Postings read | Complete descriptions |
|---|---|---|---|---|
| <CC> | <date> | <generic title> | <n> | <n> |

Terms of use: <what the site's terms say about automated access, with the
date they were read>.

## What Changes

- `providers/<id>.md`: <coverage>, access `<access>`, <login/presence>,
  <dependencies>, recipe, fields, terms, stop conditions, pitfalls.
- <If any: `src/jobtracker/core/readers/<id>.py` and its registry entry; tests
  with fictional pages in `tests/test_<id>_reader.py`; the optional
  dependency extra in `pyproject.toml`.>

## Capabilities

### New Capabilities

- `provider-<id>`: how <site> is searched and read, and what is never done
  there.

### Modified Capabilities

None.

## Impact

- <Files added or changed.>
- The provider starts switched off for every user.
