## What this changes

<!-- One or two sentences. For a change with an OpenSpec folder, name it. -->

## Checks

- [ ] `ruff check .` passes
- [ ] `pytest` passes
- [ ] The privacy guard passes (`python scripts/check_private.py`); nothing from `user-data/`, no names, emails, or phone numbers
- [ ] `openspec validate <change> --strict` passes (or say why it could not run)

## New job site (only for a new provider)

- [ ] Studied with real requests; the routes and results are in `openspec/changes/add-provider-<id>/proposal.md`
- [ ] `providers/<id>.md` is valid and states coverage (`regions`), access, login/presence, terms of use, stop conditions
- [ ] Proved with a real search in each country it claims (counts only, no personal data)
- [ ] No credentials through automation; a signed-in account is only used by the user, in their own browser
- [ ] A reader, if any, has tests with fictional pages only
