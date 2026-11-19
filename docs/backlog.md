# Backlog

Issues found outside the change being applied. Each one needs its own OpenSpec
change (or a decision to drop it). Nothing here is scheduled.

## A registered document version cannot be withdrawn

- **Found:** 2026-11-17, during a real run. A tailored resume registered by mistake
  (here, with corrupted accents from a stdin encoding bug, since fixed) stays
  in the application's history; only a newer version can replace it.
- **Spec:** `document-preparation` forbids modifying earlier versions; a
  "withdraw" (hide, keep the file) would need its own change.
