#!/usr/bin/env python3
"""Download episodes of a BBC podcast.

Intended to be run daily by systemd user timers, and for one-off backfills.

Usage:
    bbc_podcast.py SHOW [DOWNLOAD_DIR] [--limit N] [--dry-run]
                        [--min-bytes BYTES] [--include-shorts]

SHOW is one of the known show names below, or a raw feed URL.
DOWNLOAD_DIR defaults to ~/Downloads/<Show Name>; it is created if missing.

Behaviour:
  * Fetches the RSS feed and walks it newest first.
  * Skips episodes already recorded in the state file (.last_episode.json).
  * Downloads up to --limit episodes (default 1 = the daily behaviour),
    atomically (via a .part temp file), named "<YYYY-MM-DD> <Title>.mp3".
  * Items smaller than --min-bytes (default 5 MB) are treated as trailers and
    skipped unless --include-shorts is given.
  * If the CDN the feed points at rejects the download (Akamai answers 403
    "Access Denied" on some networks), the other connections the BBC mediaset
    API lists for that episode are tried before giving up.

Exit codes: 0 = ok (downloaded or nothing new), non-zero = failure.
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; bbc-podcast-downloader/1.0)"
FEED_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 900
CHUNK_SIZE = 1024 * 1024
STATE_FILE_NAME = ".last_episode.json"
MIN_AUDIO_BYTES = 100 * 1024        # guard against error pages
DEFAULT_MIN_EPISODE_BYTES = 5 * 1024 * 1024  # anything smaller is a trailer

# Known shows: name -> (feed URL, default download directory name)
SHOWS: dict[str, tuple[str, str]] = {
    "global-news": (
        "https://podcasts.files.bbci.co.uk/p02nq0gn.rss",
        "BBC Global News Podcast",
    ),
    "in-our-time": (
        "https://podcasts.files.bbci.co.uk/b006qykl.rss",
        "In Our Time",
    ),
}

log = logging.getLogger("bbc_podcast")

# The RSS enclosure points at BBC's redirector (…/mediaset/audio-nondrm-download-rss/
# proto/http/vpid/<vpid>.mp3). Asking the mediaset API for that vpid returns every
# CDN connection for the episode, which is what the 403 fallback below uses.
MEDIASET_JSON = ("https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/"
                 "mediaset/audio-nondrm-download/vpid/{vpid}.json")
VPID_RE = re.compile(r"/vpid/([A-Za-z0-9]+)")
PREFERRED_SUPPLIERS = ("mf_cloudfront",)


class FetchError(Exception):
    pass


def fetch_bytes(url: str, timeout: int, retries: int = 3) -> bytes:
    """GET a URL, following redirects, with simple retries."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_exc = exc
            log.warning("fetch failed (attempt %d/%d): %s", attempt, retries, exc)
    raise FetchError(f"could not fetch {url}: {last_exc}") from last_exc


def _episode_from_item(item: ET.Element) -> dict | None:
    """Turn one <item> into an episode dict; None if it has no usable enclosure."""
    enc = item.find("enclosure")
    if enc is None or not enc.get("url"):
        return None
    title = html.unescape((item.findtext("title") or "unknown episode").strip())
    pub_date = item.findtext("pubDate") or ""
    guid = (item.findtext("guid") or item.findtext("link") or enc.get("url") or "").strip()

    date_part = None
    try:
        dt = parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        date_part = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        log.warning("could not parse pubDate %r; using 'undated'", pub_date)

    return {
        "title": title,
        "pub_date": pub_date,
        "guid": guid,
        "audio_url": enc.get("url").strip(),
        "declared_length": int(enc.get("length") or 0),
        "date": date_part,
    }


def parse_episodes(feed: bytes) -> list[dict]:
    """Return every item of the feed, in feed order (normally newest first)."""
    try:
        root = ET.fromstring(feed)
    except ET.ParseError as exc:
        raise FetchError(f"invalid RSS feed: {exc}") from exc

    episodes = []
    for item in root.findall("./channel/item"):
        ep = _episode_from_item(item)
        if ep:
            episodes.append(ep)
    if not episodes:
        raise FetchError("feed contains no usable items")
    return episodes


def parse_latest_episode(feed: bytes) -> dict:
    """Return the most recent item of the feed as a dict (kept for compatibility)."""
    return parse_episodes(feed)[0]


def slugify(text: str, maxlen: int = 80) -> str:
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:maxlen].rstrip() or "episode"


INDEX_FILE_NAME = ".downloaded.json"


def load_index(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_index(path: Path, index: dict) -> None:
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(state_path: Path) -> dict:
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def done_guids(state: dict) -> set[str]:
    """Guids already fetched; understands the older single-episode state file."""
    guids = set(state.get("guids") or [])
    if state.get("guid"):
        guids.add(state["guid"])
    return guids


def download_audio(url: str, dest: Path) -> int:
    """Download url to dest atomically; returns size in bytes."""
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".part", dir=dest.parent)
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
            timeout=DOWNLOAD_TIMEOUT,
        ) as resp, open(fd, "wb") as out:
            shutil.copyfileobj(resp, out, CHUNK_SIZE)
        size = Path(tmp_name).stat().st_size
        if size < MIN_AUDIO_BYTES:
            raise FetchError(f"suspiciously small download ({size} bytes)")
        Path(tmp_name).chmod(0o644)
        Path(tmp_name).replace(dest)
        return size
    except BaseException:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def alternative_audio_urls(url: str) -> list[str]:
    """Other CDN connections for the same episode, best first.

    Nothing to do when the URL carries no vpid (an unexpected feed format) or
    the mediaset lookup fails; both cases just return an empty list.
    """
    m = VPID_RE.search(url)
    if not m:
        return []
    try:
        data = json.loads(fetch_bytes(MEDIASET_JSON.format(vpid=m.group(1)), FEED_TIMEOUT))
    except (FetchError, ValueError) as exc:
        log.warning("mediaset lookup failed: %s", exc)
        return []

    def rank(c: dict) -> tuple[int, int]:
        return (0 if c.get("supplier") in PREFERRED_SUPPLIERS else 1,
                0 if c.get("protocol") == "https" else 1)

    conns = [c for media in data.get("media", [])
             for c in media.get("connection", []) if c.get("href")]
    out: list[str] = []
    for c in sorted(conns, key=rank):
        if c["href"] != url and c["href"] not in out:
            out.append(c["href"])
    return out


def download_episode_audio(url: str, dest: Path) -> int:
    """download_audio(), retrying the episode's other CDN connections.

    Some networks are denied (403) by the Akamai edge the feed usually points
    at, while the CloudFront connection listed by the mediaset API serves the
    same file, so a failed download is retried elsewhere before giving up.
    """
    try:
        return download_audio(url, dest)
    except (urllib.error.URLError, FetchError, TimeoutError, ConnectionError) as exc:
        last_exc: Exception = exc
        log.warning("download failed (%s); trying another CDN connection", exc)

    for alt in alternative_audio_urls(url):
        log.info("retrying via %s", urllib.parse.urlparse(alt).netloc)
        try:
            return download_audio(alt, dest)
        except (urllib.error.URLError, FetchError, TimeoutError, ConnectionError) as exc:
            last_exc = exc
            log.warning("still failing (%s)", exc)
    raise last_exc


def parse_args(argv: list[str]) -> tuple[str, Path | None, int, bool, int, bool] | None:
    """Split argv into (show, download_dir, limit, dry_run, min_bytes, include_shorts)."""
    positional, limit, dry_run, include_shorts = [], 1, False, False
    min_bytes = DEFAULT_MIN_EPISODE_BYTES
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit":
            i += 1
            if i >= len(argv):
                log.error("--limit needs a value")
                return None
            limit = int(argv[i])
        elif a == "--dry-run":
            dry_run = True
        elif a == "--include-shorts":
            include_shorts = True
        elif a == "--min-bytes":
            i += 1
            if i >= len(argv):
                log.error("--min-bytes needs a value")
                return None
            min_bytes = int(argv[i])
        elif a.startswith("-"):
            log.error("unknown option %r", a)
            return None
        else:
            positional.append(a)
        i += 1

    if not positional:
        return None
    show = positional[0].lower()
    download_dir = Path(positional[1]).expanduser() if len(positional) > 1 else None
    return show, download_dir, max(1, limit), dry_run, min_bytes, include_shorts


def main(args: list[str]) -> int:
    """args = [SHOW, DOWNLOAD_DIR?] plus optional flags; DOWNLOAD_DIR is optional."""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    args = [a for a in args if a]
    parsed = parse_args(args)
    if not parsed:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    show, explicit_dir, limit, dry_run, min_bytes, include_shorts = parsed

    if show in SHOWS:
        feed_url, default_dir = SHOWS[show]
        label = show.replace("-", " ")
    elif show.startswith("http"):
        feed_url, default_dir, label = show, "BBC Podcast", show
    else:
        log.error("unknown show %r (known: %s)", show, ", ".join(SHOWS))
        return 2

    download_dir = explicit_dir or (Path.home() / "Downloads" / default_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    state_path = download_dir / STATE_FILE_NAME

    log.info("[%s] fetching feed: %s", label, feed_url)
    episodes = parse_episodes(fetch_bytes(feed_url, FEED_TIMEOUT))
    log.info("[%s] feed has %d episodes (%s … %s)", label, len(episodes),
             episodes[0].get("date"), episodes[-1].get("date"))

    state = load_state(state_path)
    index_path = download_dir / INDEX_FILE_NAME
    index = load_index(index_path)
    index_dirty = False
    done = done_guids(state)
    log.info("[%s] %d episodes already fetched", label, len(done))
    guids: list[str] = list(state.get("guids") or [])

    fresh = [ep for ep in episodes if ep["guid"] not in done]
    cross_show = [ep for ep in fresh if re.search(r"\(from ", ep["title"], re.I)]
    if cross_show:
        fresh = [ep for ep in fresh if ep not in cross_show]
        for ep in cross_show:
            log.info("[%s] skipping item from another programme: %s", label, ep["title"])
    if not include_shorts:
        shorts = [ep for ep in fresh if 0 < ep["declared_length"] < min_bytes]
        fresh = [ep for ep in fresh if ep["declared_length"] >= min_bytes or ep["declared_length"] == 0]
        for ep in shorts:
            log.info("[%s] skipping short item: %s (%.1f MB)",
                     label, ep["title"], ep["declared_length"] / 1e6)

    if not fresh:
        log.info("[%s] nothing new to download", label)
        return 0

    chosen = fresh[:limit]
    log.info("[%s] %d new episode(s) available; taking %d", label, len(fresh), len(chosen))

    downloaded = 0
    for ep in chosen:
        filename = f"{ep['date'] or 'undated'} {slugify(ep['title'])}.mp3"
        dest = download_dir / filename
        if dest.exists() and dest.stat().st_size >= MIN_AUDIO_BYTES:
            log.info("[%s] already on disk: %s", label, filename)
            if ep["guid"] not in guids:
                guids.append(ep["guid"])
            index[filename] = {"title": ep["title"], "date": ep["date"], "guid": ep["guid"]}
            index_dirty = True
            continue
        log.info("[%s] %s (%s, %.1f MB declared)", label, filename, ep["date"],
                 ep["declared_length"] / 1e6)
        if dry_run:
            continue
        size = download_episode_audio(ep["audio_url"], dest)
        log.info("[%s] saved %s (%.1f MiB)", label, dest.name, size / 1024 / 1024)
        guids.append(ep["guid"])
        index[filename] = {"title": ep["title"], "date": ep["date"], "guid": ep["guid"]}
        index_dirty = True
        downloaded += 1
        state.update({
            "guid": ep["guid"],
            "audio_url": ep["audio_url"],
            "title": ep["title"],
            "pub_date": ep["pub_date"],
            "file": dest.name,
            "bytes": size,
            "guids": guids,
        })
        save_state(state_path, state)

    if not dry_run and (downloaded or guids != (state.get("guids") or [])):
        state["guids"] = guids
        save_state(state_path, state)
    if not dry_run and index_dirty:
        save_index(index_path, index)
        log.info("[%s] title index updated: %s", label, index_path.name)
    log.info("[%s] done: %d downloaded", label, downloaded)
    return 0


def entry(argv: list[str]) -> int:
    """main() with top-level error handling; returns a process exit code."""
    try:
        return main(argv)
    except FetchError as exc:
        log.error("%s", exc)
        return 1
    except Exception:
        log.exception("unexpected error")
        return 2


if __name__ == "__main__":
    sys.exit(entry(sys.argv[1:]))
