# Agentic Job Search and Track

A clone-and-run, local-first job search assistant driven by an AI agent, built
for [Claude Code](https://claude.com/claude-code).

**[Español más abajo](#español)**

- The **agent** sets everything up from your resume and a short questionnaire,
  searches job sites, scores each posting against your profile, researches
  salary evidence, and drafts tailored resumes, cover letters, and form answers.
- A **local web panel** (English or Spanish) shows the latest search, tracks
  every application and its status, and lets you record what really happened.
- A **learning loop** uses your real outcomes to tune future searches, scores,
  and advice.

Everything personal stays on your machine, in one folder that git ignores.

## Status

Everything below works today.

| Area | What you get |
|---|---|
| Setup (`/setup`) | Requirements, panel language, your resume in each language you apply in, the job-needs questionnaire, target titles researched with you, job sites, your standing rules |
| Job search (`/job-search`) | Seven job sources (below), filtering with reasons, scoring, salary evidence with links, the Search tab |
| Applications | Statuses, tags, details, the resume you sent, history, the Applications tab |
| Documents (`/prepare-documents`, `/form-answers`) | Tailored resumes, cover letters, and application-form answers, in each posting's language |
| Learning (`/analyze-results`) | What is working, lessons you apply or ignore, interview-chance estimates once your own results validate them |
| Seasons (`/new-season`) | Start a new campaign; earlier seasons stay viewable; export; full reset to an archive |
| Panel (`/panel`) | Search, Applications, Learning, and Profile & agent tabs, on your own computer |
| Your own job sites (`/add-provider`) | Add a site the project does not cover, prove it, and offer it back |

## Requirements

- Python 3.11 or newer
- [Claude Code](https://claude.com/claude-code)
- Git

Nothing else needs to be installed by hand. Setup installs the Python packages
into a `.venv` folder inside the project, and before a search the agent
installs whatever a job site you turned on needs (for example Scrapling, about
150 MB) and tells you.

## Quick start

```
git clone <this repository>
cd agentic-job-search-and-track
claude
```

Then, inside Claude Code, type `/setup`, or just say "set up the job tracker".

The agent will:

1. Check your environment and install what is missing (it asks first).
2. Ask whether you want the panel in English or Spanish.
3. Create your private workspace.
4. Ask in which languages you will apply, and for your resume (PDF or DOCX)
   in each one; for a language you have none in, it offers to translate one of
   yours as a draft you review.
5. Ask about the job you want: remote/hybrid/onsite, contract type, country
   and places, minimum salary, languages, and so on. Every question can be
   skipped.
6. Ask which job titles you want, look at how the market names similar roles,
   and propose alternates for you to include or exclude.
7. Offer the job sites that serve your country and turn on the ones you pick.
8. Record your standing preferences (for example: never change my resume's
   layout) and give you a short tour.

You can stop at any time; running `/setup` again continues where you left off.
Run it again later to change any answer.

## Asking the agent

Type a command, or just ask in plain words, in English or Spanish: the agent
loads the right command and asks only for what is missing.

| Command | What it does | You can also say |
|---|---|---|
| `/setup` | First run, and later changes to your profile, titles, sites, or rules | "change my target titles", "turn on Get on Board" |
| `/job-search days=7` | Searches the job sites you turned on and updates the panel | "do a job search for this week", "any new postings?" |
| `/prepare-documents pending` | Tailored resumes, cover letters, and form answers that tracked jobs lack (or `ids=J0007,J0012`, or `all`) | "complete the missing documents for J0007" |
| `/form-answers ids=J0007` | Answers to a posting's application form (`alternative` for another version) | "answer the form for J0007" |
| `/analyze-results` | Reviews your results and proposes lessons | "how am I doing?", "why does nobody call me?" |
| `/new-season` | Starts over with a new or updated profile; the previous campaign stays viewable | "I'm back after six months, let's start fresh" |
| `/add-provider` | Adds a job site the project does not cover yet | "add Computrabajo as a job site" |
| `/panel` | Starts or stops the local panel | "open the panel" |

Spanish users also get Spanish command names (see the Spanish section). You
can also tell the agent standing rules in plain words, such as "don't show me
outsourcing consultancies" or "never change my resume layout". It stores them
and follows them from then on.

## Job sites

Every site starts **switched off**: you choose which ones to use in `/setup`
or in the panel, so an update never starts searching a new site on its own.
*Global* sites serve many countries; a *local* site serves only its
countries, and setup offers you the global ones plus those of your country.

| Site | Coverage | How it is read |
|---|---|---|
| LinkedIn | global | Public job pages, logged out, never with your account |
| Indeed | global | A headless browser session (no window, no account); several first pages per title, since Indeed shows only one page of results when logged out |
| Glassdoor | global, also salaries | A headless browser session (no window, no account); also reads Glassdoor's salary reports as one source of salary evidence |
| Greenhouse | global | Greenhouse's public Job Board API for each company; companies are found through your signed-in MyGreenhouse search when you are present, or through a web search otherwise |
| Get on Board | global (mostly Latin America and remote) | Get on Board's free public API |
| Bumeran Perú | local: PE | A headless browser session (no window, no account) |
| Web search (company sites) | global | The agent searches the open web for companies' own careers pages and remembers the companies it finds |

Each site's file in [`providers/`](providers/) says exactly how it is read and
what is never done there. Be aware of each site's terms of use: LinkedIn,
Indeed, Glassdoor, and Bumeran forbid automated access, so they may limit or
block your connection for a while (no account of yours is ever involved).
Greenhouse's and Get on Board's APIs are public; Get on Board asks that its
jobs be shown with their source and a link, which the panel does.

### Adding your own job site

Run `/add-provider` (or say "add <site> as a job site"). The agent studies the
site with you, builds the provider in your private folder
(`user-data/providers/`), proves it with a real search in each country it
claims, and turns it on just for you. Once it works, it offers to contribute it
to the project as a pull request, only with your yes and without any personal
data. The rules are in [`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md).

## What the agent will and will not do

- It never applies to a job, sends a message, or changes anything in your
  accounts on job sites. It prepares; you apply.
- It never invents facts. A salary is suggested only when at least two
  comparable, linked sources support it; otherwise you see "no reliable data".
  Resumes and form answers never claim experience you do not have.
- It does not change your resume's layout without your consent.
- It writes documents in the language of each job posting, whatever language
  the panel is in, starting from your own resume in that language.
- Lessons it learns from your results take effect only after you approve them.

## Your data and privacy

- Everything personal (resume, profile, applications, documents, database,
  your own job sites) is stored in `user-data/` inside the project folder. Git
  ignores that folder.
- A pre-commit guard refuses any commit that contains files from that folder,
  resume or database files, or your name, email, or phone number.
- The panel is served only on your own computer (`127.0.0.1`).
- To back up your data, copy `user-data/`, or ask for an export. To keep it
  somewhere else, set the `JOBTRACKER_HOME` environment variable to another
  folder before running setup.
- Nothing is deleted by the tool. A full reset moves your data into
  `user-data/archive/`.

The exact layout of the private folder is documented in
[`docs/workspace-layout.md`](docs/workspace-layout.md).

## The command-line interface

The agent does all its reading and writing through one tool, which you can use
too. It prints JSON.

```
python scripts/jt.py doctor          # check the environment; changes nothing
python scripts/jt.py context         # profile, rules, and state the agent works from
python scripts/jt.py profile show    # your job needs and target titles
python scripts/jt.py providers list  # the job sites, their coverage, and whether they are on
python scripts/jt.py rules list      # the rules the agent follows
python scripts/jt.py paths           # where everything is stored
```

To try the panel with invented data, point `JOBTRACKER_HOME` at an empty
folder, then run `jt.py init`, `jt.py demo seed`, and `jt.py panel` (and
`jt.py demo clear` to remove it). The demo refuses to mix with real search
results.

`python scripts/jt.py --help` lists every command. After setup, `jobtracker`
(inside the project's virtual environment) is the same tool.

## Troubleshooting

| Problem | What to do |
|---|---|
| Not sure what is wrong | `python scripts/jt.py doctor` lists each check with a fix. |
| "The workspace is not initialized" | Run `/setup`. |
| A job site says a tool is missing | Run a search again: the agent installs it (`python scripts/jt.py providers install --enabled`). |
| A job site was skipped as "blocked" | The site refused automated access for a while; the other sites still ran. Try again later. |
| The resume "could not be read" | It is probably a scanned image. Provide a text-based PDF or a DOCX, or let the agent read it visually and confirm the text with you. |
| Spanish commands do not appear | Restart Claude Code in the project folder; if they are still missing, run `python scripts/jt.py skills sync`. |
| A commit is blocked by the privacy guard | The message names the file. Personal data belongs in `user-data/`; remove it from the commit. |
| The privacy guard says "no working Python 3.11+ found" | On Windows, `python` may be only the Microsoft Store's alias. Run `/setup`: it installs Python (with winget, not the Store) and creates the project's `.venv`, which the guard uses first. `python scripts/jt.py doctor` shows the `privacy_guard_python` check. |
| "schema … is newer than this code" | Update the project (`git pull`). |
| You want to start completely fresh | `/new-season` for a new campaign, or `python scripts/jt.py reset --confirm RESET` to move everything to `user-data/archive/` and start empty. |

## Contributing

Contributions are welcome: new job sites, fixes, translations, and features.
Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) (setup, the spec-driven
workflow, privacy rules, and the checks every pull request passes). Adding a
job site has its own guide in
[`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md).

## License

GPL-3.0. See [`LICENSE`](LICENSE).

---

# Español

Asistente local de búsqueda de empleo manejado por un agente de IA, hecho para
[Claude Code](https://claude.com/claude-code). Clonas el repositorio, abres
Claude Code y el agente lo configura contigo.

- El **agente** arma tu perfil a partir de tu CV y un cuestionario corto, busca
  en portales de empleo, puntúa cada aviso según tu perfil, investiga salarios
  con evidencia y redacta CV adaptados, cartas de presentación y respuestas de
  formularios.
- Un **panel web local** (en español o inglés) muestra la última búsqueda,
  sigue cada postulación y su estado, y te deja registrar lo que pasó de verdad.
- Un **ciclo de aprendizaje** usa tus resultados reales para ajustar las
  búsquedas, los puntajes y los consejos.

Todo lo personal se queda en tu computadora, en una sola carpeta que git ignora.

## Estado

Todo funciona hoy: configuración, búsqueda en siete fuentes con puntaje y
evidencia salarial, seguimiento de postulaciones, documentos y formularios,
aprendizaje, temporadas, el panel con sus cuatro pestañas y la posibilidad de
agregar tus propios portales.

## Requisitos

- Python 3.11 o superior
- [Claude Code](https://claude.com/claude-code)
- Git

No tienes que instalar nada a mano: la configuración instala los paquetes en
una carpeta `.venv` del proyecto, y antes de buscar el agente instala lo que
necesite un portal que activaste (por ejemplo Scrapling, unos 150 MB) y te
avisa.

## Inicio rápido

```
git clone <este repositorio>
cd agentic-job-search-and-track
claude
```

Dentro de Claude Code escribe `/setup`, o simplemente "configura el proyecto".
Lo primero que pregunta el agente es el idioma. Si eliges español, el resto de
la configuración es en español y se instalan los nombres de comandos en
español (aparecen la próxima vez que abras Claude Code en la carpeta). Puedes
interrumpir cuando quieras: al volver a ejecutarlo continúa donde quedaste.

## Cómo pedirle cosas al agente

Escribe un comando o simplemente pídelo con tus palabras, en español o inglés:
el agente carga el comando correcto y solo te pregunta lo que falte.

| Comando | En inglés | Qué hace | También puedes decir |
|---|---|---|---|
| `/configurar` | `/setup` | Primera vez, y cambios a tu perfil, títulos, portales o reglas | "cambia mis títulos", "activa Get on Board" |
| `/buscar-empleos dias=7` | `/job-search days=7` | Busca en los portales que activaste y actualiza el panel | "busca trabajo de esta semana", "¿hay avisos nuevos?" |
| `/preparar-documentos pendientes` | `/prepare-documents pending` | CV, cartas y respuestas de formulario que falten (o `ids=J0007,J0012`, o `todas`) | "completa los documentos faltantes de la J0007" |
| `/formulario ids=J0007` | `/form-answers ids=J0007` | Respuestas del formulario de un aviso (`alternativa` para otra versión) | "responde el formulario de la J0007" |
| `/analizar-resultados` | `/analyze-results` | Revisa tus resultados y propone lecciones | "¿cómo me está yendo?", "¿por qué no me llaman?" |
| `/nueva-temporada` | `/new-season` | Empieza de nuevo con un perfil nuevo o actualizado; lo anterior queda consultable | "volví a buscar trabajo, empecemos de nuevo" |
| `/agregar-proveedor` | `/add-provider` | Agrega un portal que el proyecto aún no cubre | "agrega Computrabajo como portal" |
| `/panel` | `/panel` | Inicia o detiene el panel local | "abre el panel" |

Los nombres en inglés funcionan siempre. También puedes darle reglas con tus
palabras, como "no me muestres consultoras de outsourcing" o "nunca cambies el
diseño de mi CV": las guarda y las respeta desde entonces.

## Portales de empleo

Cada portal empieza **apagado**: eliges cuáles usar en `/configurar` o en el
panel, así una actualización nunca empieza a buscar en un portal nuevo por su
cuenta. Los portales *globales* sirven a muchos países; uno *local* solo a sus
países, y la configuración te ofrece los globales más los de tu país.

| Portal | Cobertura | Cómo se lee |
|---|---|---|
| LinkedIn | global | Páginas públicas de empleos, sin iniciar sesión, nunca con tu cuenta |
| Indeed | global | Una sesión de navegador sin ventana ni cuenta; varias primeras páginas por título, porque sin sesión Indeed muestra una sola |
| Glassdoor | global, también salarios | Una sesión de navegador sin ventana ni cuenta; también lee los reportes de salario de Glassdoor como una fuente de evidencia |
| Greenhouse | global | La API pública de Greenhouse de cada empresa; las empresas se encuentran con tu búsqueda de MyGreenhouse con sesión iniciada cuando estás presente, o con una búsqueda web si no |
| Get on Board | global (sobre todo Latinoamérica y remotos) | La API pública y gratuita de Get on Board |
| Bumeran Perú | local: PE | Una sesión de navegador sin ventana ni cuenta |
| Búsqueda web (sitios de empresas) | global | El agente busca en la web las páginas de empleo de las propias empresas y recuerda las empresas que encuentra |

El archivo de cada portal en [`providers/`](providers/) dice exactamente cómo
se lee y qué nunca se hace allí. Ten en cuenta las condiciones de uso:
LinkedIn, Indeed, Glassdoor y Bumeran prohíben el acceso automatizado, así que
pueden limitar o bloquear tu conexión por un tiempo (nunca se usa una cuenta
tuya). Las API de Greenhouse y Get on Board son públicas; Get on Board pide
mostrar sus avisos con su fuente y un enlace, y el panel lo hace.

### Agregar tu propio portal

Ejecuta `/agregar-proveedor` (o di "agrega <portal> como portal de empleo"). El
agente estudia el sitio contigo, crea el proveedor en tu carpeta privada
(`user-data/providers/`), lo prueba con una búsqueda real en cada país que
cubre y lo activa solo para ti. Cuando funciona, te ofrece aportarlo al
proyecto como pull request, solo si dices que sí y sin datos personales. Las
reglas están en [`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md).

## Qué hace y qué no hace el agente

- Nunca postula por ti, ni envía mensajes, ni cambia nada en tus cuentas de los
  portales. Él prepara; tú postulas.
- Nunca inventa datos. Solo sugiere un salario cuando hay al menos dos fuentes
  comparables con enlace; si no, verás "sin datos confiables". Los CV y las
  respuestas nunca afirman experiencia que no tienes.
- No cambia el diseño de tu CV sin tu consentimiento.
- Escribe los documentos en el idioma de cada aviso, sin importar el idioma del
  panel, a partir de tu propio CV en ese idioma.
- Las lecciones que aprende de tus resultados solo se aplican cuando las
  apruebas.

## Tus datos y tu privacidad

- Todo lo personal (CV, perfil, postulaciones, documentos, base de datos, tus
  propios portales) se guarda en `user-data/`, dentro de la carpeta del
  proyecto. Git ignora esa carpeta.
- Una protección impide cualquier commit que incluya archivos de esa carpeta,
  archivos de CV o de base de datos, o tu nombre, correo o teléfono.
- El panel solo se sirve en tu propia computadora (`127.0.0.1`).
- Para respaldar tus datos, copia `user-data/` o pide una exportación. Para
  guardarlos en otro lugar, define la variable de entorno `JOBTRACKER_HOME`
  antes de configurar.
- La herramienta no borra nada. Un reinicio completo mueve tus datos a
  `user-data/archive/`.

## Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| No sabes qué falla | `python scripts/jt.py doctor` lista cada revisión con su solución. |
| "The workspace is not initialized" | Ejecuta `/configurar`. |
| Un portal dice que le falta una herramienta | Vuelve a buscar: el agente la instala (`python scripts/jt.py providers install --enabled`). |
| Un portal quedó "bloqueado" | El sitio rechazó el acceso automatizado por un rato; los demás portales sí se buscaron. Intenta más tarde. |
| El CV "no se pudo leer" | Probablemente es una imagen escaneada. Usa un PDF con texto o un DOCX, o deja que el agente lo lea visualmente y confirma el texto. |
| No aparecen los comandos en español | Reinicia Claude Code en la carpeta del proyecto; si siguen sin aparecer, ejecuta `python scripts/jt.py skills sync`. |
| La protección de privacidad bloquea un commit | El mensaje indica el archivo. Los datos personales van en `user-data/`; quítalos del commit. |
| La protección de privacidad dice "no working Python 3.11+ found" | En Windows, `python` puede ser solo el alias de la Microsoft Store. Ejecuta `/configurar`: instala Python (con winget, no desde la Store) y crea el `.venv` del proyecto, que la protección usa primero. `python scripts/jt.py doctor` muestra la revisión `privacy_guard_python`. |
| Quieres empezar de cero | `/nueva-temporada` para una campaña nueva, o `python scripts/jt.py reset --confirm RESET` para mover todo a `user-data/archive/` y empezar vacío. |

## Contribuir

Las contribuciones son bienvenidas: portales nuevos, correcciones,
traducciones y funciones. Empieza por [`CONTRIBUTING.md`](CONTRIBUTING.md) (en
inglés: preparación, el flujo basado en especificaciones, las reglas de
privacidad y las revisiones de cada pull request). Agregar un portal tiene su
propia guía en [`providers/CONTRIBUTING.md`](providers/CONTRIBUTING.md).
