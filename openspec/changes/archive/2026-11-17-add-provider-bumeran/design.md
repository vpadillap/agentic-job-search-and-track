## Context

See proposal.md for the motivation. The provider mechanism and the LinkedIn
reader exist (`core/readers/`, `jt providers read <id>`, drafts plus readings
at import, run state and lock in the capture folder). This change adds the
second reader, the first one that needs a browser.

### Study (2026-11-17, no account, no cookies, generic query "data engineer")

| Request | Result |
|---|---|
| `robots.txt` (curl) | 200. Disallows only `*recientes=true`, `*relevantes=true`, the `localidades` parameter, and a few listing paths; `/api/` is not disallowed |
| search page `/empleos-busqueda-data-engineer.html` (curl) | 200, 63 KB, the same empty application shell as every page: no postings, no JSON-LD |
| `sitemap_avisos_bum.xml` (curl) | 200, 7 MB, ~35,000 posting URLs, every `lastmod` the same day: useless for posting age |
| `/llms.txt` (curl) | 200: the site's own URL patterns for searches (`empleos-busqueda-<title>.html`, `empleos-publicacion-hoy.html`, by seniority, full-time); nothing on automated access |
| `POST api/avisos/searchV2` and `GET api/candidates/fichaAvisoNormalizada/<id>` (curl, anonymous session as the site's script does) | **403 from Cloudflare**, "Sorry, you have been blocked". `robots.txt` still 200 right after: the firewall refuses non-browser clients on `/api/`, not the IP |
| search page in Chromium (Playwright, visible window), 3 page loads ~30 s apart | 200 everywhere, no challenge. The page itself calls `POST api/avisos/searchV2?pageSize=20&page=0&sort=RELEVANTES` with body `{"filtros":[…],"query":"data engineer"}` and headers `x-site-id: BMPE`, `x-session-jwt` (anonymous session the site issues) |
| `/empleos-publicacion-menor-a-7-dias-busqueda-data-engineer.html` in Chromium | the page sends `filtros: [{"id":"dias_fecha_publicacion","value":"publicacion-menor-a-7-dias"}]`; 6 results, matching the site's own count for that window |
| a posting page in Chromium | the page calls `GET api/candidates/fichaAvisoNormalizada/<id>` |

`searchV2` answers `{number, size, total, content[20], filters, filtersApplied}`.
A list entry has `id`, `titulo`, `empresa`, `localizacion` ("Lima, Lima"),
`fechaPublicacion` ("09-11-2026", day first), `fechaHoraPublicacion`,
`modalidadTrabajo` ("Presencial", "Híbrido", "Remoto"), `tipoTrabajo`
("Full-time"), `confidencial`, `tienePreguntas`, `detalle` (a ~1 KB excerpt).
`filters` lists the posting-age windows the site offers: `publicacion-menor-a-
{2,3,4,5,6,7,15}-dias` and `publicacion-menor-a-1-mes`.

`fichaAvisoNormalizada` answers `{aviso, avisosSimilares, …}`; `aviso` has
`id`, `titulo`, `descripcion` (complete, HTML), `empresa.denominacion`,
`empresa.confidencial`, `localizacion` (province and district ids and names),
`fechaPublicacion`, `fechaFinalizacion`, `estado`, `modalidadTrabajo`,
`tipoTrabajo`, `tipoContratacion` ("Indeterminado", "Temporal"),
`nivelLaboral` ("Semi Sr"), `requisitos.salario` (`salarioMinimo`,
`salarioMaximo`, often null), `preguntas` (for example
`[{"simple": {"id": …, "texto": "¿Cuántos años de experiencia…?"}}]`), and
`seoFriendlyUrl` (`/empleos/data-engineer-gcp-entelgy-1118664666.html`).

The site also has `api/candidates/aviso/<id>/postularV2` (applying), which the
pages call only when the user clicks to apply.

**Terms** (read in the browser; last updated 2026-10-01). Clause 1.5.1
"Usos prohibidos" forbids "el uso o intento de uso de cualquier máquina,
software, herramienta, agente u otro mecanismo para navegar o buscar en este
Sitio Web que sean distintos a las herramientas de búsqueda provistos por
BUMERAN", and reverse engineering of the site's software. "Usuario" covers
everyone who accesses the site; access needs no registration. Clause 1.5.2
allows suspending users. The owner decided to accept this risk; the provider
file states it.

**Study, part 2** (tasks 1.1–1.3, same day, Playwright's Chromium, fresh
context, `es-PE`, images/fonts/media and any `postular` request cancelled,
6 s or more between loads, 10 loads in total):

| Request | Result |
|---|---|
| 7-day search, page 2 of a search, a posting by id, **headless** | **403 "Attention Required! \| Cloudflare"** on all three, no API response |
| the 7-day search, **visible window**, 20 s later | 200, `searchV2` answered 200 |
| `/empleos-busqueda-analista.html?page=2`, visible | 200; the page asked `searchV2?…&page=1` and the response says `number: 1` (zero-based): `?page=N` is page N |
| `/empleos/1118664666.html` (id only), visible | 200; the site moves to the canonical `/empleos/data-engineer-gcp-entelgy-1118664666.html` and the page asks `fichaAvisoNormalizada/1118664666` (sometimes twice) |
| 4 more postings by id, visible | 200 each. Question shapes: `{"simple": {"id", "texto"}}` and `{"choice": {"id", "texto", "opciones": [{"id", "opcion"}], "indiceCorrecta"}}`. No salary range in 6 postings; 4 had `requisitos.salario.solicitarCandidato: true` (the form asks the expected salary) |

So the reader runs Chromium in a **visible window** (B2), list entries are
opened as `/empleos/<id>.html` (B5), and page 2 is `?page=2`.

**Dry run** (task 4.2, the finished reader, a temporary home, one title "Data
Engineer", 7-day window): 7 page loads, 6 postings, no block; drafts imported
with readings; 22 form questions stored (choice questions with their
options); run report found 6 / new 6, Bumeran `ok`.

## Goals / Non-Goals

**Goals:** read Bumeran with the same guarantees as LinkedIn (fixed work in
code, pacing across calls, stop on first block, drafts plus readings), using
the site's own structured fields, and never applying.

**Non-Goals:** a general browser-reader framework (only what Bumeran needs);
refactoring the LinkedIn reader; any panel change.

## Decisions

### B1. A real browser on public pages, reading the responses the pages get
The reader opens the public search page and each posting page in Chromium
(Playwright, sync API) and captures the JSON responses whose URL matches
`api/avisos/searchV2` and `api/candidates/fichaAvisoNormalizada/`. The site's
own script creates the anonymous session and sends the requests; the reader
creates nothing and calls no API.

Alternatives: plain HTTP to the API (403 from Cloudflare in the study; making
it pass needs TLS impersonation or borrowed Cloudflare cookies, which is
evasion and forbidden); Scrapling (its plain fetcher is plain HTTP, its
stealth mode is evasion); the user's Chrome through the extension (puts the
user's Bumeran account at risk and needs the user present); reading the
rendered DOM instead of the responses (more fragile, loses the structured
fields and the questions); the sitemap (no usable dates, and pages still need
a browser).

### B2. A visible browser window (decided by the study)
Cloudflare blocked headless Chromium on every page and served the same pages
to a visible window. The reader therefore launches Chromium with a visible
window, unchanged: no stealth plugins, no edited user agent or fingerprint.
The window opens during a Bumeran search and closes when the call ends; the
provider file says so, and that the user should not interact with it. If the
visible window is blocked too, the reader stops (B8) and a new change
revisits it.

Alternatives: headless (blocked in the study); headless with stealth plugins
or a spoofed user agent (evasion, forbidden); the user's own Chrome (account
risk, needs the user present).

### B3. A fresh browser context per call, nothing kept
Each call starts a new incognito-like context: no cookies or storage are read
or saved, so nothing of the user's or of earlier runs is reused. Locale
`es-PE`, a normal desktop viewport, Playwright's default user agent for the
installed Chromium (never edited).

Alternatives: a persistent profile in the capture folder (keeps Cloudflare
and session cookies between runs, which is reuse of clearance by another
name).

### B4. What the browser may load
Requests to images, fonts, and media are cancelled to keep page loads light,
and any request whose path contains `postular` is cancelled as a guard so no
application can leave the browser even if a page misbehaves. Scripts, the
site's API, and Cloudflare's own scripts are left alone. The reader never
clicks or types on the page; navigation is only `goto` to the two URL forms.

Alternatives: cancelling third-party analytics too (changes how the page
behaves for Cloudflare; not needed); no guard (relies only on never clicking).

### B5. URLs and the posting-age window
Search URL: `https://www.bumeran.com.pe/empleos-publicacion-<window>-busqueda-
<slug>.html`, where `<slug>` is the title lowercased, accents removed, and
non-alphanumerics replaced by single hyphens, and `<window>` is the smallest
of `menor-a-2-dias` … `menor-a-7-dias`, `menor-a-15-dias`, `menor-a-1-mes`
covering the run's `posting_age_days`; above 30 days the URL has no window
(`/empleos-busqueda-<slug>.html`) and the run's window is applied to the
dates. Page 2 is the same URL with `?page=2`; the reader checks that the captured
response's `number` is 1 (zero-based) and stops with `error` otherwise. A
posting is opened as `/empleos/<id>.html` (list entries carry no link); the
site moves to its canonical URL, and the stored link is the posting data's
`seoFriendlyUrl` on `https://www.bumeran.com.pe`.

Alternatives: injecting filters into the request body (that is calling the
API); the `localidades` parameter (disallowed by robots.txt).

### B6. Pacing, page cap, lock, state
Same mechanics as the LinkedIn reader, in its own files: `bumeran-state.json`
(time of the last page opened, ids opened in this run, drafts written, page
counter) and `bumeran.lock` (exclusive, stale after 30 minutes) in the run's
capture folder; pacing is between page navigations (at least
`min_seconds_between_requests`, never under 5). `max_results_per_query: 40`
gives 2 pages of 20. Each captured JSON is saved as `bumeran-<n>.json` for
audit. Plain-text conversion of descriptions reuses the LinkedIn reader's
helper (same rules: paragraphs, "• " list items, unescaped entities).

Alternatives: extracting a shared reader base now (touches the LinkedIn
reader; deferred until a third reader shows what is really common).

### B7. Each list entry
In order: a date before `published_since` → outside the window; an id already
opened in this run → duplicate; an id Bumeran already stored in an earlier run
→ imported as seen from the stored posting (no page opened); otherwise its
posting page is opened and it becomes a draft. A posting page whose data says
`estado` is not active, or that never sends its data within 30 s, is listed as
unreadable with its link and reason.

### B8. Stop conditions
Blocked (stop the provider for the run, record `run provider bumeran failed
--reason blocked --detail …`): a main document with status 403 or 429, a
Cloudflare challenge or block page (title "Just a moment…" or "Attention
Required!", or the challenge form), or a captured API response with 403 or
429. Error (same recording, reason `error`): the search page sends no
`searchV2` response within 30 s, a response that is not the expected JSON
shape, a page number mismatch. A search with `total: 0` is no results, not an
error.

### B9. Draft fields
Fixed: `external_id` (id as text), `url` (canonical), `title`, `company`
(`empresa.denominacion`; "Confidencial" when `confidencial`), `location`
(as shown), `country: "PE"`, `posted_at` (day-first date to ISO), `seniority`
(`nivelLaboral.nombre`), `contract_type` (`tipoTrabajo`: Full-time →
`full-time`, Part-time → `part-time`; "Por Contrato"/"Temporario"-like values
and anything else left empty), `description` (plain text of `descripcion`),
`form_questions` (`simple` → text question; `choice` → choice question with
the texts of its `opciones`; unknown shapes → text question with its visible
text, and a note in the summary). `indiceCorrecta` (the answer the employer
expects) is never stored or shown: answers must be truthful, not tuned to
pass a screen. Hints for the agent, ignored by the import:
`site_work_mode` (presencial → onsite, híbrido → hybrid, remoto → remote),
`site_contract` (`tipoContratacion`), `site_salary`
(`{min, max}` as given, or null), `asks_expected_salary`
(`requisitos.salario.solicitarCandidato`), `closing_date`
(`fechaFinalizacion`).
Readings stay exactly as today: `work_mode`, `work_mode_detail`, `language`,
`flags`, `published_salary`.

Alternatives: filling `work_mode` from the site directly (the import's
reading contract would have to change, and the description sometimes
contradicts the site; the agent confirms in one pass).

### B10. Dependency and diagnostics
`pyproject.toml` gains the optional group `browser = ["playwright>=1.45"]`.
The provider file declares `dependencies: [playwright]`; `jt doctor` already
checks it as an importable module and `INSTALL_HINTS` already says how to
install the package and Chromium. The reader also catches a missing browser
executable and answers `missing_dependency` with
`python -m playwright install chromium`, before opening any page and without
recording the provider as searched.

Alternatives: making Playwright a core dependency (every user downloads it,
even without Bumeran).

### B11. Tests without the network
The browser is behind a small interface (open a page, return the captured
responses and the document status/title); tests use a fake that serves
fictional JSON fixtures (persona-safe companies and texts), so no test opens
a real browser or touches bumeran.com.pe. One live check, marked like the
browser tests and skipped by default, opens one search page to confirm the
recipe still works.

## Risks / Trade-offs

- [Cloudflare starts challenging the automated browser] → The reader stops at
  the first challenge and records it; no evasion; a new change revisits.
- [The site changes its JSON or URL patterns] → Shape checks stop with
  `error` naming what is missing; fixing it is a provider change.
- [The terms forbid this; Bumeran may block the user's IP] → Stated in the
  provider file; off until the user enables it; low volume and pacing.
- [A call is slow (browser start plus pages at 5 s)] → One title per call:
  about 2 search pages plus up to ~20 postings, a few minutes.
- [Playwright and Chromium are a large download] → Only for users who enable
  Bumeran, through the optional group.

## Migration Plan

None: no schema change. Provider file, reader, skill note, and optional
dependency land together; Bumeran stays off until each user enables it.

## Open Questions

None. The shape of a published salary range was not seen in the study
(6 postings); the reader takes `salarioMinimo`/`salarioMaximo` as given and
passes them as a hint only, so a different shape changes nothing stored.
