# Claude Job Tracker

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

The project is being built in stages. What works today:

| Area | State |
|---|---|
| First-run setup (`/setup`): requirements, language, resume, questionnaire, target titles, preferences | Works |
| Private workspace, database, `jobtracker` command-line interface, privacy guard | Works |
| Panel: Search tab (results, filters, score and salary detail, track and dismiss; work mode with how the posting describes it, which you can correct) | Works |
| Job search (`/job-search`), scoring, salary evidence, job-site recipe format | Works; job sites: LinkedIn (read logged out). Each new site arrives with its own update, switched off |
| Applications tab, statuses, uploads | Works |
| Tailored resumes, cover letters, form answers (`/prepare-documents`, `/form-answers`) | Works |
| Learning: insights, lessons, predictions, recommendations (`/analyze-results`) | Planned |
| Seasons and resets (`/new-season`), Profile & agent tab, `/panel` | Planned |

The specification of every planned stage is in
[`openspec/changes/`](openspec/changes/).

## Requirements

- Python 3.11 or newer
- [Claude Code](https://claude.com/claude-code)
- Git

Nothing else needs to be installed by hand; setup installs the Python packages
into a `.venv` folder inside the project after asking you.

## Quick start

```
git clone <this repository>
cd claude-job-tracker
claude
```

Then, inside Claude Code:

```
/setup
```

The agent will:

1. Check your environment and install what is missing (it asks first).
2. Ask whether you want the panel in English or Spanish.
3. Create your private workspace.
4. Ask in which languages you will apply, and for your resume (PDF or DOCX)
   in each one; for a language you have none in, it offers to translate one of
   yours as a draft you review. Each resume is used for postings in its
   language.
5. Ask about the job you want: remote/hybrid/onsite, contract type, location,
   minimum salary, languages, and so on. Every question can be skipped.
6. Ask which job titles you want, look at how the market names similar roles,
   and propose alternates for you to include or exclude.
7. Record your standing preferences (for example: never change my resume's
   layout).
8. Give you a short tour.

You can stop at any time; running `/setup` again continues where you left off.
Run it again later to change any answer.

## Commands

You talk to the agent with these commands in Claude Code. Spanish users get
Spanish command names as well (see the Spanish section).

| Command | What it does | State |
|---|---|---|
| `/setup` | First run, and later changes to your profile | Works |
| `/job-search days=7` | Searches the enabled job sites and updates the panel | Works (LinkedIn) |
| `/prepare-documents pending` | Tailored resumes, cover letters, and form answers for tracked jobs that lack them (or `ids=J0007,J0012`) | Works |
| `/form-answers ids=J0007` | Answers to a posting's application form | Works |
| `/analyze-results` | Reviews your results and proposes adjustments | Planned |
| `/new-season` | Starts over with a new or updated profile; archives the previous campaign | Planned |
| `/panel` | Starts or stops the local panel | Planned |

You can also just tell the agent things in plain language, such as "don't show
me outsourcing consultancies" or "never change my resume layout". It stores
them as rules and follows them from then on.

## What the agent will and will not do

- It never applies to a job, sends a message, or changes anything in your
  accounts on job sites. It prepares; you apply.
- It never invents facts. A salary is suggested only when at least two
  comparable, linked sources support it; otherwise you see "no reliable data".
  Resumes and form answers never claim experience you do not have.
- It does not change your resume's layout without your consent.
- It writes documents in the language of each job posting, whatever language
  the panel is in, starting from your own resume in that language. If you have
  no resume in a language, it asks you for one or offers to translate one of
  yours as a draft you review in Word first.
- Lessons it learns from your results take effect only after you approve them.

## Your data and privacy

- Everything personal (resume, profile, applications, documents, database) is
  stored in `user-data/` inside the project folder. Git ignores that folder.
- A pre-commit guard refuses any commit that contains files from that folder,
  resume or database files, or your name, email, or phone number.
- The panel is served only on your own computer (`127.0.0.1`).
- To back up your data, copy `user-data/`. To keep it somewhere else, set the
  `JOBTRACKER_HOME` environment variable to another folder before running
  setup.
- Nothing is deleted by the tool. A reset moves your data into
  `user-data/archive/`.
- How each job site is read is defined per site. Every site starts switched
  off: you choose which ones to use in `/setup` or in the Search tab, so an
  update never starts searching a new site on its own. Be aware of each
  site's terms of use; for example, LinkedIn is read logged out, never with
  your account, but its terms forbid automated access and it may throttle
  your connection for a while.

The exact layout of the private folder is documented in
[`docs/workspace-layout.md`](docs/workspace-layout.md).

## The command-line interface

The agent does all its reading and writing through one tool, which you can use
too. It prints JSON.

```
python scripts/jt.py doctor          # check the environment; changes nothing
python scripts/jt.py context         # profile, rules, and state the agent works from
python scripts/jt.py profile show    # your job needs and target titles
python scripts/jt.py rules list      # the rules the agent follows
python scripts/jt.py paths           # where everything is stored
python scripts/jt.py setup status    # which setup steps are done
```

To try the panel with invented data, point `JOBTRACKER_HOME` at an empty
folder, then run `jt.py demo seed` and `jt.py panel` (and `jt.py demo clear`
to remove it). The demo refuses to mix with real search results.

`python scripts/jt.py --help` lists every command. After setup, `jobtracker`
(inside the project's virtual environment) is the same tool.

## Troubleshooting

| Problem | What to do |
|---|---|
| Not sure what is wrong | `python scripts/jt.py doctor` lists each check with a fix. |
| "The workspace is not initialized" | Run `/setup`. |
| The resume "could not be read" | It is probably a scanned image. Provide a text-based PDF or a DOCX, or let the agent read it visually and confirm the text with you. |
| Spanish commands do not appear | Restart Claude Code in the project folder; if they are still missing, run `python scripts/jt.py skills sync`. |
| A commit is blocked by the privacy guard | The message names the file. Personal data belongs in `user-data/`; remove it from the commit. |
| "schema … is newer than this code" | Update the project (`git pull`). |
| You want to start completely fresh | `python scripts/jt.py reset --confirm RESET` moves everything to `user-data/archive/` and starts empty. |

## Contributing

Development is spec-driven with [OpenSpec](https://github.com/Fission-AI/OpenSpec);
see [`AGENTS.md`](AGENTS.md) for the rules and the repository map.

```
git config core.hooksPath .githooks     # enable the privacy guard
uv sync --extra dev                     # or: pip install -e ".[dev]" in a virtual environment
uv run ruff check . && uv run pytest
```

Never use real personal data in code, tests, specs, or commits. Tests use the
fictional persona in `tests/fixtures/`.

## License

GPL-3.0. See [`LICENSE`](LICENSE).

---

# Español

Asistente local de búsqueda de empleo manejado por un agente de IA, hecho para
[Claude Code](https://claude.com/claude-code). Clonas el repositorio, ejecutas
un comando y el agente lo configura para ti.

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

El proyecto se construye por etapas. Hoy funciona la configuración inicial
(`/configurar`), el espacio de trabajo privado, la interfaz de línea de
comandos, la protección de privacidad, las pestañas Búsqueda y Postulaciones
del panel (estados, etiquetas, CV enviado, historial; la modalidad con el detalle
que da el aviso, que puedes corregir) y la búsqueda
(`/buscar-empleos`) con puntaje y evidencia salarial. El primer portal es
LinkedIn (leído sin iniciar sesión); cada portal nuevo llega con su propia
actualización, apagado hasta que lo actives. Los documentos y el
aprendizaje están especificados en
[`openspec/changes/`](openspec/changes/) y en desarrollo.

## Requisitos

- Python 3.11 o superior
- [Claude Code](https://claude.com/claude-code)
- Git

## Inicio rápido

```
git clone <este repositorio>
cd claude-job-tracker
claude
```

Dentro de Claude Code:

```
/setup
```

Lo primero que pregunta el agente es el idioma. Si eliges español, el resto de
la configuración es en español y se instalan los nombres de comandos en
español (aparecen la próxima vez que abras Claude Code en la carpeta). Puedes
interrumpir cuando quieras: al volver a ejecutar el comando continúa donde
quedaste.

## Comandos

| Comando | En inglés | Qué hace | Estado |
|---|---|---|---|
| `/configurar` | `/setup` | Primera vez, y cambios posteriores a tu perfil | Funciona |
| `/buscar-empleos dias=7` | `/job-search days=7` | Busca en los proveedores activos y actualiza el panel | Funciona (LinkedIn) |
| `/preparar-documentos pendientes` | `/prepare-documents pending` | CV, cartas y respuestas de formulario que falten en las vacantes en seguimiento (o `ids=J0007,J0012`) | Funciona |
| `/formulario ids=J0007` | `/form-answers ids=J0007` | Respuestas del formulario de una vacante | Funciona |
| `/analizar-resultados` | `/analyze-results` | Revisa tus resultados y propone ajustes | Planificado |
| `/nueva-temporada` | `/new-season` | Empieza de nuevo con un perfil nuevo o actualizado; archiva lo anterior | Planificado |
| `/panel` | `/panel` | Inicia o detiene el panel local | Planificado |

Los nombres en inglés funcionan siempre. Un comando en español solo se instala
cuando su versión en inglés ya existe.

También puedes decirle cosas al agente en lenguaje natural, como "no me
muestres consultoras de outsourcing" o "nunca cambies el diseño de mi CV". Las
guarda como reglas y las respeta desde entonces.

## Qué hace y qué no hace el agente

- Nunca postula por ti, ni envía mensajes, ni cambia nada en tus cuentas de los
  portales. Él prepara; tú postulas.
- Nunca inventa datos. Solo sugiere un salario cuando hay al menos dos fuentes
  comparables con enlace; si no, verás "sin datos confiables". Los CV y las
  respuestas nunca afirman experiencia que no tienes.
- No cambia el diseño de tu CV sin tu consentimiento.
- Escribe los documentos en el idioma de cada aviso, sin importar el idioma del
   panel, a partir de tu propio CV en ese idioma. Si no tienes CV en un idioma,
  te lo pide o te ofrece traducir uno tuyo como borrador que revisas en Word.
- Las lecciones que aprende de tus resultados solo se aplican cuando las
  apruebas.

## Tus datos y tu privacidad

- Todo lo personal (CV, perfil, postulaciones, documentos, base de datos) se
  guarda en `user-data/`, dentro de la carpeta del proyecto. Git ignora esa
  carpeta.
- Una protección impide cualquier commit que incluya archivos de esa carpeta,
  archivos de CV o de base de datos, o tu nombre, correo o teléfono.
- El panel solo se sirve en tu propia computadora (`127.0.0.1`).
- Para respaldar tus datos, copia `user-data/`. Para guardarlos en otro lugar,
  define la variable de entorno `JOBTRACKER_HOME` antes de configurar.
- La herramienta no borra nada. Un reinicio mueve tus datos a
  `user-data/archive/`.
- Cada portal de empleo empieza apagado: eliges cuáles usar en `/configurar`
  o en la pestaña Búsqueda. LinkedIn se lee sin iniciar sesión, nunca con tu
  cuenta, pero sus condiciones prohíben el acceso automatizado y puede limitar
  tu conexión por un tiempo.

## Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| No sabes qué falla | `python scripts/jt.py doctor` lista cada revisión con su solución. |
| "The workspace is not initialized" | Ejecuta `/setup`. |
| El CV "no se pudo leer" | Probablemente es una imagen escaneada. Usa un PDF con texto o un DOCX, o deja que el agente lo lea visualmente y confirma el texto. |
| No aparecen los comandos en español | Reinicia Claude Code en la carpeta del proyecto; si siguen sin aparecer, ejecuta `python scripts/jt.py skills sync`. |
| La protección de privacidad bloquea un commit | El mensaje indica el archivo. Los datos personales van en `user-data/`; quítalos del commit. |
| Quieres empezar completamente de cero | `python scripts/jt.py reset --confirm RESET` mueve todo a `user-data/archive/` y empieza vacío. |
