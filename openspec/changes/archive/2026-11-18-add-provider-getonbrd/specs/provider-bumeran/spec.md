## MODIFIED Requirements

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

### Requirement: Missing browser is reported
When Bumeran is enabled and Scrapling or its browser is not installed,
diagnostics and the reader SHALL name what is missing and how to install it,
and the reader SHALL open no page.

#### Scenario: Browser not installed
- **WHEN** the reader is called and Scrapling or its browser is not installed
- **THEN** it answers with the missing piece and the install command, and Bumeran is not recorded as searched
