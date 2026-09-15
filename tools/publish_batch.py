#!/usr/bin/env python3
"""Run make_episode.py for a list of downloaded MP3s with a bounded pool.

Usage:
    publish_batch.py [--workers N] MP3 [--title T --date D] ...

Each argument after --workers is one episode: MP3 path plus optional
--title/--date pairs (same semantics as make_episode.py defaults: title
from the index/filename, date from the filename prefix).

Does NOT commit or push — run git after the batch finishes.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / "venv" / "bin" / "python"
MAKE_EPISODE = ROOT / "tools" / "make_episode.py"
SHOW = "In Our Time"
DOWNLOAD_DIR = ROOT / "downloads" / "In Our Time"
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ _]+(.+)$")


def load_index() -> dict:
    try:
        return json.loads((DOWNLOAD_DIR / ".downloaded.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run_one(mp3: Path, index: dict) -> tuple[str, int, str]:
    m = DATE_RE.match(mp3.stem)
    date = m.group(1) if m else ""
    title = (index.get(mp3.name) or {}).get("title") or (m.group(2) if m else mp3.stem)
    cmd = [str(VENV_PYTHON), str(MAKE_EPISODE), str(mp3),
           "--show", SHOW, "--title", title, "--date", date,
           "--model", "small", "--site", str(ROOT / "english-site")]
    log_dir = ROOT / ".tmp-ep-logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"ep-{mp3.stem.replace(' ', '_')}.log"
    with open(log_file, "w", encoding="utf-8") as lf:
        rc = subprocess.run(cmd, cwd=str(ROOT), stdout=lf, stderr=subprocess.STDOUT).returncode
    tail = log_file.read_text(encoding="utf-8").strip().splitlines()
    last = tail[-1] if tail else ""
    return mp3.name, rc, last


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("mp3s", nargs="+", type=Path)
    args = ap.parse_args()

    index = load_index()
    ok, failed = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, p.expanduser().resolve(), index): p.name
                for p in args.mp3s}
        for fut in concurrent.futures.as_completed(futs):
            name, rc, last = fut.result()
            status = "ok" if rc == 0 else f"FAIL({rc})"
            print(f"[{status}] {name}: {last}", flush=True)
            (ok if rc == 0 else failed).append(name)

    print(f"\n{len(ok)} ok, {len(failed)} failed")
    for f in failed:
        print(f"  failed: {f}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
