# Job-needs questionnaire

Ask in the user's language, in the groups below. Confirm what the resume
already shows instead of asking again. Any question may be skipped: leave that
field out of what you send and move on. Never fill in a value the user did not
give. Store free-text answers as the user said them.

## Group A: how and where

| # | Question (en) | Pregunta (es) | Field | Allowed values |
|---|---|---|---|---|
| A1 | Which work modes do you accept? You can pick several. | ¿Qué modalidades aceptas? Puedes elegir varias. | `work_modes` | `remote`, `hybrid`, `onsite` |
| A2 | Which contract types? You can pick several. | ¿Qué tipos de contrato? Puedes elegir varios. | `contract_types` | `full-time`, `part-time`, `contractor` |
| A3 | Which country are you based in for work purposes? | ¿En qué país trabajas o buscas trabajo? | `country` | ISO 3166 two-letter code (`PE`, `MX`, `US`…) |
| A4 | (only if hybrid or onsite) Which cities or districts can you commute to? | (solo si híbrido o presencial) ¿A qué ciudades o distritos puedes ir? | `locations` | list of names as the user writes them |
| A5 | (only if remote) Remote for companies in your country only, in your region, or anywhere? | (solo si remoto) ¿Remoto solo para empresas de tu país, de tu región o de cualquier lugar? | `remote_scope` | `country`, `region`, `worldwide` |
| A6 | (only if A5 is region) Which region? | (solo si A5 es región) ¿Qué región? | `remote_region` | name as the user says it (`Latin America`) |

## Group B: level and money

| # | Question (en) | Pregunta (es) | Field | Allowed values |
|---|---|---|---|---|
| B1 | Which seniority are you aiming for? | ¿Qué nivel de seniority buscas? | `seniority` | free text (`Senior`, `Lead`, `Mid`…) |
| B2 | Is there a minimum monthly salary below which you would not apply? In which currency, and gross or net? (optional) | ¿Hay un salario mensual mínimo por debajo del cual no postularías? ¿En qué moneda, y bruto o neto? (opcional) | `minimum_salary` | `{"amount": 11000, "currency": "PEN", "basis": "gross"}` or `null` |
| B3 | Which languages can you work in, and at what level? | ¿En qué idiomas puedes trabajar y con qué nivel? | `languages` | `[{"language": "es", "level": "native"}, {"language": "en", "level": "B2"}]` |

Notes: `amount` is a whole number per month. If the user gives a yearly figure,
divide by 12 and confirm the monthly number with them. `currency` is an ISO
4217 code. The period is always monthly.

## Group C: preferences and constraints

| # | Question (en) | Pregunta (es) | Field | Allowed values |
|---|---|---|---|---|
| C1 | Any industries you prefer? Any you want to avoid? | ¿Rubros que prefieres? ¿Alguno que quieras evitar? | `industries_preferred`, `industries_avoided` | lists of names |
| C2 | Any companies you do not want to see (current employer, past ones)? | ¿Empresas que no quieres ver (tu empleador actual, anteriores)? | `companies_excluded` | list of names |
| C3 | When could you start? | ¿Cuándo podrías empezar? | `availability` | free text |
| C4 | (only if A5 is region or worldwide) Anything about work authorization employers should know, such as needing sponsorship or only being able to work as a contractor abroad? | (solo si A5 es región o cualquier lugar) ¿Algo sobre permisos de trabajo que un empleador deba saber, como necesitar patrocinio o poder trabajar solo como contratista para el exterior? | `work_authorization` | free text |
| C5 | By default searches look at postings from the last 7 days. Keep that? | Por defecto se buscan avisos de los últimos 7 días. ¿Lo dejamos así? | `posting_age_days` | whole number, 1–90 |

Company names in `companies_excluded` are personal data when they reveal the
user's employer: they are stored only through the command below.

One more field is filled from the resume step, not from a question:

| Field | Content |
|---|---|
| `additional_facts` | Things the user confirmed about themselves that are not on the resume, one short sentence each, without their name (`"Knows Kafka from personal projects"`). Documents may rely on these. |

## Storing the answers

Send all fields in one call, as JSON on standard input. Include only fields
you have answers for. A field you leave out keeps its current value, so to
clear an earlier answer send it explicitly as `null` (or `[]` for a list).
`titles` is handled in the next step.

```
python scripts/jt.py profile set - <<'JSON'
{
  "work_modes": ["remote", "hybrid"],
  "contract_types": ["full-time", "contractor"],
  "country": "PE",
  "locations": ["San Isidro", "Miraflores"],
  "remote_scope": "region",
  "remote_region": "Latin America",
  "seniority": "Senior",
  "minimum_salary": {"amount": 11000, "currency": "PEN", "basis": "gross"},
  "languages": [{"language": "es", "level": "native"}, {"language": "en", "level": "B2"}],
  "industries_avoided": ["gambling"],
  "posting_age_days": 7,
  "additional_facts": ["Knows Kafka from personal projects"]
}
JSON
```

On PowerShell use a here-string piped to the command instead of a heredoc.

An `invalid_profile` error names the field and the allowed values: correct it
and send again. Every change to the profile creates a new profile version;
that is expected, and it is why answers are sent together rather than one at
a time.

Answers that do not fit a field (for example "only companies with a 4-day
week", "no startups under 20 people") are not lost: record them as rules in
the Preferences step.

## Confirming

The command's output is the stored profile. Present those values to the user
as a short list in their language and ask if anything should change before
moving on.
