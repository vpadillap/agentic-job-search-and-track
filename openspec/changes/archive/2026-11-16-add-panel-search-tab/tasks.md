## 1. Data and API

- [x] 1.1 Migration: search runs, postings, run results, dismissals, minimal applications record
- [x] 1.2 Services: latest run summary, list results, track, track-and-apply, dismiss, undo
- [x] 1.3 API routes for runs, results, and row actions; host-header check
- [x] 1.4 `jobtracker demo seed` with fictional runs and postings
- [x] 1.5 API tests for every action and for the host-header check

## 2. Panel shell

- [x] 2.1 Static hosting, `index.html`, tokens from the design, self-hosted fonts
- [x] 2.2 Vendor Preact + htm with version and license note
- [x] 2.3 Header: brand, profile chip, pending indicator, freshness, language toggle
- [x] 2.4 Hash-based tabs with counters and persisted selection; placeholders for unbuilt boards
- [x] 2.5 i18n loader, `locales/en.json` and `locales/es.json`, `Intl` formatting
- [x] 2.6 Change polling with edit protection
- [x] 2.7 Copyable command chip component; empty states
- [x] 2.8 Browser tests for every `panel-shell` scenario

## 3. Search board

- [x] 3.1 Run summary with provider chips, skipped-provider notices, and filtered-out list
- [x] 3.2 Reusable data table: sortable columns, selection, expandable rows
- [x] 3.3 Filter bar: type-ahead, work mode, contract, minimum score, provider, has salary; hidden-rows footer
- [x] 3.4 Row detail: verbatim description, score breakdown, salary suggestion with evidence
- [x] 3.5 Row and bulk actions with undo toast; dismiss reasons
- [x] 3.6 Earlier-run selector
- [x] 3.7 Browser tests for every `search-results-board` scenario against the demo seed

## 4. Verification

- [x] 4.1 Compare the board with `design/panel-ux.html` side by side in both languages
