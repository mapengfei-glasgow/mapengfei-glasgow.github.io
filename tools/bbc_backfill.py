#!/usr/bin/env python3
"""Backfill a date range of a BBC podcast (one episode per day).

The daily systemd timer runs `bbc_podcast.py SHOW --limit 1`, which takes the
newest not-yet-downloaded item. That is correct for the daily flow but wrong for
a backfill, because the Global News Podcast feed carries *two* editions per day
plus cross-posted items from other programmes ("The Happy Pod", "The Global
Story"). Walking newest-first therefore both overshoots and picks the wrong
edition.

This tool selects, for every date in the requested range, the **earliest** item
published that day. That is the edition the site has always published: checked
against the feed, every existing episode page (2026-09-03 … 2026-09-12) matches
the earliest item of its own date.

It reuses bbc_podcast.py's feed parsing, atomic download and Akamai-403 →
CloudFront fallback, and keeps the same `.last_episode.json` / `.downloaded.json`
state files so the daily flow carries on normally afterwards.

Usage (the BBC is only reachable through the local Mihomo proxy on this host):

    http_proxy=http://127.0.0.1:7891 https_proxy=http://127.0.0.1:7891 \
        python3 tools/bbc_backfill.py global-news --from 2026-09-13 --to 2026-09-18

Exit codes: 0 = ok, 1 = fetch error, 2 = usage/unexpected error.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bbc_podcast as bp  # noqa: E402

log = logging.getLogger("bbc_backfill")


def select_one_per_day(episodes: list[dict], start: str, end: str,
                       done: set[str]) -> list[dict]:
    """Earliest item of each date in [start, end], oldest date first."""
    best: dict[str, dict] = {}
    for ep in episodes:
        date = ep.get("date")
        if not date or not (start <= date <= end):
            continue
        # Cross-posted items from other programmes are never the daily edition.
        if "(from " in ep["title"].lower():
            continue
        cur = best.get(date)
        if cur is None or ep["pub_date"] < cur["pub_date"]:
            best[date] = ep
    # Pick the earliest item of each date FIRST, and only then drop the dates
    # that are already covered. Filtering by `done` before the comparison would
    # fall through to the *next* edition of a day whose morning edition is
    # already downloaded — i.e. it would quietly start pulling in the afternoon
    # edition as well (which is exactly what happened on 2026-09-18).
    return [best[d] for d in sorted(best) if best[d]["guid"] not in done]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("show", help='show name (e.g. "global-news") or a raw feed URL')
    ap.add_argument("--from", dest="start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--to", dest="end", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--dir", type=Path, default=None, help="download directory")
    ap.add_argument("--min-mb", type=float, default=5.0,
                    help="treat items smaller than this as trailers (default 5)")
    ap.add_argument("--dry-run", action="store_true", help="only list what would download")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")

    # The proxy on this host is slow; the module defaults (60 s / 900 s) are tight.
    bp.FEED_TIMEOUT = 300
    bp.DOWNLOAD_TIMEOUT = 3600
    bp.CHUNK_SIZE = 256 * 1024
    min_bytes = int(args.min_mb * 1e6)

    show = args.show.lower()
    if show in bp.SHOWS:
        feed_url, default_dir = bp.SHOWS[show]
    elif show.startswith("http"):
        feed_url, default_dir = show, "BBC Podcast"
    else:
        log.error("unknown show %r (known: %s)", show, ", ".join(bp.SHOWS))
        return 2

    download_dir = (args.dir.expanduser() if args.dir
                    else Path.home() / "Downloads" / default_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    state_path = download_dir / bp.STATE_FILE_NAME
    index_path = download_dir / bp.INDEX_FILE_NAME

    log.info("fetching feed: %s", feed_url)
    episodes = bp.parse_episodes(bp.fetch_bytes(feed_url, bp.FEED_TIMEOUT))
    log.info("feed has %d items", len(episodes))

    state = bp.load_state(state_path)
    index = bp.load_index(index_path)
    done = bp.done_guids(state)
    guids: list[str] = list(state.get("guids") or [])

    chosen = select_one_per_day(episodes, args.start, args.end, done)
    if not chosen:
        log.info("nothing to backfill in %s … %s", args.start, args.end)
        return 0

    log.info("%d episode(s) selected (one per day, earliest edition):", len(chosen))
    for ep in chosen:
        log.info("  %s  %-55s %5.1f MB", ep["date"], ep["title"][:55],
                 ep["declared_length"] / 1e6)
    if args.dry_run:
        return 0

    downloaded = 0
    for ep in chosen:
        if 0 < ep["declared_length"] < min_bytes:
            log.info("skipping short item: %s", ep["title"])
            continue
        filename = f"{ep['date']} {bp.slugify(ep['title'])}.mp3"
        dest = download_dir / filename
        if dest.exists() and dest.stat().st_size >= bp.MIN_AUDIO_BYTES:
            log.info("already on disk: %s", filename)
        else:
            log.info("downloading %s", filename)
            size = bp.download_episode_audio(ep["audio_url"], dest)
            log.info("saved %s (%.1f MiB)", dest.name, size / 1024 / 1024)
            downloaded += 1
        if ep["guid"] not in guids:
            guids.append(ep["guid"])
        index[filename] = {"title": ep["title"], "date": ep["date"],
                           "guid": ep["guid"]}
        state.update({
            "guid": ep["guid"],
            "audio_url": ep["audio_url"],
            "title": ep["title"],
            "pub_date": ep["pub_date"],
            "file": dest.name,
            "bytes": dest.stat().st_size,
            "guids": guids,
            "backfilled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        bp.save_state(state_path, state)

    state["guids"] = guids
    bp.save_state(state_path, state)
    bp.save_index(index_path, index)
    log.info("done: %d downloaded into %s", downloaded, download_dir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except bp.FetchError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except Exception:
        log.exception("unexpected error")
        sys.exit(2)
