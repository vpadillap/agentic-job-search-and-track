# Changelog

What each update brings, in plain words, newest first. One entry per change
merged into `main`. The agent reads it to tell you what an update brings
(`/update`); the last three lines of each entry are for it: the job or salary
sites the change adds, the one-time offers it brings, and anything you must do.

## 2026-11-20 · job-search-live-results

Changed
- Search results reach the panel while the search goes on: each batch of postings is filtered and scored right away, so you can start reviewing and tracking postings long before a long search ends. Postings still being scored show "Scoring…", and the search summary shows how many sites are done, how many postings are scored, and when a paused site resumes.
- A site that asks the agent to slow down no longer holds up the others: the agent goes on with the rest and comes back to it when its pause ends.
- The agent uses at most 3 helpers at the same time, however many titles and sites you have, so a large search does not use up your usage limit.

Providers: none
Offers: none
Action: none

## 2026-11-19 · fix-salary-sources-without-country

Fixed
- Before your profile has a country, the diagnosis no longer asks for the tools of every salary source; once the country is set, it checks only the sources of that country.

Providers: none
Offers: none
Action: none

## 2026-11-19 · salary-sources-always-on

Changed
- Salary sources are no longer switched on or off: the agent uses the ones that serve each posting's country (Glassdoor, Indeed, Computrabajo, Payscale, Talent.com) and installs what they need. The job-site switches are only about searching postings.

Providers: none
Offers: none
Action: none

## 2026-11-19 · add-provider-computrabajo

Added
- Computrabajo is a job site in Peru, Mexico, Colombia, Chile, Argentina, and Ecuador. Republished postings count (a company that republishes is still hiring), with their first publication date noted; confidential postings are read too.

Providers: computrabajo
Offers: none
Action: turn it on in /setup (job sites) if you search in one of those countries

## 2026-11-19 · add-changelog

Added
- This changelog: every update says here, in plain words, what it adds, changes, or fixes.
- Ask "is it worth updating?": the agent answers from the changelog. After an update, it offers to turn on each new job site and to search it right away, alone or with the day's full search.

Providers: none
Offers: none
Action: none

## 2026-11-19 · rework-salary-research

Added
- The suggested salary is now the agent's analysis: it looks at everything available (what the posting offers, the offers you received and the salaries other postings published, with each company's industry and size), searches only what is missing, and explains its range in a short note.
- The salary column shows the salary the posting offers and the range to ask for, with how many sources of each kind support it; the detail lists every source and what was set aside and why.
- Salary pages of Indeed (every country), Computrabajo (Peru, Mexico, Colombia, Chile, Argentina, Ecuador), Payscale, and Talent.com as salary sources, each switched off until you turn it on.
- Market research is reused for the same role, level, and country for 30 days, whatever the company, so the same searches are not repeated.

Changed
- One source can be enough when it is about the same company or from your own history; market data alone still needs two.
- The currency of the salaries you asked for and were offered starts from the most likely one (the posting's, your profile's, the country's) instead of PEN; any currency can be typed.

Providers: computrabajo, payscale, talent
Offers: none
Action: none

## 2026-11-19 · improve-table-layout

Changed
- The Search and Applications tables fit the screen from 1,280 pixels up; on narrower screens secondary columns move into the row's detail, and on a phone each row becomes a card.
- "Already applied" and "Dismiss" are compact icon buttons; the link to the posting sits under the company.

Providers: none
Offers: none
Action: none

## 2026-11-19 · group-searches-by-day

Added
- Searches made on the same day are shown on one page, with their counts added up and each posting once. When you search again on a later day in the same chat, the agent asks whether to join it to the earlier one.

Providers: none
Offers: group-searches-by-day
Action: none

## 2026-11-19 · add-self-update

Added
- Ask "update the project" (or `/update`): the agent tells you what is new, and with your yes brings it and leaves everything working, without touching your data.

Providers: none
Offers: none
Action: none

## 2026-11-19 · fix-python-on-windows

Fixed
- On Windows, the privacy check no longer fails when `python` is only the Microsoft Store's shortcut; setup installs Python itself when needed.

Providers: none
Offers: none
Action: none

## 2026-11-19 · fix-provider-glassdoor

Fixed
- Glassdoor searches and salary pages work again where they had returned nothing (for example Peru, commercial and marketing titles).

Providers: none
Offers: none
Action: none

## 2026-11-19 · retry-soft-blocks

Changed
- When a site asks to slow down, the search waits and tries again instead of giving up on that site for the whole search.

Providers: none
Offers: none
Action: none

## 2026-11-19 · end-title-on-page-error

Fixed
- One odd page on a job site no longer stops that site for the rest of the search: only that title is skipped.

Providers: none
Offers: none
Action: none

## 2026-11-19 · fix-browser-install-windows

Fixed
- On Windows inside the Claude desktop app, the sites read with a browser session (Indeed, Glassdoor, Bumeran) start their browser correctly after installing it.

Providers: none
Offers: none
Action: none

## 2026-11-19 · deepen-agentic-search

Changed
- The web search for companies' own careers pages searches more widely, reads pages built with JavaScript, and helps job seekers outside tech.

Providers: none
Offers: none
Action: none

## 2026-11-18 · update-docs-for-release

Changed
- The README and guides describe everything the project does, in English and Spanish.

Providers: none
Offers: none
Action: none

## 2026-11-18 · improve-skill-invocation

Added
- You can ask in plain words, in English or Spanish ("busca trabajo de esta semana"), instead of typing a command.

Providers: none
Offers: none
Action: none

## 2026-11-18 · add-provider-contribution

Added
- Add a job site the project does not cover yet with `/add-provider`; once it works for you, the agent can offer it to the project.

Providers: none
Offers: none
Action: none

## 2026-11-18 · add-provider-getonbrd

Added
- Get on Board as a job site (Latin America and remote), through its public API.

Providers: getonbrd
Offers: none
Action: none

## 2026-11-18 · add-provider-agentic-search

Added
- A web search for openings on companies' own careers pages, which remembers the companies it finds.

Providers: agentic-search
Offers: none
Action: none

## 2026-11-18 · add-provider-greenhouse

Added
- Greenhouse as a job site, through its public job-board API for each company.

Providers: greenhouse
Offers: none
Action: none

## 2026-11-18 · add-provider-glassdoor

Added
- Glassdoor as a job site and as a source of salary reports.

Providers: glassdoor
Offers: none
Action: none

## 2026-11-18 · add-provider-coverage

Added
- Job sites are global or local; setup offers the global ones and those of your country, and the panel lets you filter them by country.

Providers: none
Offers: none
Action: none

## 2026-11-17 · first release

Added
- Setup, job search with scoring and salary evidence, application tracking, document preparation, the learning loop, seasons, and the local panel; LinkedIn, Indeed, and Bumeran Perú as job sites.

Providers: linkedin, indeed, bumeran
Offers: none
Action: none
