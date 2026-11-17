## 1. Data and services

- [ ] 1.1 Migration: statuses with stages, tags, application details, documents register, events, snapshot fields
- [ ] 1.2 Seed built-in statuses with English and Spanish names
- [ ] 1.3 Services: change status, create/rename/retire status, tags, details, next-step derivation
- [ ] 1.4 Event writing for every change; snapshot on first entry to the applied stage
- [ ] 1.5 Ghost and follow-up flags from thresholds (rule-adjustable)
- [ ] 1.6 Tests for every `application-tracking` scenario

## 2. Uploads and files

- [ ] 2.1 Upload endpoint with type and size checks, versioned storage in the application folder
- [ ] 2.2 Download endpoint confined to the private home
- [ ] 2.3 Rescore queue entry on upload
- [ ] 2.4 Tests for upload, replace, rejection, and path confinement

## 3. CLI

- [ ] 3.1 `jobtracker applications list|show|set-status|update` for agent use
- [ ] 3.2 `jobtracker pending` listing work items for the agent
- [ ] 3.3 CLI tests

## 4. Applications board

- [ ] 4.1 Funnel cards as stage filters
- [ ] 4.2 Attention summary with filters and the pending-work command
- [ ] 4.3 Table with document-state indicators, asked vs suggested, next step
- [ ] 4.4 Inline status picker with create-new and stage choice; tag editor
- [ ] 4.5 Filter bar, type-ahead, sorting, show-closed toggle, hidden count
- [ ] 4.6 Row detail: documents, form answers, details form, history
- [ ] 4.7 Upload and replace control for the sent resume
- [ ] 4.8 Browser tests for every `applications-board` scenario

## 5. Verification

- [ ] 5.1 Compare with board 2 of `design/panel-ux.html` in both languages
- [ ] 5.2 Confirm Search-board track actions land here with the right status
