#!/usr/bin/env python3
"""Write the edited plain-text copy back into the episode's sentences.

`content/edit/<name>.md` holds the transcript one sentence per line, so line N
is sentence N. That makes it pleasant to correct in an editor, but the site
renders the copy that lives in `content/episodes/<slug>.md`'s front matter, so
the text has to be written back here.

Only the `text:` value is replaced. `start`, `end`, `explain` and `zh` are left
untouched, which is what keeps the timestamps and the notes aligned.

The line count and the sentence count must match exactly. If they do not, the
mapping is wrong for every sentence after the first difference, so this refuses
to write anything and says so — a silent misalignment would be far worse than a
failed run.

Usage:
    ./venv/bin/python tools/apply_transcript.py --dry-run    # show what would change
    ./venv/bin/python tools/apply_transcript.py              # write it back
    ./venv/bin/python tools/apply_transcript.py --slug why-science-needs-storytellers
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "english-site"
CONTENT = SITE / "content"
EDITS = CONTENT / "edit"

_QUOTED = r'"(?:[^"\\]|\\.)*"'
LINE = re.compile(
    r'^  - \{text: (' + _QUOTED + r'), start: ([0-9.]+), end: ([0-9.]+)'
    r'(?:, explain: (' + _QUOTED + r'))?'
    r'(?:, zh: (' + _QUOTED + r'))?\}\s*$')


def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter body without the --- fences, rest of the file)."""
    if not text.startswith("---"):
        raise SystemExit("no frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise SystemExit("malformed frontmatter")
    return parts[1], parts[2]


def edit_sources() -> list[Path]:
    return sorted(p for p in EDITS.glob("*.md") if p.name != "_index.md")


def sync(copy: Path, dry_run: bool) -> int:
    fm_text, body = split_frontmatter(copy.read_text(encoding="utf-8"))
    fm = yaml.safe_load(fm_text) or {}
    original = fm.get("original")
    if not original:
        print(f"{copy.name}: no `original:` in the frontmatter, skipped")
        return 0

    page = CONTENT / original
    if not page.exists():
        raise SystemExit(f"{copy.name}: original page not found: {page}")

    lines = [ln.rstrip("\r") for ln in body.rstrip("\n").split("\n")]
    page_text = page.read_text(encoding="utf-8")
    page_fm, _ = split_frontmatter(page_text)
    sentences = (yaml.safe_load(page_fm) or {}).get("sentences") or []

    if len(lines) != len(sentences):
        print(f"{copy.name}: {len(lines)} text lines vs {len(sentences)} sentences "
              f"in {page.name}")
        print("  REFUSING: line N would no longer mean sentence N. "
              "Fix the line count in the copy first.")
        return 1

    out, i, changed = [], 0, 0
    for ln in page_text.splitlines(keepends=True):
        m = LINE.match(ln.rstrip("\n"))
        if m:
            new_text = lines[i].strip()
            if new_text != json.loads(m.group(1)):
                changed += 1
                if dry_run or changed <= 20:
                    print(f"  line {i + 1}:")
                    print(f"    - {json.loads(m.group(1))[:110]}")
                    print(f"    + {new_text[:110]}")
                rebuilt = f'  - {{text: {json.dumps(new_text, ensure_ascii=False)}, ' \
                          f'start: {m.group(2)}, end: {m.group(3)}'
                if m.group(4):
                    rebuilt += f", explain: {m.group(4)}"
                if m.group(5):
                    rebuilt += f", zh: {m.group(5)}"
                rebuilt += "}\n"
                ln = rebuilt
            i += 1
        out.append(ln)

    if i != len(sentences):
        raise SystemExit(f"{copy.name}: parsed {i} sentence lines, expected {len(sentences)}")
    if not changed:
        print(f"{copy.name}: nothing to sync ({len(lines)} sentences identical)")
        return 0

    text = "".join(out)
    yaml.safe_load(split_frontmatter(text)[0])  # validate before writing
    if dry_run:
        print(f"{copy.name}: would change {changed} of {len(lines)} sentences (dry run)")
        return 0
    page.write_text(text, encoding="utf-8")
    print(f"{copy.name}: wrote {changed} of {len(lines)} sentences into {page.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", default=None, help="only this copy (file stem)")
    ap.add_argument("--dry-run", action="store_true", help="show, do not write")
    args = ap.parse_args()

    copies = edit_sources()
    if args.slug:
        copies = [p for p in copies if p.stem == args.slug]
    if not copies:
        print("no editable copies in content/edit/ (or none matched --slug)")
        return 0

    rc = 0
    for c in copies:
        print(f"=== {c.name}")
        rc |= sync(c, args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
