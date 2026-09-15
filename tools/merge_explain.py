#!/usr/bin/env python3
"""Merge A2 plain-English explanations into episode frontmatter.

Reads tools/a2_chunks/results/<slug>_cNN.json (arrays of {"id", "explain"})
and inserts  , explain: "..."  into the matching sentence line of each
episode's YAML frontmatter. Sentence lines are processed in file order, so
the line position equals the sentence index used in the chunk files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "english-site" / "content" / "episodes"
RESULTS = Path(__file__).resolve().parent / "a2_chunks" / "results"
# Sentence lines (current single-stream format, no per-sentence file field);
# an existing explain field is matched (and replaced) so re-merges are safe.
# text/explain are proper YAML double-quoted scalars, so values containing
# escaped quotes (\" ) still match — without this, re-merges would skip those
# lines and the sentence index would drift.
_QUOTED = r'"(?:[^"\\]|\\.)*"'
LINE = re.compile(
    r'^  - \{text: (' + _QUOTED + r'), start: ([0-9.]+), end: ([0-9.]+)'
    r'(?:, explain: (?:' + _QUOTED + r'))?\}\s*$')


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    total = 0
    for md in sorted(CONTENT.glob("*.md")):
        slug = md.stem
        expl: dict[int, str] = {}
        for rf in sorted(RESULTS.glob(f"{slug}_c*.json")):
            for e in json.load(open(rf, encoding="utf-8")):
                expl[int(e["id"])] = e["explain"].strip()
        if not expl:
            print(f"{slug}: no explanation results yet, skipping")
            continue
        lines = md.read_text(encoding="utf-8").splitlines(keepends=True)
        if not lines[0].startswith("---"):
            print(f"{slug}: no frontmatter, skipping")
            continue
        end = lines.index("---\n", 1)
        out, i, n = [], 0, 0
        for idx, ln in enumerate(lines):
            if 0 < idx < end:
                m = LINE.match(ln.rstrip("\n"))
                if m:
                    if i in expl:
                        ln = (f'  - {{text: {m.group(1)}, start: {m.group(2)}, '
                              f'end: {m.group(3)}, explain: "{esc(expl[i])}"}}\n')
                        n += 1
                    i += 1
            out.append(ln)
        fm_text = "".join(out).split("---\n", 2)[1]
        fm = yaml.safe_load(fm_text)  # validate before writing
        ne = sum(1 for s in fm["sentences"] if s.get("explain"))
        assert ne == n, f"{slug}: wrote {n}, yaml sees {ne}"
        md.write_text("".join(out), encoding="utf-8")
        total += n
        print(f"{slug}: {n}/{len(fm['sentences'])} sentences with explain")
    print(f"total: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
