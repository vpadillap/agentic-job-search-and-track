# Adding a job site

Anyone who clones this project can add a job site (a *provider*) for their own
search and, once it is proved, offer it to everyone as a pull request. In
Claude Code, run **`/add-provider`** (Spanish: `/agregar-proveedor`): the
agent guides every step below. This page is the rulebook it follows.

## 1. Private first

A new provider lives in your private home, never in the repository, until you
decide to contribute it:

```
user-data/providers/<id>.md         the provider file (same format as providers/_template.md)
user-data/providers/<id>.py         its reader, if it needs one
user-data/providers/<id>.study.md   your study and proving runs (private)
user-data/providers/tests/          tests of your reader (fictional pages only)
```

A private provider is listed, validated, switched on and off, and searched
exactly like the ones in `providers/`, and the panel marks it "Private". It
can use any access method, any dependency, and its own reader with the same
interface as `src/jobtracker/core/readers/` (it may import
`jobtracker.core.readers.common` for pacing, run state, seen postings, and
stops). Its id must not be one that `providers/` already uses.

## 2. Study before choosing how to read the site

Try the routes with real requests and write down what each one returns, in a
table (route → result), before deciding:

1. plain HTTP;
2. a headless browser;
3. a visible browser with a fresh profile;
4. only if a sign-in is unavoidable: your own browser through the Claude in
   Chrome extension, where you sign in yourself.

Also record: the search address and its filters (title, location, date),
where each posting's fields come from, how pages continue (paging, "show
more"), whether application questions are visible without applying, and the
site's terms of use.

## 3. Rules every provider follows

- **Accounts are never put at risk.** Never type or pass credentials through
  automation, and never automate a signed-in account in a way that could get
  it banned: when a sign-in is needed, you sign in yourself, in your own
  browser, and you are present (`requires_login: true`, `live_walk: true`).
  Reading logged out, where no account is involved, getting past a site's
  automated checks is allowed.
- **Read-only.** Never apply, submit or save a form, send a message, follow,
  save jobs, or set alerts.
- **Verbatim.** Descriptions and form questions are copied, never retyped,
  summarized, or translated. Dates are what the site states; never guessed.
- **Coverage.** `regions: [global]` for a site that serves many countries, or
  the two-letter codes of a local site (`[PE]`, `[PE, CL]`). A local site
  with several countries has a `## Countries` table with a row per country
  and the date it was verified **in that country**.
- **Terms.** The file states the site's terms-of-use risk before the user
  turns it on.
- **Pacing.** At least 5 seconds between requests for a reader (the shared
  `common` module enforces it); one call at a time per run.
- **Domains.** The front matter lists the site's hosts in `domains` (for
  example `[computrabajo.com]`, or `[example.*]` for every country domain of
  the site). The agentic web search then never reads that site; without it,
  `jt providers validate` warns.

## 4. Proved means

- `jt providers validate <file>` reports it valid;
- a real search with at least one of your titles returns postings with
  complete descriptions and imports them without errors, **for each country
  the file claims**;
- a reader, if any, has tests with fictional pages (never real people,
  companies' real postings, or your own data) that pass.

The study file records each proving run (date, country, how many postings).

## 5. Contributing it

When the provider is proved, `/add-provider` offers a pull request. Only with
your yes, it:

1. checks that `gh` is signed in and forks the repository if needed;
2. creates a branch `add-provider-<id>` from the latest `main`;
3. copies the file to `providers/<id>.md`; moves a reader to
   `src/jobtracker/core/readers/<id>.py` with its registry entry, its tests to
   `tests/test_<id>_reader.py`, and new dependencies to an optional extra in
   `pyproject.toml`;
4. writes `openspec/changes/add-provider-<id>/` from `providers/change-template/`,
   with the study table **rewritten without personal data** (generic titles,
   counts, no names, no search results);
5. runs `ruff check .`, `pytest`, the privacy guard, and
   `openspec validate add-provider-<id> --strict` when OpenSpec is installed;
6. commits, pushes to your fork, and opens the pull request with the
   repository's template.

If you say no, nothing leaves your machine and the provider stays private. A
failing step stops the flow and is reported; nothing is forced.
