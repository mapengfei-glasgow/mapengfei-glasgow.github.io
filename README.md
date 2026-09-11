# English Listening

Podcast audio is transcribed and **timestamped sentence by sentence**, so tapping
any sentence jumps playback to that exact moment. The episode audio stays loaded
in a persistent bottom player bar, and navigating between pages never interrupts it —
built for close listening and shadowing.

Stack: Hugo + [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme + AppWrite (vocabulary book).

## Layout

```
english-site/          # the Hugo site
  content/episodes/    # one .md per episode (front matter holds every sentence + its timestamps)
  data/transcripts/    # <slug>.small.json per episode (word-level timestamps)
  static/audio/<slug>/ # LOCAL ONLY while building: the episode MP3 is uploaded to
                       # R2 and then removed, so the repo keeps pages only
  static/css/          # main.css — styles for our own components only
  assets/js/           # player.js (bottom bar + episode page wiring)
                       # appwrite.js (vocabulary book)
  layouts/             # index.html (home: intro + cards), episodes/single.html,
                       # words/list.html, partials/ overrides
  themes/PaperMod/     # theme (git submodule)
tools/make_episode.py  # MP3 → full audio + Hugo content (with sentence timestamps)
tools/bbc_podcast.py   # downloader for the BBC feeds (run by systemd timers)
bin/                   # static hugo / ffmpeg binaries, uv
venv/                  # Python environment (faster-whisper)
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

Two systemd user timers download the newest episodes, and one publishes them:

- `~/.config/systemd/user/bbc_gnp.timer` — 09:00, Global News Podcast
- `~/.config/systemd/user/bbc_iot.timer` — 11:00, In Our Time
- `tools/systemd/bbc-publish.timer` — 12:30, runs `tools/bbc_publish.py`, which
  transcribes any newly downloaded episode, generates its page, commits and pushes

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

- `bbc_podcast.py` skips trailers (< 5 MB), items belonging to other programmes,
  and keeps a `.downloaded.json` title index next to the MP3s (so real feed titles
  like `Archive: Coffee` are preserved).
- `bbc_publish.py` skips any episode that already has a page, so re-running is safe.
- Transcription runs at roughly 4–5 minutes per 50-minute episode on this machine.

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
