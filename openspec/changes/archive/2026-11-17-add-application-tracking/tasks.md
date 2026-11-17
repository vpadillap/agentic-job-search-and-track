## 1. Data and services

- [x] 1.1 Migration: statuses with stages, tags, application details, documents register, events, snapshot fields
- [x] 1.2 Seed built-in statuses with English and Spanish names
- [x] 1.3 Services: change status, create/rename/retire status, tags, details, next-step derivation
- [x] 1.4 Event writing for every change; snapshot on first entry to the applied stage
- [x] 1.5 Ghost and follow-up flags from thresholds (rule-adjustable)
- [x] 1.6 Tests for every `application-tracking` scenario

## 2. Uploads and files

- [x] 2.1 Upload endpoint with type and size checks, versioned storage in the application folder
- [x] 2.2 Download endpoint confined to the private home
- [x] 2.3 Rescore queue entry on upload
- [x] 2.4 Tests for upload, replace, rejection, and path confinement

## 3. CLI

- [x] 3.1 `jobtracker applications list|show|set-status|update` for agent use
- [x] 3.2 `jobtracker pending` listing work items for the agent
- [x] 3.3 CLI tests

## 4. Applications board

- [x] 4.1 Funnel cards as stage filters
- [x] 4.2 Attention summary with filters and the pending-work command
- [x] 4.3 Table with document-state indicators, asked vs suggested, next step
- [x] 4.4 Inline status picker with create-new and stage choice; tag editor
- [x] 4.5 Filter bar, type-ahead, sorting, show-closed toggle, hidden count
- [x] 4.6 Row detail: documents (open, copy cover letter), form questions (answers arrive with add-document-preparation), details form, history
- [x] 4.7 Upload and replace control for the sent resume
- [x] 4.8 Browser tests for every `applications-board` scenario

## 5. Verification

- [x] 5.1 Compare with board 2 of `design/panel-ux.html` in both languages
- [x] 5.2 Confirm Search-board track actions land here with the right status
