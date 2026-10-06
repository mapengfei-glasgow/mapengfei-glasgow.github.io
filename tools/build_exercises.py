#!/usr/bin/env python3
"""Build the /exercises/ page data from the upstream exercises-dataset repo.

Upstream: https://github.com/hasaneyldrm/exercises-dataset (1,324 exercises)

What this writes
----------------
`static/exercises/exercises.json` — one file, fetched by assets/js/exercises.js
at runtime. It is NOT a Hugo `data/` file on purpose: Hugo would parse 2.5 MB of
JSON on every build and bake it into the template context, while the browser only
needs it after the first paint (and GitHub Pages sends it gzipped, ~0.3 MB).

Why the data is trimmed
-----------------------
Upstream `data/exercises.json` is 17 MB: 10 instruction languages, ISO
timestamps, and duplicated `category`/`body_part`. The site is a Chinese-UI
bilingual page, so only `zh` + `en` instructions and steps are kept (pass
`--langs` to change that), and `body_part` is dropped because it is byte-for-byte
identical to `category` in all 1,324 records (the script asserts this instead of
trusting it).

Media is deliberately NOT copied
--------------------------------
The 1,324 thumbnails (12 MB) and animation GIFs (126 MB) are © Gym visual and
are NOT covered by the dataset's MIT license (`NOTICE.md` upstream: "cloning this
repository does not grant you any license to the media"). Instead of
re-distributing them from this repo, the page points at jsDelivr, which serves
the upstream repository:
    https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@main/videos/<id>-<mediaId>.gif
The base URL is `params.exercises.mediaBase` in hugo.toml, so it can be pointed
at an R2 bucket (tools/r2_upload.py) without touching any code. Every record in
the output carries the `attribution` string the rights holder requires, and the
page renders it.

Usage
-----
    tools/build_exercises.py                 # clone/refresh upstream into .scratch/, rebuild
    tools/build_exercises.py --update        # git pull the existing upstream clone first
    tools/build_exercises.py --source /path  # use an existing clone
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / ".scratch" / "exercises-dataset"
UPSTREAM_URL = "https://github.com/hasaneyldrm/exercises-dataset.git"
UPSTREAM_WEB = "https://github.com/hasaneyldrm/exercises-dataset"

OUT_DIR = REPO / "static" / "exercises"
OUT_FILE = OUT_DIR / "exercises.json"

# The rights holder's required notice, kept verbatim in every record (upstream
# `attribution` field) and shown on the page.
ATTRIBUTION = "© Gym visual — https://gymvisual.com/"

DEFAULT_LANGS = ("zh", "en")

# Facet order for the filter dropdowns. Upstream values are lowercase English;
# the page renders Chinese labels from its own table, so the data stays raw.
FACETS = ("category", "equipment", "target", "muscleGroup")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, **kw)


def ensure_source(path: Path, update: bool) -> Path:
    """Return a usable clone of the upstream dataset, cloning/pulling as needed."""
    if not (path / "data" / "exercises.json").exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise SystemExit(
                f"{path} exists but is not an exercises-dataset clone.\n"
                f"Remove it, or pass --source with the right path."
            )
        print(f"cloning {UPSTREAM_URL} → {path}", file=sys.stderr)
        run(["git", "clone", "--depth", "1", UPSTREAM_URL, str(path)])
    elif update:
        print(f"updating {path}", file=sys.stderr)
        run(["git", "-C", str(path), "fetch", "--depth", "1", "origin"])
        # The clone is shallow and never carries local commits, so hard-reset to
        # whatever origin has: a plain pull would fail on any rewritten history.
        run(["git", "-C", str(path), "reset", "--hard", "origin/HEAD"])
    return path


def upstream_commit(path: Path) -> str:
    try:
        return run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                   stdout=subprocess.PIPE).stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_key(value: str) -> str:
    """ASCII-fold a facet value so the page can sort/compare without surprises."""
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def build(source: Path, langs: tuple[str, ...]) -> dict:
    raw = json.loads((source / "data" / "exercises.json").read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise SystemExit("upstream data/exercises.json is not a non-empty list")

    ids = [e["id"] for e in raw]
    if len(set(ids)) != len(ids):
        raise SystemExit("upstream data has duplicate exercise ids")

    # Guard the assumptions this whole script (and the media URL layout) rests on.
    for e in raw:
        if e["category"] != e["body_part"]:
            raise SystemExit(f"{e['id']}: category != body_part — stop dropping body_part")
        if e["image"] != f"images/{e['id']}-{e['media_id']}.jpg":
            raise SystemExit(f"{e['id']}: unexpected image path {e['image']}")
        if e["gif_url"] != f"videos/{e['id']}-{e['media_id']}.gif":
            raise SystemExit(f"{e['id']}: unexpected gif path {e['gif_url']}")
        if e.get("attribution") != ATTRIBUTION:
            raise SystemExit(f"{e['id']}: attribution changed upstream: {e.get('attribution')!r}")
        for lang in langs:
            if not e["instructions"].get(lang) or not e["instruction_steps"].get(lang):
                raise SystemExit(f"{e['id']}: missing {lang} instructions/steps")

    def pick(mapping: dict) -> dict:
        """Keep only the requested languages, in the requested order."""
        return {lang: mapping[lang] for lang in langs if mapping.get(lang)}

    exercises = []
    for e in raw:
        exercises.append({
            "id": e["id"],
            "name": e["name"],
            "category": e["category"],
            "equipment": e["equipment"],
            "target": e["target"],
            "muscleGroup": e["muscle_group"],
            "secondaryMuscles": e["secondary_muscles"],
            "mediaId": e["media_id"],
            "instructions": pick(e["instructions"]),
            "steps": pick(e["instruction_steps"]),
        })

    # Facets with counts, ordered by how many exercises carry each value, so the
    # most useful filter entries come first (body weight, dumbbell, …).
    facets = {}
    for facet in FACETS:
        counts = Counter(e[facet] for e in exercises)
        facets[facet] = [
            {"value": v, "count": c, "key": norm_key(v)}
            for v, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    exercises.sort(key=lambda e: (e["name"].lower(), e["id"]))

    return {
        "version": 1,
        "generated": iso_now(),
        "languages": list(langs),
        "count": len(exercises),
        "upstream": {
            "repo": UPSTREAM_WEB,
            "mediaRepo": UPSTREAM_WEB,
            "commit": upstream_commit(source),
        },
        "attribution": ATTRIBUTION,
        "license": {
            "data": "MIT (names, categories, muscle data, instruction text)",
            "media": "© Gym visual — NOT MIT; served from the upstream repository via jsDelivr",
        },
        "facets": facets,
        "exercises": exercises,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help=f"clone of the upstream dataset (default: {DEFAULT_SOURCE})")
    ap.add_argument("--update", action="store_true",
                    help="git pull the upstream clone before building")
    ap.add_argument("--langs", default=",".join(DEFAULT_LANGS),
                    help="comma-separated instruction languages, first one is the default "
                         f"(default: {','.join(DEFAULT_LANGS)})")
    args = ap.parse_args()

    langs = tuple(x.strip() for x in args.langs.split(",") if x.strip())
    if not langs:
        raise SystemExit("--langs cannot be empty")

    source = ensure_source(args.source, args.update)
    payload = build(source, langs)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    size = OUT_FILE.stat().st_size
    print(f"{OUT_FILE.relative_to(REPO)}: {payload['count']} exercises, "
          f"{size / 1e6:.2f} MB (languages: {','.join(langs)}, "
          f"upstream {payload['upstream']['commit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
