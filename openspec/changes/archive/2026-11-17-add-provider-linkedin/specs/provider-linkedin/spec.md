## Purpose

Defines how the agent searches and reads LinkedIn job postings: logged out,
through LinkedIn's guest search and its public posting pages only, with
conservative pacing, and without ever touching the user's LinkedIn account.

## ADDED Requirements

### Requirement: Logged-out access only
The LinkedIn provider SHALL read LinkedIn only over plain HTTP, without
cookies, credentials, or any browser, through two kinds of pages: the guest
job search (`jobs-guest/jobs/api/seeMoreJobPostings/search`) for the list of
postings, and the public posting page (`jobs/view/<id>/`) for each posting.
It SHALL NOT use the user's LinkedIn session, a browser extension, browser
automation, or the `jobs/search` page, and SHALL NOT fall back to any of them.

#### Scenario: Normal search
- **WHEN** a search runs with LinkedIn enabled
- **THEN** every LinkedIn request goes to the guest search or a public posting page and carries no cookie or authorization header

#### Scenario: Guest search unavailable
- **WHEN** the guest search stops returning postings
- **THEN** LinkedIn is recorded as failed for that run with the reason, and no other access method is tried

### Requirement: Only the filters LinkedIn offers visitors
The provider SHALL send only the parameters LinkedIn offers logged-out
visitors: keywords, location, posting age, and paging. Posting age SHALL use
the smallest of LinkedIn's windows (24 hours, past week, past month) that
covers the run's window; postings older than the run's window are dropped at
import. Work mode and contract type SHALL NOT be sent as filters, because
LinkedIn ignores them for visitors; they are read from each posting instead.

#### Scenario: Seven-day window
- **WHEN** a run uses a 7-day window
- **THEN** each LinkedIn search requests the past week

#### Scenario: Three-day window
- **WHEN** a run uses a 3-day window
- **THEN** each LinkedIn search requests the past week, and postings published more than 3 days ago are not stored

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between LinkedIn requests, SHALL
read at most 3 result pages per target title, and SHALL open a posting's page
at most once per job id per run, only for postings published inside the run's
window. It SHALL stop all LinkedIn requests for the rest of the run on the
first throttling response or redirect to a login or sign-up page, and record
the provider as blocked with what happened. Postings already imported in that
run are kept.

#### Scenario: Throttled mid-run
- **WHEN** LinkedIn answers HTTP 429 while the second title is being searched
- **THEN** no further LinkedIn request is sent in that run, the provider is recorded as blocked, and the postings from the first title remain

#### Scenario: Login redirect
- **WHEN** a request is redirected to a login or sign-up page
- **THEN** the provider stops and is recorded as blocked, without following the redirect

### Requirement: Posting fields from the posting page
For each posting the provider SHALL record LinkedIn's numeric job id as the
external id, the canonical `linkedin.com/jobs/view/<id>/` link, the title,
company, and location as shown, the publication date the site states, and the
complete description verbatim from the posting page. Seniority and contract
type SHALL be taken from the posting page's criteria when present. A salary
SHALL be recorded only when the posting states one.

#### Scenario: Complete posting
- **WHEN** a posting's list entry and its page are read
- **THEN** the posting carries the job id, canonical link, title, company, location, publication date, complete description, seniority, and contract type

#### Scenario: Posting page unavailable
- **WHEN** a posting's page cannot be read but its list entry was
- **THEN** the posting is imported from the list entry with an empty description and a flag saying the description could not be read

### Requirement: Work mode read by the agent
The agent SHALL determine each posting's work mode (onsite, remote, hybrid) by
reading its title and complete description, and SHALL record, in the
posting's language, how the posting describes the arrangement when it says
more than the mode (for example, days on site per week or shortened Fridays).
When neither the title nor the description states the work mode, it SHALL be
left empty and the posting flagged as "work mode not stated"; it SHALL NOT be
guessed from the company, the location, or the search.

#### Scenario: Hybrid with details
- **WHEN** a description says the role is hybrid with two days a week at the office
- **THEN** the posting's work mode is hybrid and its work-mode detail states the two days a week at the office

#### Scenario: Not stated
- **WHEN** neither the title nor the description mentions where the work is done
- **THEN** the work mode is empty, the posting carries a "work mode not stated" flag, and it is not excluded for its work mode

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that LinkedIn's terms prohibit automated access
for logged-out visitors as well as members, that LinkedIn's robots.txt
disallows the guest search, and that the realistic consequence is throttling
or blocking of the user's IP address, so the user can decide whether to
enable it.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/linkedin.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it
