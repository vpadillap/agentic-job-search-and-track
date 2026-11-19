## MODIFIED Requirements

### Requirement: Open-web search with reputable sources
The agentic-search provider SHALL find postings for each included title by
searching the web with several query families (title variants and
local-language synonyms, applicant-tracking `site:` queries, careers phrases,
and the careers pages of the leading employers of the user's sector in the
user's country), within the per-title search budget stated in its provider
file, using any web-search tools the agent has. It SHALL prefer the company's
own careers page or applicant-tracking board over copies of the same posting,
and SHALL NOT use aggregators that republish postings, pages without a
company name, or pages that require payment or personal data to show a
posting. It SHALL NOT request search-engine result pages through the reader.

#### Scenario: Posting found on an aggregator
- **WHEN** a posting is found on a site that republishes it and the company's own page has the same posting
- **THEN** the posting is read and recorded from the company's own page

#### Scenario: Untrusted page
- **WHEN** a page asks for personal data before showing the posting
- **THEN** the posting is not used

#### Scenario: Several query families
- **WHEN** the agent discovers postings for the title "Key Account Manager" for a profile in Peru
- **THEN** its searches include local-language variants of the title, applicant-tracking `site:` queries, and careers phrases, and stay within the file's search budget

#### Scenario: Sector employers
- **WHEN** a season has no list of leading employers for the profile's sector and country
- **THEN** the agent builds one from public sources with links, records each employer as a company, and later runs revisit them first

### Requirement: Sites with their own provider are not read
The provider SHALL NOT read a site that has its own provider file, whether
that provider is enabled or disabled, built-in or private. The reader SHALL
refuse, before any request, every link whose host is one of the `domains`
another provider file names.

#### Scenario: Posting only on a disabled provider's site
- **WHEN** a posting is found only on the site of a provider the user turned off
- **THEN** it is not read or imported

#### Scenario: Link on a provider's domain
- **WHEN** the agent passes a link on `pe.indeed.com` to the reader
- **THEN** the reader makes no request to it and lists it as refused because it belongs to another provider

#### Scenario: Private provider's domain
- **WHEN** the user added a private provider whose file names its domain
- **THEN** the reader refuses links on that domain too

### Requirement: Verbatim records with their source
Each posting SHALL be imported with its canonical URL as external id (tracking
parameters removed), the site it came from, the complete description taken
by the reader from the page itself, verbatim, and the publication date only
when the page states it. The agent SHALL NOT type or paste a description.

#### Scenario: Page without a date
- **WHEN** a posting's page does not show a publication date
- **THEN** the posting is imported without a date and flagged, and no date is guessed

#### Scenario: Structured posting data
- **WHEN** a page carries `JobPosting` structured data
- **THEN** the draft's title, company, location, date, and description come from that data, the description as plain text with its lines kept

## ADDED Requirements

### Requirement: Found links are read by the reader
The agent SHALL read the links it found through the reader command
(`jt providers read agentic-search <run> --title <title> --found <file>`),
which fetches each allowed link, saves the page in the run's capture folder,
and writes drafts. The reader SHALL read at most the provider file's maximum
number of pages per call and one call at a time per run.

#### Scenario: Reading found links
- **WHEN** the agent passes three posting links for a title
- **THEN** the reader fetches each one, saves its page and its numbered plain text in the capture folder, and returns drafts and a summary

#### Scenario: Posting already stored
- **WHEN** a found link's canonical URL was stored by an earlier run
- **THEN** the reader does not draft it again and it is recorded as seen

### Requirement: Polite fetching
The reader SHALL obey each host's `robots.txt` for its user agent, SHALL wait
at least the provider file's minimum (never less than the readers' common
minimum) between two requests to the same host, across calls of the same
run, SHALL identify itself with an honest user agent, and SHALL NOT open
sign-in, account, or application pages.

#### Scenario: Path disallowed by robots.txt
- **WHEN** a host's `robots.txt` disallows a found link's path for the reader
- **THEN** the reader does not request that page and lists it as refused by robots.txt

#### Scenario: Two pages on one host
- **WHEN** two found links are on the same host
- **THEN** the second request starts at least the minimum interval after the first

### Requirement: JavaScript pages are rendered with a plain headless browser
When a page answers without posting content because it needs JavaScript, the
reader SHALL render it once in a plain headless browser (no stealth, no saved
cookies, no sign-in) if the browser is installed, and otherwise SHALL report
the page as needing a browser with how to install it.

#### Scenario: Careers page rendered by JavaScript
- **WHEN** a careers page answers with an empty application shell and the browser is installed
- **THEN** the reader renders it in the headless browser and reads the rendered page

#### Scenario: Browser not installed
- **WHEN** a page needs JavaScript and the browser is not installed
- **THEN** the page is reported as needing a browser and the summary says how to install it

### Requirement: Refusals are respected
When a host answers `401`, `403`, `429`, or a challenge page, the reader SHALL
stop requesting that host for the rest of the run, SHALL NOT retry it with a
browser or another identity, and SHALL report it as refused. When the
refusing host is a job board, the agent SHALL offer the user to add it as a
provider instead of reading it here.

#### Scenario: Job board refuses plain requests
- **WHEN** a national job board with no provider file answers `403` to the reader
- **THEN** the reader makes no further request to that host in the run, reports it as refused, and the agent offers to add the board with `/add-provider`

### Requirement: Descriptions without structured data are cut, not retyped
For a page without `JobPosting` data, the reader SHALL return its numbered
plain text; the agent SHALL pass back the first and last line of the
posting, and the reader SHALL build the description from exactly those lines
of the saved page without a new request.

#### Scenario: Plain careers page
- **WHEN** a posting page has no structured data and the agent passes lines 12 to 48 of its capture
- **THEN** the draft's description is exactly lines 12 to 48 of the saved text, and no request is made

### Requirement: Originals are preferred over copies
The reader SHALL follow a page's pointer to the original posting (structured
`url`, canonical link, or an apply link to a company or applicant-tracking
host) and read the original instead, and within one run SHALL keep a single
draft per posting, from the most direct source, listing the copies it set
aside.

#### Scenario: Copy pointing to an applicant-tracking board
- **WHEN** a found page republishes a posting and links to the same posting on `jobs.lever.co`
- **THEN** the reader reads the Lever posting, drafts it from there, and lists the first page as a copy

#### Scenario: Same posting found twice
- **WHEN** two found links in a run carry the same company, title, and location, one on the company's own site and one elsewhere
- **THEN** only the company's own page is drafted and the other is listed as a copy

### Requirement: Careers listings are read
For a Lever or Ashby board link the reader SHALL read the board's public
postings API and draft the postings matching the title and the profile's
country or remote for it; for any other careers listing it SHALL return the
links whose text matches the title, for the agent to pass back.

#### Scenario: Lever board
- **WHEN** the agent passes `https://jobs.lever.co/example-co`
- **THEN** the reader reads the board's public API and drafts the matching open postings in the profile's country

#### Scenario: Generic careers page
- **WHEN** the agent passes a company careers page that lists openings
- **THEN** the reader returns the links whose text matches the title and drafts none of them until they are passed back

### Requirement: Closed postings are left out
The reader SHALL drop a posting whose structured `validThrough` date has
passed or whose page says it is closed.

#### Scenario: Expired posting
- **WHEN** a posting's `validThrough` is before today
- **THEN** it is not drafted and the summary counts it as closed
