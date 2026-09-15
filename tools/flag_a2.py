#!/usr/bin/env python3
"""Flag sentences likely beyond CEFR A2 and export chunks for
plain-English explanation (subagents write the explanations).

A sentence is a candidate when it contains at least one
  * dictionary word whose own entry or any reduced base form ranks beyond
    A2_RANK in the BNC and has no oxford core-list flag, or
  * lowercase word absent from the dictionary, length >= 4, not blocklisted, or
  * a known set phrase from tools/phrase_notes.tsv.
Capitalized tokens (proper nouns) never flag a sentence by themselves.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_episode import BLOCKLIST, _variants, load_dict, load_phrases  # noqa: E402

A2_RANK = 2000      # BNC rank above this counts as beyond A2
MIN_UNKNOWN_LEN = 4
CHUNK = 55
REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "english-site" / "content" / "episodes"
OUT = Path(__file__).resolve().parent / "a2_chunks"


def sentence_flagged(text: str, d: dict, phrase_set: frozenset[str]) -> bool:
    low = text.lower().replace(" -", "-")
    for ph in phrase_set:
        if ph in low:
            return True
    for tok in re.findall(r"[A-Za-z][A-Za-z']*", text):
        if tok[0].isupper():
            continue
        t = tok.lower()
        if t in BLOCKLIST:
            continue
        for w in (t, *_variants(t, d)):
            e = d.get(w)
            if not e:
                continue
            if e[3]:            # oxford core list -> core vocabulary
                break
            if e[2] and e[2] > A2_RANK:
                return True
            if e[2]:            # ranked within A2 range -> fine
                break
        if t not in d and len(t) >= MIN_UNKNOWN_LEN:
            return True
    return False


def main() -> int:
    d = load_dict()
    phrases = load_phrases()
    phrase_set = frozenset(p.strip() for p, _ in phrases)
    OUT.mkdir(parents=True, exist_ok=True)

    manifest = []
    for md in sorted(CONTENT.glob("*.md")):
        fm = yaml.safe_load(md.read_text(encoding="utf-8").split("---\n", 2)[1])
        if not fm or not fm.get("sentences"):
            continue  # e.g. _index.md (section index, no sentences)
        slugs = [s for s in fm["sentences"]]
        flagged = [
            {"id": i, "text": s["text"]}
            for i, s in enumerate(slugs)
            if sentence_flagged(s["text"], d, phrase_set)
        ]
        meta = {"episode": md.stem, "title": str(fm["title"]),
                "show": str(fm.get("show", "")),
                "date": str(fm.get("date", ""))[:10]}
        n_chunks = 0
        for start in range(0, len(flagged), CHUNK):
            part = flagged[start:start + CHUNK]
            n_chunks += 1
            path = OUT / f"{md.stem}_c{n_chunks:02d}.json"
            payload = dict(meta, sentences=part)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                            encoding="utf-8")
            manifest.append({"file": str(path), "episode": md.stem,
                             "from": part[0]["id"], "to": part[-1]["id"],
                             "n": len(part)})
        print(f"{md.stem}: {len(flagged)}/{len(slugs)} sentences flagged "
              f"-> {n_chunks} chunk(s)")
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total chunks: {len(manifest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
