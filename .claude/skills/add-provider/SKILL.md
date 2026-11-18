---
name: add-provider
description: Adds a job site the project does not cover yet, for this user first. Studies the site with the user (which way of reading it works), writes a private provider file (and a reader when the site needs one) in the user's private folder, validates it, proves it with a real search in each country it claims, and turns it on. Once proved, offers to contribute it to the project as a pull request, only with the user's yes and without any personal data. Never signs in for the user or applies to anything.
---

# Add a job site

The rules are in `providers/CONTRIBUTING.md`: read it completely first and
follow it. This skill is the guided path through it.

**The CLI.** From the repository root run `python scripts/jt.py <command>`
(`python3` if `python` is missing). Below, `jt` means `python scripts/jt.py`.
Talk to the user in the panel language (`jt context` → `language`).

**Hard rules for this whole skill**

- Everything is written in the user's private folder (`jt paths` →
  `private_providers`), never in `providers/` or `src/`, until the user
  accepts a pull request in step 7.
- Never type, ask for, or pass the user's credentials. If a site can only be
  read signed in, the user signs in themselves, in their own browser, and the
  provider is marked `requires_login: true` and `live_walk: true`.
- Read-only on every site: never apply, submit or save a form, send a
  message, follow, save jobs, or set alerts.
- Never put personal data in anything that could leave the machine (step 7).

## 1. The site

1. `jt context`. If `setup_required` is true, suggest `/setup` first and stop.
2. Ask which site and why (a local board, a niche site…). `jt providers list`:
   if the site already has a provider (repository or private), say so and
   offer to turn it on instead.
3. Agree on the provider id with the user: lowercase letters, digits, and
   hyphens, from the site's name (`computrabajo`, `getonbrd`). It must not be
   an id that `jt providers list` already shows.
4. Coverage: does the site serve many countries (`regions: [global]`) or only
   some (`[PE]`, `[PE, CL]`)? Each country claimed must be proved (step 5).

## 2. Study

With the user watching, try the routes in the order of
`providers/CONTRIBUTING.md` (§2), with real requests and the user's included
titles, and write each route and its result in
`<private_providers>/<id>.study.md` as a table. Save what you fetch for the
study in the scratchpad, not in the repository.

Stop and ask the user when:

- a route would need their sign-in (they decide whether to sign in themselves
  in their own Chrome and be present on every run);
- the site's terms forbid automated access (say what they say; the user
  decides whether to go on).

Agree with the user on the route. Prefer, in order: a public structured
source (an API or embedded data), plain HTTP, a browser.

## 3. The provider file

1. Copy `providers/_template.md` to `<private_providers>/<id>.md` and fill
   every field and section from the study: access method and what does not
   work, search recipe, fields, application form questions, limits and terms,
   stop conditions, pitfalls. Write it in English, like the repository's
   files. Look at a similar repository provider for the level of detail
   (`providers/indeed.md` for a browser reader, `providers/greenhouse.md` for
   an API, `providers/agentic-search.md` for a recipe without reader).
2. A local site with two or more countries gets the `## Countries` table
   (`providers/README.md`).
3. `jt providers validate <private_providers>/<id>.md` until it is valid.

## 4. A reader, when the site needs one

When the recipe is fixed and mechanical (requests, parsing), write a reader so
runs are consistent; when it needs judgment page by page, the recipe alone is
enough.

- `<private_providers>/<id>.py` with `read(paths, run_id, title,
  location=None)`, written like `src/jobtracker/core/readers/indeed.py` (or
  `greenhouse.py` for plain HTTP): use `jobtracker.core.readers.common`
  (`context`, `lock`, `load_state`, pacing of at least 5 seconds,
  `finish`), write drafts, never import anything.
- Tests in `<private_providers>/tests/test_<id>_reader.py` with a fake
  browser or getter and **fictional** pages only; run them with
  `python -m pytest <private_providers>/tests`.
- A dependency the reader needs (for example `scrapling`, `playwright`): tell
  the user what will be installed and its size, ask, install it into the
  project's `.venv`, and list it in `dependencies`.
- `jt providers read <id> <run_id> --title "<title>"` runs it like a built-in
  reader.

## 5. Prove it

For each country in the file's coverage (for a global site: the user's
country, plus any other the user wants to claim):

1. `jt providers enable <id>`, then a real search with one of the user's
   titles, following `/job-search` for this provider only (`jt run start
   --days 7`, the provider's recipe or reader, readings, `jt postings
   import`, `jt run finish`).
2. Proved when postings with complete descriptions import without errors.
   Record in the study file: date, country, title, postings read, complete
   descriptions, run id.
3. If it fails, fix the file or the reader and try again; tell the user what
   happened.

A local site with several countries: update its `## Countries` row with the
date of the proving run in that country.

`jt doctor` must show the provider's check passing. Tell the user the site is
on and will be used by `/job-search`; they can turn it off in the panel, where
it shows as "Private".

## 6. Done for the user

Summarize: what the provider reads, how, its coverage, the proving runs, and
any risk the file states. If the user does not want to contribute it, stop
here: everything stays in their private folder.

## 7. Offer a pull request

Only when every country claimed has a successful proving run and validation
passes. Ask plainly: "This job site works. Do you want to offer it to the
project, so other people can use it? I would open a pull request on GitHub
with the provider file (and its reader and tests), and no personal data."
Without a clear yes, stop.

With a yes:

1. `gh auth status`. If `gh` is missing or signed out, tell the user how to
   install it or sign in (`! gh auth login`) and stop until they do.
2. `git status`: the working tree must be clean apart from `user-data/`;
   otherwise stop and ask.
3. If the user cannot push to this repository, `gh repo fork --remote`.
4. `git fetch` and a new branch `add-provider-<id>` from the latest `main`.
5. Copy the provider file to `providers/<id>.md`. If there is a reader: move
   it to `src/jobtracker/core/readers/<id>.py`, add `"<id>":
   "jobtracker.core.readers.<id>"` to `READERS` in
   `src/jobtracker/core/readers/__init__.py`, move its tests to
   `tests/test_<id>_reader.py` (fix their imports), and add any new
   dependency to an optional extra in `pyproject.toml`.
6. Write `openspec/changes/add-provider-<id>/` from
   `providers/change-template/` (proposal, `specs/provider-<id>/spec.md`,
   tasks). The study table and the proving runs are **rewritten**: generic
   titles, counts, dates, countries; no names, emails, companies the user
   applied to, search results, or anything from `user-data/`.
7. `ruff check .`, `python -m pytest`, `python scripts/check_private.py`, and
   `openspec validate add-provider-<id> --strict` when `openspec` is
   installed (otherwise say so in the pull request). Fix and repeat until they
   pass; never skip the privacy guard or the hooks.
8. Commit with a plain message ("Add <Site> as a job site"), push the branch,
   and `gh pr create` with the body of `.github/pull_request_template.md`
   filled in. Give the user the link.
9. The private copy stays as it is; it keeps working until the pull request
   is merged and the user updates, after which the repository's file takes
   over and the private one is reported as "id already used": tell the user
   they can then delete `<private_providers>/<id>.*`.

Any failing step: stop, tell the user what failed and what it would take;
nothing is forced.
