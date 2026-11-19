## 1. Study (nothing is built before it)

- [x] 1.1 Search and posting pages, plain HTTP then Scrapling, logged out: listing, paging, filters, fields, structured data, refusals; robots.txt and terms
- [x] 1.2 One real search per country (PE, MX, CO, CL, AR, EC)
- [x] 1.3 Results table and recommended route in the proposal; owner approves

## 2. Provider

- [x] 2.1 `providers/computrabajo.md`: `kind: both`, search recipe, fields, form questions, limits, pitfalls, a verified row per country
- [x] 2.2 Reader (if the route is mechanical) with drafts as the other readers write them; tests on fictional pages
- [x] 2.3 README job-site tables (en/es)

## 3. Wrap-up

- [x] 3.1 A real search per country through the reader (2026-11-19: PE 10 new, MX 9, CO 59 of the 60 cap with one removed, CL 8, AR 1, EC 2; republished ones counted)
- [x] 3.2 `ruff check .`, full `pytest`, privacy guard, `openspec validate add-provider-computrabajo --strict`
