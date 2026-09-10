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
  static/audio/<slug>/ # the full episode.mp3 (sentences seek by timestamp; no slicing)
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

## Using the site

- Tap any sentence → playback jumps to that moment; tap the same sentence again to pause
- Play the whole episode: tap the first sentence (with auto-continue on it runs to the end)
- Bottom bar (on every page): ⏮/⏭ step by sentence, ▶/⏸, draggable progress,
  an “Auto-continue” toggle, the current sentence counter (e.g. 13 / 291) and time
- Each episode remembers its own position: switch away and back to resume
- Keyboard, site-wide: ↑/↓ for previous/next sentence, Space to play/pause

## Adding a show / an episode

1. Download the MP3 with `bbc_podcast.py` or by hand
2. Run `make_episode.py`
3. Reload the site (or push — GitHub Actions publishes it)
