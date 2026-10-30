# Vocabulary previews with Qwen

In an article's Markdown body, mark a word or phrase:

```text
The [[Ottoman Empire]] is collapsing.
She is an [[aspiring]] writer.
```

The site shows highlighted terms. Hover, focus with the keyboard, or tap to read
pronunciation, part of speech, Chinese meaning, a simple English explanation,
and the original paragraph. Escape or clicking outside dismisses the preview.
Code blocks and inline code are not intended as vocabulary input.

## Episodes (`content/episodes/`)

An episode page has **no Markdown body**: its transcript lives in the front
matter as `sentences`, so the marker goes inside a sentence's `text` value:

```yaml
sentences:
  - {text: "[[Curfews]] have been in place in several French cities.", start: 0.0, end: 8.2, explain: "…", zh: "…"}
  - {text: "and [[looting]] that rocked the country over the weekend.", start: 8.2, end: 11.0}
```

The marker **replaces the word on screen**, so it has to match the sentence
character for character — `[[Curfews]]` where the sentence says "Curfews",
`[[looting]]` where it says "looting". `[[curfew]]` would silently rewrite the
sentence to "curfew". Quote marks and brackets are fine inside the value; only
`[[…]]` is special.

Only the sentence text is highlighted: indices, the 💡 A2 note and the 🀄 Chinese
note of the same sentence are left alone, and the sentence-in-the-notebook (☆)
stores the plain words, not the markers.

## Marking terms in the editable copy

`content/edit/<name>.md` is a plain-text copy of one transcript: one sentence
per line, so line N is sentence N. It is the comfortable place to add `[[…]]`
marks, but the site renders the copy in `content/episodes/<slug>.md`, so the
marks have to be written back before the page can show them:

```sh
python3 tools/apply_transcript.py --dry-run   # show the per-line diff first
python3 tools/apply_transcript.py             # write it back
python3 tools/build_word_notes.py --dry-run   # then see which terms need notes
python3 tools/build_word_notes.py             # generate them
```

`apply_transcript.py` replaces only each sentence's `text`. The `start`, `end`,
`explain` and `zh` fields are left alone, so timestamps and notes stay aligned.
It refuses to run when the copy's line count no longer matches the page's
sentence count — past the first difference every line would be written into the
wrong sentence — and it is a no-op when nothing changed.

The copy names its page in the front matter:

```yaml
original: "episodes/2026-09-15-why-science-needs-storytellers.md"
```

## On the machine running Qwen

From the root of this repository, using Python 3.9 or newer:

```sh
# Preview pending terms without calling the model.
python3 tools/build_word_notes.py --dry-run

# Generate with the existing local Qwen service.
python3 tools/build_word_notes.py \
  --endpoint http://127.0.0.1:30000/v1/chat/completions \
  --model Qwen3.8-27B-FP8

# Build / preview after generating.
hugo server
```

Use the actual model name served by your Qwen installation if different.
If the service requires authentication, set `WORD_NOTES_API_KEY` in the shell
before running the script. The key is never written into the website.
`WORD_NOTES_ENDPOINT` and `WORD_NOTES_MODEL` can also set the defaults.

The command saves definitions in `data/word_notes.json`. Review generated
meanings and IPA there; you may correct them directly. Unchanged terms and
contexts are skipped on subsequent runs, preserving corrections. Changed
paragraphs regenerate their definitions. A term has a separate definition per
article; if used with multiple meanings within one article, its first marked
paragraph supplies the meaning for that article.

After generation, commit the article and cache, and publish normally:

```sh
git add content/ data/word_notes.json
git commit -m "Add marked vocabulary and generated definitions"
git push
```

## Doing it without thinking about it

Marking a word is an ordinary content edit: you add `[[term]]`, commit, push.
The definition cannot ride along, though — it has to be generated where the model
lives — so `tools/daily_bbc_pipeline.sh` (the `bbc-daily.timer` unit) runs
`build_word_notes.py` as its **stage 3b** and commits `data/word_notes.json`.

It is checked on *every* run, not only when an episode was published, because
marks are added to old pages too. It is also cheap when idle: the pending check
is a `--dry-run`, which needs no model, so nothing is started unless a term is
actually waiting. A run with `SKIP_NOTES=1` skips this stage as well.

**Which model.** The stage defaults to Ollama's `qwen3:30b-a3b`
(`http://127.0.0.1:11434/v1/chat/completions`), not the sglang server the A2
notes use: on 2026-10-21 sglang-qwen could not start at all — a partly occupied
GPU left the mamba state cache at `max_num_reqs=0` — and word notes must not
depend on that. Ollama needs no key and stays up on its own, so the stage never
has to start (or leak) an inference server. Set `WORD_NOTES_ENDPOINT` /
`WORD_NOTES_MODEL` to switch back to `http://127.0.0.1:30000/v1/chat/completions`
and `Qwen3.8-27B-FP8` once sglang is healthy.

The cost is up to one timer interval. To make a mark take effect immediately,
run the builder before pushing:

```sh
python3 tools/build_word_notes.py
git add content/ data/word_notes.json
git commit -m "Add marked vocabulary and generated definitions"
git push
```

A mark pushed without its definition is not broken: the page builds, the word is
still hoverable, and the preview says “Definition not generated yet.” until the
definition lands — nothing in the browser ever calls the model.

GitHub Pages builds only read the committed cache; they do not need access to Qwen. Generation failures exit nonzero and preserve
completed notes, so rerunning resumes the work. Missing definitions display
“Definition not generated yet.” They never trigger a browser request to Qwen.

Only mark public article content: the generation command sends marked paragraphs
to the configured endpoint. Vocabulary notes from published pages are included
in a public JSON asset; do not use markers for confidential content.
