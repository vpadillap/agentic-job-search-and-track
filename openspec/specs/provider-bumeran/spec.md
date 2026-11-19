# provider-bumeran Specification

## Purpose

Defines how Bumeran Perú job postings are searched and read: through a real
browser visiting only the site's public pages, logged out, with conservative
pacing, without imitating a browser by other means and without ever applying.

## Requirements

### Requirement: Public pages in a real browser only
The Bumeran provider SHALL read Bumeran only by opening, in a headless stealth
browser session (Scrapling) without an account, saved cookies, or the user's
own browser profile, two kinds of public page: the search results page for one
title and posting age, and each posting's public page. It SHALL take the
postings from the data the site sends to those pages. Every Bumeran request
SHALL come from the system's Bumeran reader; the agent SHALL NOT request
Bumeran itself. The provider SHALL NOT send requests to Bumeran's API outside
a page the browser opened, and SHALL NOT use the user's Bumeran account or
browser. Because no account is involved, the session MAY get past the site's
automated checks; no browser window opens.

#### Scenario: Normal search
- **WHEN** a search runs with Bumeran enabled
- **THEN** Bumeran is read only through the public search page and public posting pages opened by the reader's headless session, without any account or stored cookie, and no window opens

#### Scenario: Requests only through the reader
- **WHEN** the agent searches Bumeran
- **THEN** it runs the reader command and sends no Bumeran request of its own

#### Scenario: Browser refused
- **WHEN** the site answers the session with a block or a challenge page it does not pass
- **THEN** Bumeran is recorded as failed for that run with what happened, and no other access method is tried

### Requirement: Never apply or write on Bumeran
The provider SHALL NOT click anything on Bumeran's pages, start or submit an
application, save postings, or report postings. Any request the pages try to
send to an application endpoint SHALL be cancelled.

#### Scenario: Reading a posting with questions
- **WHEN** the reader opens a posting whose form has questions
- **THEN** the questions are read from the posting's page data and no application request leaves the browser

### Requirement: The site's own filters
The provider SHALL search with the title and the posting age only. Posting
age SHALL use the smallest of Bumeran's windows (2, 3, 4, 5, 6, 7, 15, or 30
days) that covers the run's window; postings published before the run's
window are not stored. Without a window that covers the run (more than 30
days), no posting-age filter is applied and the run's window is applied to
the results.

#### Scenario: Seven-day window
- **WHEN** a run uses a 7-day window
- **THEN** each Bumeran search asks for postings published in the last week

#### Scenario: Ten-day window
- **WHEN** a run uses a 10-day window
- **THEN** each Bumeran search asks for the last 15 days, and postings published more than 10 days ago are not stored

### Requirement: Pacing and stop conditions
The provider SHALL wait at least 5 seconds between opening Bumeran pages,
including between separate calls of the reader in the same run, SHALL read at
most 2 result pages per target title, and SHALL open a posting's page at most
once per posting per run, only for postings published inside the run's window
and not already stored by an earlier run. HTTP 429 on a page or on the site
data, and a Cloudflare challenge page ("Just a moment…") that is not passed,
SHALL be handled by the provider-throttling policy: waiting and repeating the
page, then a cool-down after which the same run resumes. It SHALL stop all
Bumeran requests for the rest of the run on HTTP 403 or a Cloudflare block
page ("Attention Required", "Access denied"), and record the provider as
blocked with what happened. Postings already imported in that run are kept,
and any later call of the reader in that run SHALL be refused. A call SHALL
also be refused, without opening any page, while another call for the same run
is still running. It SHALL also stop, with reason `error`, when the browser
cannot load a page. A search with no results SHALL mean no postings for that
title and nothing else. When a search page sends no readable data in time, its
results have no ids, or a later results page is not the page asked for, the
reader SHALL load that page once more after the pacing wait; if it is still
wrong, or if two postings in a row in a title send no posting data, that is a
title problem: it SHALL end only that title, keep the postings already read
for it, state the problem in the reader's summary, leave Bumeran unrecorded as
failed, and let the next title be read normally. A single result without an id
SHALL be skipped and counted, and a single posting without data SHALL be
listed as unreadable; the title SHALL continue. Title problems SHALL NOT stop
the provider, however many titles have them. When the same problem has ended
every title that read anything in the run (two at least), the summary SHALL
say the site may have changed.

#### Scenario: Challenge mid-run
- **WHEN** Bumeran keeps showing a challenge page after the retries while the second title is being read
- **THEN** no further Bumeran page is opened until the cool-down ends, the postings from the first title remain, and the second title resumes in the same run after the cool-down

#### Scenario: Block page mid-run
- **WHEN** Bumeran shows a Cloudflare "Attention Required" page
- **THEN** no further Bumeran page is opened in that run and the provider is recorded as blocked

#### Scenario: Calling again after a block
- **WHEN** the reader is called for another title in a run where Bumeran was blocked
- **THEN** it opens no page and answers that Bumeran is stopped for this run

#### Scenario: Posting already stored
- **WHEN** the results list a posting that an earlier run already stored
- **THEN** its page is not opened again and the posting is recorded as seen in this run

#### Scenario: Calls in parallel
- **WHEN** the reader is called for a second title while the call for the first title of the same run is still running
- **THEN** the second call is refused without opening any page, and the agent is told to read the titles one at a time

#### Scenario: Pacing across calls
- **WHEN** the reader is called for the next title right after the previous call ended
- **THEN** its first page is opened at least 5 seconds after the last page of the previous call

#### Scenario: Titles with no results
- **WHEN** three titles in a row have no results
- **THEN** each is reported with no postings, nothing is retried, no title problem is recorded, and Bumeran goes on with the next title

#### Scenario: Search data back on retry
- **WHEN** a title's search page sends no readable data in time and the same page opened again after the pacing wait does
- **THEN** the title is read normally and the summary counts one retry

#### Scenario: One title's search sends no data
- **WHEN** a title's search page sends no readable data in time, also on the retry
- **THEN** that title ends with its postings so far, the summary states the problem, Bumeran is not recorded as failed, and the next title is read normally

#### Scenario: The same problem on every title
- **WHEN** every title read so far ends with the same title problem
- **THEN** every title is still tried, Bumeran is not stopped, and from the second such title on the summary says the site may have changed

#### Scenario: Second results page is not page 2
- **WHEN** a title's second results page answers with another page number, also on the retry
- **THEN** the postings of the first page are kept, the title ends with the problem stated, and the next title is read

### Requirement: Posting fields
For each posting the provider SHALL record Bumeran's numeric posting id as the
external id, the canonical `bumeran.com.pe/empleos/...` link, the title,
company (or "Confidential" when the company is hidden), and location as
shown, the country, the publication date as a calendar date, and the complete
description as plain text that keeps its paragraphs and list items, without
summarizing or translating it. Seniority and contract type SHALL be taken
from the posting's data, mapped to the system's contract types (full-time,
part-time, contractor) where they match and left empty otherwise.

#### Scenario: Complete posting
- **WHEN** a posting's list entry and its page are read
- **THEN** the posting carries the posting id, canonical link, title, company, location, country, publication date, complete description, seniority, and contract type

#### Scenario: Posting page unavailable
- **WHEN** a posting's page cannot be read but its list entry was
- **THEN** the posting is not imported, and the reader's summary lists its id and link with the reason

### Requirement: Form questions without applying
When a posting's data includes application-form questions, the provider SHALL
store them with the posting, in order, with their text and, for questions
with choices, the choices, without starting an application.

#### Scenario: Posting with two questions
- **WHEN** a posting's data lists two questions
- **THEN** the posting is stored with those two questions in the same order, and form answers can be prepared for it

#### Scenario: Posting without questions
- **WHEN** a posting's data has no questions
- **THEN** the posting is stored without form questions

### Requirement: What the site states is a hint, the agent decides
The provider SHALL pass the work mode, the salary range, and the contract
details that Bumeran states to the agent as hints in each draft. The agent
SHALL decide the work mode, its detail, the language, flags, and the
published salary by reading the title and description together with those
hints. A salary SHALL be recorded only when the posting states one; when the
site's work mode and the description disagree, the agent SHALL follow the
description and flag the disagreement.

#### Scenario: Hybrid stated by the site
- **WHEN** Bumeran states a posting is hybrid and the description says three days a week at the office
- **THEN** the posting is stored as hybrid with a work-mode detail that states the three days

#### Scenario: Site and description disagree
- **WHEN** Bumeran states "remote" but the description requires daily presence at the office
- **THEN** the posting is stored as onsite and carries a flag that the site's work mode disagrees with the description

#### Scenario: Salary range published
- **WHEN** a posting's data states a monthly salary range
- **THEN** the posting is stored with that range as its published salary

### Requirement: Drafts for the agent's reading
For each target title, the reader SHALL write a drafts file in the run's
capture folder with one import record per new posting: the fixed fields and
form questions filled in, the site's hints attached, and the fields that need
the agent's reading left empty. It SHALL print a short summary with the path
of that file and what it did.

#### Scenario: One title read
- **WHEN** the agent runs the reader for "Senior Data Engineer" in a run
- **THEN** a drafts file with one record per new posting is written in the run's capture folder, and the summary gives its path and the numbers of pages opened, postings found, postings outside the window, postings already seen, and new postings

### Requirement: Missing browser is reported
When Bumeran is enabled and Scrapling or its browser is not installed,
diagnostics and the reader SHALL name what is missing and how to install it,
and the reader SHALL open no page.

#### Scenario: Browser not installed
- **WHEN** the reader is called and Scrapling or its browser is not installed
- **THEN** it answers with the missing piece and the install command, and Bumeran is not recorded as searched

### Requirement: Terms-of-use risk is stated
The provider file SHALL state that Bumeran's terms of use (clause 1.5.1)
forbid using any software, tool, or agent other than the site's own search
tools to browse or search it, that the terms apply to visitors without an
account, and that the realistic consequence is that the site blocks the
user's IP address, so the user can decide whether to enable it.

#### Scenario: Reading the provider file
- **WHEN** the user or the agent reads `providers/bumeran.md`
- **THEN** the terms-of-use risk and its likely consequence are stated in it
