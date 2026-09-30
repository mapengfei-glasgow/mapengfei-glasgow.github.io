# English Listening

Podcast audio is transcribed and **timestamped sentence by sentence**, so tapping
any sentence jumps playback to that exact moment. The episode audio stays loaded
in a persistent bottom player bar, and navigating between pages never interrupts it —
built for close listening and shadowing.

Stack: Hugo + [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme + a Cloudflare Worker (files + vocabulary) + giscus (comments, backed by this repo's GitHub Discussions).

## Layout

```
content/episodes/    # one .md per episode (front matter holds every sentence + its timestamps)
data/transcripts/    # <slug>.small.json per episode (word-level timestamps)
static/audio/<slug>/ # LOCAL ONLY while building: the episode MP3 is uploaded to
                     # R2 and then removed, so the repo keeps pages only
static/css/          # main.css — styles for our own components only
assets/js/           # player.js (bottom bar + episode page wiring)
                     # vocab.js (sync code + vocabulary book)
                     # comments.js (mounts the giscus comment box)
layouts/             # index.html (home: intro + cards), episodes/single.html,
                     # words/list.html, partials/ overrides
themes/PaperMod/     # theme (git submodule)
tools/               # the pipeline (see tools/ below)
android/             # installable app: a Trusted Web Activity around the site
                     # (see android/README.md — paths, toolchain, how to build)
```

`tools/` is committed; a few large or machine-local pieces are not, and are
recreated on a new host:

```
tools/make_episode.py     # MP3 → full audio + Hugo content (sentence timestamps)
tools/bbc_podcast.py      # BBC feed downloaders (run by the systemd timers)
tools/bbc_gnp.py
tools/bbc_backfill.py     # one episode per day for a date range (backfills)
tools/bbc_publish.py      # transcribe → publish → push a batch
tools/publish_batch.py    # batch helper used by BBC publishing
tools/r2_client.py        # shared R2 signing/upload code (stdlib only)
tools/r2_upload.py        # R2 CLI (also used from make_episode.py)
tools/make_og.py          # Open Graph image for an episode
tools/flag_a2.py          # A2-level sentence flagging (uses tools/phrase_notes.tsv)
tools/qwen_explain.py     # writes the 💡 A2 notes and the 🀄 Chinese notes (local Qwen)
tools/merge_explain.py    # merge both note kinds into the sentence frontmatter
tools/phrase_notes.tsv    # set-phrase table used by the flagger
tools/daily_bbc_pipeline.sh      # the whole daily chain (systemd calls this)
tools/mihomo_bbc_route.py # point the BBC at a proxy exit that can reach it
tools/site-api/           # Cloudflare Worker behind /files/ AND the vocabulary
                          # book (sync-code auth, vocab in a private bucket)
tools/systemd/*.service|timer    # bbc-daily (+ the older bbc_gnp/bbc_iot units)
tools/test_charts.mjs     # test for the chart shortcode (see below)

tools/ecdict.csv          # NOT committed (66 MB ECDICT table); make_episode.py
                          # prints the one-line curl to fetch it
bin/                      # NOT committed: static hugo / ffmpeg binaries, uv
venv/                     # NOT committed: Python environment (faster-whisper)
static/audio/, ecdict     # NOT committed: episode MP3s live in R2
~/.r2.env                 # NOT committed: R2 credentials (chmod 600)
```

## Build one episode from an MP3

```bash
cd ~/dcgrid
HF_HOME=$PWD/.hf-cache ./venv/bin/python tools/make_episode.py \
  ~/Downloads/BBC\ Global\ News\ Podcast/2026-09-03\ xxx.mp3 \
  --show "Global News Podcast" \
  --title "Episode title" --date 2026-09-03
```

Pipeline: faster-whisper (word-level timestamps) → group words into sentences by
punctuation/pauses → ffmpeg transcodes the full episode (CBR 96k) → writes
`content/episodes/<slug>.md` (start/end per sentence) and
`static/audio/<slug>/episode.mp3` (transcription cache lands in `data/transcripts/`).
The first run downloads the Whisper model (cached in `.hf-cache/`, ~460MB, `small`).

- `--model tiny|base|small|medium|large-v3` — bigger is more accurate but slower (default `small`)
- `--slug`, `--force`, `--notes`: see `--help`

## Local preview / build

```bash
cd ~/dcgrid/english-site
../bin/hugo server -n 127.0.0.1 -p 1313      # dev preview (auto reload)
../bin/hugo --minify                          # build into public/
```

## Publishing to GitHub Pages

The site is published at <https://mapengfei-glasgow.github.io/> (user site),
from the repository `mapengfei-glasgow/mapengfei-glasgow.github.io`.

`.github/workflows/deploy.yml` runs on every push to `main`: it downloads Hugo
extended 0.165.0, checks out submodules (the PaperMod theme), runs
`hugo --minify --baseURL <Pages URL>`, and deploys `public/` with
`actions/deploy-pages`. Pages is set to **workflow** builds, so a `git push`
goes live automatically; `public/` is not committed.

> Note: the repository is the `mapengfei-glasgow.github.io` user site, served from
> the root path, and local builds use `baseURL = "/"` to match.

Publishing one episode:

```bash
cd ~/dcgrid/english-site
git add -A && git commit -m "add episode ..."
git push origin main   # remote is SSH; core.sshCommand points at the local ssh config
```

## Daily automation

One systemd **user** timer runs the whole chain — no root needed:

- `~/.config/systemd/user/bbc-daily.timer` — 18:00 daily (10:00 UTC), runs
  `tools/daily_bbc_pipeline.sh`, which does

  1. make sure the local Mihomo proxy (`mihomo.service`) is up **and that the BBC
     has a usable exit** — `tools/mihomo_bbc_route.py` re-applies a
     BBC-specific proxy group, because the subscription's auto-select group
     health-checks against Google and will happily sit on a node where every BBC
     URL returns 503. A subscription refresh overwrites `config.yaml`, so this
     runs every time rather than once,
  2. download the day's episode (`tools/bbc_backfill.py`, a rolling 3-day
     window, one episode per day),
  3. transcribe → build the page → upload to R2 → commit → push
     (`tools/bbc_publish.py`),
  4. write the 💡 English notes for the hard sentences and the 🀄 Chinese note
     for **every** sentence with the local Qwen server
     (`tools/qwen_explain.py`), merge them (`tools/merge_explain.py`), then
     commit and push again.

  Every stage is idempotent, so a failed run can be repeated with
  `systemctl --user start bbc-daily.service`.

Useful:

```bash
systemctl --user list-timers bbc-daily.timer
journalctl --user -u bbc-daily -n 50          # or work/logs/bbc-daily-*.log
systemctl --user start bbc-daily.service      # run it now
SKIP_NOTES=1 systemctl --user start bbc-daily.service   # skip the Qwen step
```

The older `bbc_gnp` / `bbc_iot` / `bbc-publish` units are superseded by
`bbc-daily`; their `ExecStart` still refers to the pre-migration host, so do not
install them as they are. To add In Our Time, copy `bbc-daily.service` and set
`Environment=SHOW=in-our-time DL_DIR=downloads/In Our Time`.

### The A2 notes and the Chinese notes

Every sentence can carry two generated notes, both written by a local Qwen
(`sglang-qwen.service`, `Qwen3.8-27B-FP8` on `127.0.0.1:30000`; the daily
pipeline starts it if it is not already running):

| field | what it is | which sentences |
|---|---|---|
| `explain` | 💡 plain-English note on the words above CEFR A2 | only the sentences `flag_a2.py` flags as containing something beyond A2 |
| `zh` | 🀄 the sentence in Simplified Chinese, followed by the Chinese meanings of the hard terms in full-width parentheses | **every** sentence |

The two differ in coverage on purpose. `explain` marks what is *hard*; `zh` is a
translation, and a translation with holes is useless — ordinary sentences like
"It's a huge deal in and of itself." are never flagged, yet a reader following
along still needs them. So `zh` is generated from the episode frontmatter
directly and covers all 11k+ sentences:

```bash
./venv/bin/python tools/qwen_explain.py --dry-run              # check the endpoint
./venv/bin/python tools/qwen_explain.py --slug <episode>       # 💡 one episode
./venv/bin/python tools/qwen_explain.py --all-sentences        # 🀄 every episode
./venv/bin/python tools/qwen_explain.py --all-sentences --slug <episode>
./venv/bin/python tools/merge_explain.py [slug]                # into frontmatter
```

Results are split by job, because they answer different questions:

```
tools/a2_chunks/results/<slug>_cNN.json   💡 explain, per flagged chunk
tools/a2_chunks/results/<slug>_zh.json    🀄 zh, one file per episode, all sentences
```

`merge_explain.py` reads both (globbing `<slug>_*.json`, so `_zh.json` sorts last
and wins for Chinese) and is additive per field: re-merging never drops a field
the results do not carry. It also leaves a file untouched when nothing changed.

On the page both notes are hidden until the sentence is playing; the **中文**
button in the bottom player bar additionally shows every Chinese note at once, so
the translation can be read before or after listening. That preference is stored
in `localStorage` like Auto-continue, and applied through `<html data-zh="on">`.

Not yet wired: the **vocabulary book** stores only `text` and `explain`, so a
saved sentence shows its English note but not its 🀄 Chinese one. The storage is
ours now (`tools/site-api/worker.js`, a JSON document in a private R2 bucket), so
this is a small change on both sides whenever it is wanted: keep `zh` in
`cleanItem()` and render it in `assets/js/vocab.js`.

The daily pipeline only annotates the episodes **it published in that run**, so
the timer can never quietly rewrite a hundred older pages. Older episodes that
have no notes yet (the In Our Time run) are a deliberate backfill; run the two
commands above for the slugs you want, then commit:

```bash
./venv/bin/python tools/qwen_explain.py --limit 20         # 20 chunks this pass
./venv/bin/python tools/merge_explain.py                   # merge into frontmatter
git -C . add content/episodes && git commit -m "A2 notes" && git push
```

`flag_a2.py` also flags sentences for every episode, so `tools/a2_chunks/` grows
regardless of which episodes you annotate; `qwen_explain.py` skips any chunk that
already has a result file.

## Android app

`android/` builds an installable APK that opens the site **full screen with no
address bar**. It is a Trusted Web Activity, so Chrome on the phone renders the
live site — new episodes appear without rebuilding anything.

```bash
export http_proxy=http://127.0.0.1:7891 https_proxy=http://127.0.0.1:7891
./android/toolchain-setup.sh                 # once: JDK 17 + Android SDK + Gradle
export JAVA_HOME=/home/deepseek-harness/android-build/jdk17
export ANDROID_HOME=/home/deepseek-harness/android-build/sdk
cd android && /home/deepseek-harness/android-build/gradle/gradle-8.7/bin/gradle assembleRelease
```

Build output is gitignored; the source is committed. Full details — every path,
the toolchain versions, how to verify the APK without a device, the signing key,
and how `assetlinks.json` enables full screen — are in **`android/README.md`**.

The site is also installable *without* the APK: `static/manifest.json` plus the
icons in `static/icons/` let Chrome's "Add to Home screen" produce the same
standalone, no-address-bar experience on Android and iOS.

## Uploading files to Cloudflare R2

`tools/r2_upload.py` is a dependency-free (stdlib only) uploader for the
S3-compatible R2 API — useful for putting large media outside the git repo:

```bash
# credentials live in ~/.r2.env (or <repo>/.ref/r2.env):
#   R2_ACCESS_KEY_ID=...  R2_SECRET_ACCESS_KEY=...
#   R2_ENDPOINT=...       R2_BUCKET=aorta-data
#   R2_PUBLIC_BASE=https://bucket.r2.mapengfei.cn

python3 tools/r2_upload.py aorta-tether-8x-32x.zip          # keeps the file name as the key
python3 tools/r2_upload.py big.mp3 --key audio/big.mp3      # explicit key
python3 tools/r2_upload.py --list-buckets                   # inspect the account
python3 tools/r2_upload.py --list --prefix audio/           # inspect a bucket
python3 tools/r2_upload.py --delete audio/big.mp3           # remove an object
```

`tools/r2_client.py` holds the shared signing/upload code (also used by
`make_episode.py`); `tools/r2_upload.py` is the CLI. It prints the public URL and
verifies it with an HTTP request. Note that the
public custom domain sits behind Cloudflare, which rejects the default
`Python-urllib/*` user agent (403) — the script sends a normal one, and some
proxies also dislike `HEAD`, so the check uses a ranged GET.

## Files page (`/files/`)

A folder-tree browser for the R2 bucket, gated by the same **sync code** the
vocabulary book uses:

- **Enter your sync code** (the header's *Sign in*, or the prompt on the page) to
  list the bucket, upload (drag & drop, with progress) and delete.
- Every file row has **Copy link** (public download URL) and the folders expand
  and collapse; expansion state is remembered per browser.
- Without the code the file list itself is not shown, and `/api/list`,
  `/api/upload` and `/api/delete` all answer 401.

`hugo.toml` points both this page and the vocabulary book at the Worker:

```toml
[params]
  apiBase = "https://r2-portal.mpf-npu.workers.dev"
```

`tools/site-api/worker.js` compares the `Authorization: Bearer …` token against
its `SITE_TOKEN` secret (constant time, and 401 for everyone when it is unset) and
only then serves the routes. The Worker also serves the vocabulary book, and its
deploy notes — including how to create the private bucket and the secret — are in
`tools/site-api/README.md`.

> Keep an eye on `hugo.toml`'s shape: a TOML table header claims **every** key
> after it, so `apiBase`/`audioBase` must stay above the first `[params.x]` block.
> They spent a while nested inside `[params.assets]`, where `site.Params.apiBase`
> is empty — which is exactly how `/files/` quietly lost its backend
> (`data-api=none`) and the audio `audioBase` fallback stopped working.

## The vocabulary book (`/words/`, the ☆ buttons)

One shared secret and one JSON document, both in Cloudflare:

- Tap ☆ on a sentence and it is stored through the Worker as
  `{ slug, idx, show, title, text, explain }`; the bottom player can play any
  saved sentence straight from its moment.
- The code is typed once per device and kept in `localStorage`; the same code on
  another device gives you the same book.
- Storage is a single object, `vocab/v1.json`, in the **private** R2 bucket bound
  as `PRIVATE` (never the public `aorta-data`, which the world can read through
  `bucket.r2.mapengfei.cn`). R2 is read-after-write consistent, so a star you just
  tapped is still there on the next page load.
- The old AppWrite book was abandoned rather than migrated, so no export tool
  lives in the repo. The Worker keeps `POST /api/vocab/import` (it merges by
  `slug:idx`) as the way back in if a JSON backup is ever wanted:

  ```bash
  curl -H "Authorization: Bearer $CODE" -H 'content-type: application/json' \
       --data @vocab.json https://r2-portal.mpf-npu.workers.dev/api/vocab/import
  ```

Why it moved off AppWrite: its free plan pauses a project after 7 days without
*development activity in the Console*, and (per [their announcement](https://appwrite.io/changelog/entry/2026-02-20-1)
and [the community thread](https://appwrite.io/threads/1481574986136158322)) API
traffic, SDK calls and visitor traffic do not count — no cron keep-alive helps,
and the detection is deliberately undocumented. An idle week therefore took the
vocabulary book and `/files/` down together. Nothing in the site talks to AppWrite
now.

## Comments (`/episodes/<slug>/` and `/posts/<slug>/`)

The comment box is [giscus](https://giscus.app): the widget is a third-party
iframe, and **the backend is this repo's Discussions tab** — there is no server of
ours and nothing about comments is stored in git.

- **Moderating** — open the repo's *Discussions* tab and work there:
  **Hide** (keeps the comment but greys it out for everyone but its author — the
  right tool for spam), **Delete** (permanent), **Edit**, **Lock**, or delete the
  whole discussion. Whatever you do shows up on the site on the next page load.
  The category is `Announcements` on purpose: only maintainers can start a thread,
  so nobody can post outside a page's thread.
- **Where it appears** — every episode page (through
  `layouts/episodes/single.html`) and every post. The posts section opts in once,
  in `content/posts/_index.md` (`cascade: comments: true`); add `comments: true`
  to any other page's front matter to give it a thread too. `/words/`, `/files/`,
  `/afsi/` and the list pages are deliberately without comments.
- **One thread per page path** (`mapping = "pathname"`), so a thread's title is
  the page URL; renaming a page's slug starts a fresh thread.
- **Prerequisite: the giscus app must be installed on the repo**
  ([github.com/apps/giscus](https://github.com/apps/giscus) → Install →
  `mapengfei-glasgow.github.io`). Without it the widget renders an error card
  instead of a comment box. This one-liner is the check — the answer must not be
  `giscus is not installed on this repository`:

  ```bash
  curl -s "https://giscus.app/api/discussions?repo=mapengfei-glasgow%2Fmapengfei-glasgow.github.io&repoId=R_kgDOUPDByw&categoryId=DIC_kwDOUPDBy84DGCmo&term=/x/" | head -c 120
  ```

The config lives in `hugo.toml`; the ids come from the picker on giscus.app and
must be re-read there if the repo or the category ever changes:

```toml
[params.giscus]
  repo = "mapengfei-glasgow/mapengfei-glasgow.github.io"
  repoId = "R_kgDOUPDByw"
  category = "Announcements"
  categoryId = "DIC_kwDOUPDBy84DGCmo"
  mapping = "pathname"
  lang = "en"          # "zh-CN" switches the widget to Chinese
  loading = "lazy"     # the iframe is only fetched when scrolled into view
```

`layouts/partials/comments.html` renders the frame (title, "the discussion runs on
GitHub" note, `<noscript>` fallback) and carries the config as data attributes;
`assets/js/comments.js` turns that into the giscus `<script>` on every page
appearance (`turbo:load`), and re-themes the iframe when the site's dark/light
toggle is used. It is a no-op on pages without a comment box.

Trade-off to remember: a commenter needs a **GitHub account**, and anonymous
comments are impossible — that is what buys the zero-backend, zero-cost,
delete-from-the-backend setup. If open anonymous comments are ever wanted, the
alternative is Waline/Twikoo behind a Worker (the site already runs the
`site-api` Worker could hold the database in Cloudflare D1), at the price of
a moderation queue to maintain.

## Figures written as data (`chart` shortcode)

A quantitative figure no longer has to be a matplotlib PNG that gets regenerated
and re-uploaded: the numbers can live **in the Markdown**, and the page draws them
with Chart.js. The reader gets hover tooltips and the exact values, and updating a
figure means editing numbers in the text.

```markdown
{{< chart xlabel="t (s)" ylabel="p (mmHg)" caption="Figure 12. Inflow and outflow pressure." >}}
t, inflow, outflow
0.000, 14.351, 85.000
0.005, 14.898, 84.999
{{< /chart >}}
```

The first line is the header — the first name is the x column, the rest are series
names — and every following line is one sample. An empty cell becomes a gap, so a
missing or non-positive sample can simply be left blank.

| Parameter | Meaning |
|---|---|
| `type` | `line` (default), `bar`, `scatter` |
| `xlabel`, `ylabel` | axis titles (the x title is also used in the tooltip) |
| `title` | title drawn inside the canvas |
| `caption` | caption under the figure (academic pages style it like a table caption) |
| `height` | canvas height in px, default 320 |
| `legend` | `true`/`false` (default: shown when there is more than one series) |
| `xlog`, `ylog` | logarithmic axis (on a log y axis non-positive samples are dropped) |
| `xkind` | `numeric` (default) or `category` (keeps the first column as labels) |
| `colors` | comma-separated colour overrides, one per series |
| `ymirror`, `y2label` | put the listed series (1-based, comma-separated) on a right-hand axis |
| `smooth` | `true` for a slightly smoothed line |

Implementation: `layouts/_shortcodes/chart.html` parses the CSV into JSON and emits a
`<canvas data-chart>` plus a `<script type="application/json" class="chart-data">`
block; `assets/js/charts.js` turns that into the Chart.js configuration. Chart.js is
self-hosted in `static/js/chart.umd.min.js` (no CDN, like MathJax), and the
stylesheet, Chart.js and `charts.js` are loaded only on pages that actually use the
shortcode. The charts follow the PaperMod theme variables and are rebuilt when the
light/dark toggle changes.

`content/posts/chart-demo.md` is a draft page exercising every parameter (two series,
gaps, a category axis, a log axis, a scatter, a mirrored axis) — run `hugo server -D`
and open `/posts/chart-demo/`. `tools/test_charts.mjs` runs the front end in Node
against a small DOM stub:

```bash
node tools/test_charts.mjs          # 17 checks: parser, datasets, scales, the built page
```

## Using the site

- Tap any sentence → playback jumps to that moment; tap the same sentence again to pause
- Play the whole episode: tap the first sentence (with auto-continue on it runs to the end)
- Bottom bar (on every page): ⏮/⏭ step by sentence, ▶/⏸, draggable progress,
  an “Auto-continue” toggle, the current sentence counter (e.g. 13 / 291) and time
- Each episode remembers its own position: switch away and back to resume
- Keyboard, site-wide: ↑/↓ for previous/next sentence, Space to play/pause

## Backfilling older episodes

The In Our Time feed carries the whole archive (~1100 episodes back to 1998), and
Global News keeps a long backlog too. `bbc_podcast.py` can fetch in batches:

```bash
cd ~/dcgrid
python3 bbc_podcast.py in-our-time "$PWD/downloads/In Our Time" --limit 10   # 10 newest not yet downloaded
./venv/bin/python tools/bbc_publish.py --dry-run                            # list what would be published
./venv/bin/python tools/bbc_publish.py --limit 4                            # transcribe → publish → push
```

To fill in a *date range* rather than "the N newest", use `bbc_backfill.py`. The
Global News feed carries two editions a day plus cross-posted items (The Happy
Pod, The Global Story), so "the newest item" is the wrong episode as soon as an
afternoon edition lands first; this takes the earliest item of each date, which
is the edition every existing page matches:

```bash
http_proxy=http://127.0.0.1:7891 https_proxy=http://127.0.0.1:7891 \
  ./venv/bin/python tools/bbc_backfill.py global-news \
    --from 2026-09-13 --to 2026-09-18 --dir "downloads/BBC Global News Podcast"
```

Add `--dry-run` first to see the selection. It is idempotent (downloaded guids
are recorded in `.last_episode.json`).

`bbc_podcast.py --limit N` is the right tool for a show with no "one a day"
meaning — use it for Planet Money, for example:

```bash
http_proxy=http://127.0.0.1:7891 https_proxy=http://127.0.0.1:7891 \
  ./venv/bin/python work/run_download.py planet-money "downloads/Planet Money" --limit 10
./venv/bin/python tools/bbc_publish.py --dry-run     # check titles and slugs first
./venv/bin/python tools/bbc_publish.py               # transcribe → R2 → push
```

### Adding a show

Three small edits, then download and publish as above:

1. `tools/bbc_podcast.py` — add `"<name>": ("<feed url>", "<download dir name>")`
   to `SHOWS`. Any RSS feed with `<enclosure url=…>` works; a raw feed URL can
   also be passed as the show argument without editing anything.
2. `tools/bbc_publish.py` — add `"<Show Name>": [<repo>/downloads/<dir name>]`
   to `SHOWS`. The key must match the show name written into the pages.
3. `data/shows.toml` — add the urlized name with an icon and a description; that
   drives the show's card on the home page and its category page.

`make_episode.py --show "<Show Name>"` writes that name into `categories`, so the
category page and the card appear on the next build with no further wiring.

- `bbc_podcast.py` skips trailers (< 5 MB), items belonging to other programmes,
  and keeps a `.downloaded.json` title index next to the MP3s (so real feed titles
  like `Archive: Coffee` are preserved).
- `bbc_publish.py` skips any episode that already has a page, so re-running is safe.
- Transcription runs at roughly 4–5 minutes per 50-minute episode on this machine.
- On networks where the BBC's Akamai edge answers 403, both downloaders retry the
  episode through the other CDN connections the mediaset API lists (CloudFront
  works); see `work/HOST-NOTES.md`. That path is BBC-specific and simply inert
  for other feeds.

### Where the audio lives (Cloudflare R2)

Audio is **not** kept in this repo. `make_episode.py` encodes the episode, uploads
it to R2 and records the public URL in the page front matter:

```yaml
audioDir: "2026-08-13-archive-coffee"
audioURL: "https://bucket.r2.mapengfei.cn/audio/2026-08-13-archive-coffee/episode.mp3"
```

`layouts/episodes/single.html` resolves the player source in this order:
`params.audioURL` → `site.Params.audioBase` + `audioDir` → a local
`/audio/<slug>/episode.mp3` (legacy fallback).

- bucket `aorta-data`, key prefix `audio/`, public base `https://bucket.r2.mapengfei.cn`
- credentials: `~/.r2.env` or `<repo>/.ref/r2.env` (see `tools/r2_client.py`)
- flags: `--no-upload` (keep it local), `--keep-local` (upload *and* keep the file),
  `--r2-prefix` (default `audio`)
- if the upload fails the local file is kept and the page falls back to it

Sizes: the published site is ~2 MB and the repo's tracked files ~5 MB; R2's free
tier is 10 GB, i.e. roughly 270 In Our Time episodes. Old audio still sits in the
git history from before this migration (~530 MB) — rewriting history would reclaim
it, but it no longer grows.

## Adding a show / an episode

1. Download the MP3 with `bbc_podcast.py` or by hand
2. Run `make_episode.py`
3. Reload the site (or push — GitHub Actions publishes it)
