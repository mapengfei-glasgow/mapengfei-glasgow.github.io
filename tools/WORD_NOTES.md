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

Run `python3 tools/build_word_notes.py && hugo --minify` in an automated publishing
pipeline on the Qwen machine. GitHub Pages builds only read the committed cache;
they do not need access to Qwen. Generation failures exit nonzero and preserve
completed notes, so rerunning resumes the work. Missing definitions display
“Definition not generated yet.” They never trigger a browser request to Qwen.

Only mark public article content: the generation command sends marked paragraphs
to the configured endpoint. Vocabulary notes from published pages are included
in a public JSON asset; do not use markers for confidential content.
