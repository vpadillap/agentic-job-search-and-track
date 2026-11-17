# Providers

One Markdown file per job site or salary source. The agent reads the file for
each enabled provider before touching that site and follows it literally.

- Copy `_template.md` to `<provider-id>.md` (lowercase, e.g. `linkedin.md`).
- Keep instructions concrete and verified: which tool to use, exact URL
  patterns, what to extract, how fast to go, and what must not be done.
- Update `last_verified` whenever you confirm the recipe still works. Sites
  change; a stale recipe should say so rather than guess.
- No personal data, cookies, or credentials in these files.

Whether a provider is enabled for a given user is stored in that user's
database (toggled from the panel), not here.
