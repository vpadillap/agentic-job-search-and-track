# Translating a resume into another language

Use this when the user will apply in a language they have no resume in, at
setup or later (for example when a search turns up postings in a new
language). Always offer first; never translate without the user's yes.

## 1. Choose the source

Ask which of their resumes to translate from (usually the one closest to the
target market). It must be a DOCX to keep its design; a PDF can only be
translated as text (a design change, which needs their consent).

## 2. Write the draft

Read the source text (`jt resume show` → `by_language` → `text_path`) and
translate it paragraph by paragraph. Send one replacement per paragraph that
changes:

```
jt resume translate --from en --to pt <inbox file or ->
```

with `{"edits": [{"find": "<original paragraph text>", "replace": "<translation>"}]}`.
Each `find` must match one paragraph exactly; edits apply all or nothing. The
draft is written as `profile/resume-draft-<to>-v<N>.docx` with the same
design; the user's resumes are not touched.

Rules while translating:

- Faithful, no tailoring, nothing added or removed.
- Employer names, product names, and certifications stay as they are.
- Job titles: keep the original when it is the usual term in that market;
  otherwise translate it. Do not infer the user's gender from their name: if
  the language needs a gendered form, ask them.
- Translate section headings.

Check `layout.same_shape` in the result; a longer language can change the
length, which is fine.

## 3. Review and confirm

Give the user the draft's path and ask them to open it in Word, correct
anything, save it, and tell you when it is ready. Only then:

```
jt resume import "<draft path>" --language pt --translated-from en
```

Read the extracted text back and confirm it with them, as for any resume.
Until it is imported, postings in that language cannot be scored or tailored.
