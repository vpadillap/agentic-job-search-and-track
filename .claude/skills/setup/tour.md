# Guided tour

Give this tour at the end of setup, in the user's language, in your own words.
Keep it to what is below; it should take about two minutes to read. Use the
command names exactly as `jt context` → `commands` gives them: those are the
names that work, or will work, in this user's installation. Say which are
usable now (`available: true`) and which are coming.

## What to cover

### 1. How this works

- You talk to the agent here, in Claude Code, by running commands. The agent
  searches, scores, researches salaries, and drafts documents.
- The panel is a local web page (only on this computer) where the results
  appear and where you record what happened. The panel never runs the agent:
  it shows the command to paste here.
- The agent never applies to a job for you. It prepares; you apply.

### 2. The panel tabs

| Tab | What it is for |
|---|---|
| Search | The postings found by the latest search, each with an alignment score, why it got that score, a suggested monthly salary with its sources (or "no reliable data"), and buttons to track it or dismiss it with a reason. |
| Applications | Every posting you decided to follow: status, tailored resume, cover letter, form answers, the date you applied, the salary you asked for, your notes. Closed negative ones are hidden by default. |
| Learning | What your real results show: which scores, titles, channels, and resume versions lead to interviews, and the lessons the agent proposes from them. You approve or ignore each lesson. |
| Profile & agent | Your profile, what the agent remembers about your preferences, what is pending for it, the list of commands, and the job sites in use. |

(es: Búsqueda, Postulaciones, Aprendizaje, Perfil y agente.)

If the panel interface is not ready in this version, say so and describe the
tabs as what is coming.

### 3. The commands

Go through the `commands` list: name, one-line description, and an example.
Group them as: usable now / coming.

### 4. Your data

- Everything personal (resume, profile, applications, documents) is in one
  folder: give the user the path from `jt context` → `home` (by default
  `user-data/` inside this project). Git ignores it, and a guard blocks any
  commit containing your name, email, or phone.
- To back it up, copy that folder. To keep it somewhere else, set the
  `JOBTRACKER_HOME` environment variable.
- Nothing is ever deleted by the tool; a reset moves the old data to an
  archive folder.

### 5. It learns from what you record

The more outcomes you record (applied, interview, rejected, no answer), the
better the advice gets: first plain statistics, later predictions of which
postings are worth your time, and recommendations. It only uses your own data,
and it tells you how much evidence is behind each claim.

### 6. Changing things later

- Preferences: just tell the agent ("never change my resume layout", "skip
  consulting firms"). It stores them as rules you can see in the panel.
- Profile answers, titles, or resume: run the setup command again.

### 7. Next step

One sentence: the next command to run (see step 10 of the setup skill).

## Tone

Plain and brief. No feature list beyond the above, no promises about results.
