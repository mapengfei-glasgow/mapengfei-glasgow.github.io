#!/usr/bin/env python3
"""Publish downloaded BBC episodes to the site.

Handles both the daily flow (the systemd timers download the newest episode,
this script publishes it) and one-off backfills (download a batch with
`bbc_podcast.py --limit N`, then publish them here).

Steps per candidate episode:
  1. work out its slug (`<date>-<slugified title>`, exactly like make_episode)
  2. skip it if `content/episodes/<slug>.md` already exists → already published
  3. otherwise run tools/make_episode.py (faster-whisper → sentences → CBR 96k)
  4. if anything was produced: git add -A && commit && push
     (GitHub Actions then rebuilds and deploys the site)

Titles come from the `.downloaded.json` index that bbc_podcast.py writes next to
the MP3s, falling back to the filename.

Usage:
    ./venv/bin/python tools/bbc_publish.py [--limit N] [--dry-run] [--model NAME]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "english-site"
VENV_PYTHON = ROOT / "venv" / "bin" / "python"
MAKE_EPISODE = ROOT / "tools" / "make_episode.py"
INDEX_NAME = ".downloaded.json"

# Show name → directories to scan (workspace first, then the home Downloads dir;
# the latter is read-only on some setups but still readable)
SHOWS: dict[str, list[Path]] = {
    "Global News Podcast": [ROOT / "downloads" / "BBC Global News Podcast",
                            Path.home() / "Downloads" / "BBC Global News Podcast"],
    "In Our Time": [ROOT / "downloads" / "In Our Time",
                    Path.home() / "Downloads" / "In Our Time"],
    "Planet Money": [ROOT / "downloads" / "Planet Money",
                     Path.home() / "Downloads" / "Planet Money"],
    "Why Oh Why": [ROOT / "downloads" / "Why Oh Why",
                   Path.home() / "Downloads" / "Why Oh Why"],
}

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ _]+(.+)$")


def load_slugify():
    """Reuse make_episode's slugify so the computed slug always matches."""
    spec = importlib.util.spec_from_file_location("make_episode", MAKE_EPISODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.slugify


def candidates(slugify, min_mb: float = 5.0) -> list[dict]:
    """Every downloaded MP3 that does not have a page yet, oldest first."""
    found: list[dict] = []
    for show, dirs in SHOWS.items():
        for d in dirs:
            if not d.is_dir():
                continue
            try:
                index = json.loads((d / INDEX_NAME).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                index = {}
            for mp3 in sorted(d.glob("*.mp3")):
                m = DATE_RE.match(mp3.stem)
                if not m:
                    continue
                if mp3.stat().st_size < min_mb * 1e6:
                    print(f"[skip] {mp3.name}: {mp3.stat().st_size/1e6:.1f} MB looks like a trailer")
                    continue
                date, from_name = m.group(1), m.group(2).strip()
                meta = index.get(mp3.name) or {}
                title = (meta.get("title") or from_name).strip()
                slug = f"{date}-{slugify(title)}"
                if (SITE / "content" / "episodes" / f"{slug}.md").exists():
                    continue
                found.append({"show": show, "mp3": mp3, "date": date,
                              "title": title, "slug": slug})
    found.sort(key=lambda c: (c["date"], c["title"]))
    return found


def audio_size_mb() -> float:
    total = sum(f.stat().st_size for f in (SITE / "static" / "audio").glob("*/*.mp3"))
    return total / 1e6


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0,
                    help="publish at most N episodes (0 = all pending)")
    ap.add_argument("--model", default="small", help="whisper model (default small)")
    ap.add_argument("--dry-run", action="store_true", help="only list what would happen")
    ap.add_argument("--min-mb", type=float, default=5.0,
                    help="ignore MP3s smaller than this (trailers); default 5")
    args = ap.parse_args()

    os.environ.setdefault("HF_HOME", str(ROOT / ".hf-cache"))
    if not VENV_PYTHON.exists():
        print(f"venv python not found: {VENV_PYTHON}")
        return 2

    slugify = load_slugify()
    pending = candidates(slugify, args.min_mb)
    if args.limit:
        pending = pending[:args.limit]

    print(f"published episodes on site: {len(list((SITE / 'content' / 'episodes').glob('*.md')))}"
          f" · audio {audio_size_mb():.0f} MB")
    if not pending:
        print("nothing new to publish.")
        return 0
    print(f"pending: {len(pending)} episode(s)")
    for c in pending:
        print(f"  {c['date']}  {c['show']:<22} {c['title']}  →  {c['slug']}")

    if args.dry_run:
        return 0

    processed = []
    for c in pending:
        cmd = [str(VENV_PYTHON), str(MAKE_EPISODE), str(c["mp3"]),
               "--show", c["show"], "--title", c["title"], "--date", c["date"],
               "--model", args.model, "--site", str(SITE)]
        print(f"[run] {c['show']} {c['date']}: {c['title']}", flush=True)
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rc == 0:
            processed.append(c)
        elif rc == 1:
            print(f"[skip] make_episode refused {c['mp3'].name} (already exists?)")
        else:
            print(f"[WARN] make_episode failed ({rc}) for {c['mp3'].name}; stopping here")
            break

    if not processed:
        print("nothing was produced — no commit.")
        return 0

    msg = "add episode(s): " + ", ".join(f"{c['show']} {c['date']}" for c in processed)
    git = ["git", "-C", str(SITE)]
    for cmd in [["add", "-A"], ["commit", "-m", msg], ["push", "origin", "main"]]:
        r = subprocess.run(git + cmd, cwd=str(SITE))
        if r.returncode != 0:
            print(f"[WARN] git {cmd[0]} failed")
            return r.returncode
    print(f"published {len(processed)} episode(s) · audio now {audio_size_mb():.0f} MB")
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
