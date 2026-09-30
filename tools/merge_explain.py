#!/usr/bin/env python3
"""Merge the learner notes into episode frontmatter.

Reads tools/a2_chunks/results/<slug>_cNN.json — arrays of
`{"id", "explain", "zh"}` — and inserts the fields into the matching sentence
line of each episode's YAML frontmatter, in this order:

    - {text: "...", start: 1.23, end: 4.56, explain: "...", zh: "..."}

Sentence lines are processed in file order, so the line position equals the
sentence index used in the chunk files.

Re-merging is safe and *additive per field*: a field the results do not carry
(for example when only the Chinese notes were regenerated) keeps whatever the
line already had, and neither field is ever dropped by adding the other.
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
# existing explain/zh fields are matched (and replaced) so re-merges are safe.
# text/explain/zh are proper YAML double-quoted scalars, so values containing
# escaped quotes (\" ) still match — without this, re-merges would skip those
# lines and the sentence index would drift.
_QUOTED = r'"(?:[^"\\]|\\.)*"'
LINE = re.compile(
    r'^  - \{text: (' + _QUOTED + r'), start: ([0-9.]+), end: ([0-9.]+)'
    r'(?:, explain: (' + _QUOTED + r'))?'
    r'(?:, zh: (' + _QUOTED + r'))?\}\s*$')

_FIELDS = ("explain", "zh")


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def load_results(slug: str) -> dict[int, dict[str, str]]:
    """{sentence id: {field: text}} from every result file of one episode.

    Two kinds of file feed this:
      * <slug>_cNN.json — the A2 pass, carrying `explain` for the sentences that
        contain something beyond A2;
      * <slug>_zh.json  — the full-translation pass, carrying `zh` for every
        sentence in the episode.
    Globbing with a sort puts `_zh.json` last (c < z), so when both happen to
    carry Chinese for the same sentence the full-translation wording wins.
    """
    merged: dict[int, dict[str, str]] = {}
    for rf in sorted(RESULTS.glob(f"{slug}_*.json")):
        try:
            entries = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"  ! unreadable result file, skipped: {rf.name}")
            continue
        for e in entries:
            entry = {f: str(e[f]).strip() for f in _FIELDS if e.get(f)}
            if entry:
                merged.setdefault(int(e["id"]), {}).update(entry)
    return merged


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    totals = {f: 0 for f in _FIELDS}
    rewritten = 0

    for md in sorted(CONTENT.glob("*.md")):
        slug = md.stem
        if only and slug != only:
            continue
        notes = load_results(slug)
        if not notes:
            print(f"{slug}: no results yet, skipping")
            continue
        lines = md.read_text(encoding="utf-8").splitlines(keepends=True)
        if not lines[0].startswith("---"):
            print(f"{slug}: no frontmatter, skipping")
            continue

        end = lines.index("---\n", 1)
        out, i, changed = [], 0, False
        for idx, ln in enumerate(lines):
            if 0 < idx < end:
                m = LINE.match(ln.rstrip("\n"))
                if m:
                    text, start, stop = m.group(1), m.group(2), m.group(3)
                    current = {"explain": m.group(4), "zh": m.group(5)}
                    values = {}
                    for f in _FIELDS:
                        # Prefer a new value; otherwise keep what the line has.
                        new = notes.get(i, {}).get(f)
                        values[f] = f'"{esc(new)}"' if new else current[f]
                    rebuilt = (f'  - {{text: {text}, start: {start}, end: {stop}'
                               + "".join(f', {f}: {values[f]}'
                                         for f in _FIELDS if values[f])
                               + "}\n")
                    if rebuilt != ln:
                        changed = True
                    ln = rebuilt
                    i += 1
            out.append(ln)

        fm_text = "".join(out).split("---\n", 2)[1]
        fm = yaml.safe_load(fm_text)  # validate before writing
        seen = {f: sum(1 for s in fm["sentences"] if s.get(f)) for f in _FIELDS}
        for f in _FIELDS:
            totals[f] += seen[f]
        assert seen["explain"] == sum(
            1 for s in fm["sentences"] if s.get("explain")), slug
        if changed:
            md.write_text("".join(out), encoding="utf-8")
            rewritten += 1
        print(f"{slug}: {seen['explain']}/{len(fm['sentences'])} explain, "
              f"{seen['zh']}/{len(fm['sentences'])} zh"
              + ("" if changed else "  (unchanged)"))

    print(f"files rewritten: {rewritten}")
    print("total: " + ", ".join(f"{f}={totals[f]}" for f in _FIELDS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
