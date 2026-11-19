---
name: formulario
description: "Propone respuestas para el formulario de postulación de vacantes en seguimiento, solo con lo que respaldan el CV y el perfil, en el idioma del aviso. Úsalo cuando el usuario pide solo las respuestas del formulario u otra versión, por ejemplo “responde el formulario de la J0007”, “qué pongo en el formulario de la J0009?”, “dame otra alternativa de respuestas”. Argumentos: ids=J0007 (obligatorio), alternativa. Nunca llena ni envía un formulario. (Alias en español de /form-answers.)"
---

# /formulario

This is the Spanish name of the `/form-answers` command. It has no procedure of
its own.

1. Read `.claude/skills/form-answers/SKILL.md` and follow it exactly, including
   the reference files it mentions (they are in `.claude/skills/form-answers/`).
2. Treat the arguments given to this command as the arguments of
   `/form-answers`. Spanish argument names: `alternativa` means `alternative`.
3. Talk to the user in Spanish, unless they write to you in another language.
