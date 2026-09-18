#!/usr/bin/env python3
"""Generate the A2 plain-English `explain:` annotations with a local Qwen model.

This is the text-processing step of the episode pipeline. It replaces the
previous manual pass, where the explanations in
`tools/a2_chunks/results/*.json` were written by hand / by subagents.

Flow (unchanged around this script):

    tools/flag_a2.py        flags sentences beyond CEFR A2 and writes
                            tools/a2_chunks/<slug>_cNN.json
    tools/qwen_explain.py   THIS SCRIPT: asks the local Qwen server for one
                            explanation per sentence and writes
                            tools/a2_chunks/results/<slug>_cNN.json
    tools/merge_explain.py  merges those into the episode frontmatter

The output format is exactly what merge_explain.py expects: a JSON array of
`{"id": <sentence id>, "explain": "<text>"}`, ids matching the chunk file.

The prompt is anchored with real examples taken from already-published
episodes so the generated notes keep the site's existing voice.

Usage:
    ./venv/bin/python tools/qwen_explain.py                  # all pending chunks
    ./venv/bin/python tools/qwen_explain.py --limit 2 --dry-run
    ./venv/bin/python tools/qwen_explain.py --slug 2026-09-18-did-the-us-carry-out-war-crimes-in-iran

Exit codes: 0 = ok, 1 = some chunk failed, 2 = usage/connection error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
CHUNKS = TOOLS / "a2_chunks"
RESULTS = CHUNKS / "results"
DEFAULT_ENDPOINT = "http://127.0.0.1:30000/v1/chat/completions"
DEFAULT_MODEL = "Qwen3.8-27B-FP8"
API_KEY_FILE = Path.home() / ".sglang_api_key"

SYSTEM_PROMPT = """\
You write very simple English notes that help CEFR A2 learners understand a \
BBC podcast transcript.

For every sentence you are given, pick out only the words or phrases that are \
too hard for an A2 learner, and explain them in plain English. Use this shape:

1. One or two explanations of the form: "TERM" means PLAIN ENGLISH.
   Put the hard word or phrase in double quotes.
2. Then one short sentence saying what the whole sentence means, in easier words.

Rules:
- Write for people with basic English. Short sentences. Common words only.
- Never use a hard word to explain another hard word.
- Every explanation sentence must open with the hard term in double quotes; only
  a short article such as "A" or "The" may come before it. For example:
  A "settler" is a person who builds a home in an area belonging to another group.
- Explain only what is genuinely hard. Skip easy words. Two or three notes is
  plenty; do not list every word.
- The text is an automatic transcript, so it may contain odd spacing such as
  "o 'clock" or "women -free zone". If that matters, say briefly that the note
  is split by a space.
- If the sentence is a fragment, or is cut off and continues in the next
  sentence, say so plainly.
- If the sentence is a station ident, an advert or a trailer, say that it is.
- Never mention that you are an AI and never add extra commentary.

Return ONLY a JSON array, with one object per input sentence, in the same order:
[{"id": <the id you were given>, "explain": "<your note>"}]
No markdown fences, no text before or after the array.

Two real published examples of the house style:

Input:
[{"id": 15, "text": "Our correspondent in Nablus has"}, {"id": 10, "text": "And the baby is as well"}]

Output:
[{"id": 15, "explain": "A \\"correspondent\\" is a reporter who reports news from a particular place. \\"Nablus\\" is a city in the West Bank. The presenter says the details will come soon, but first takes you to a village south of Nablus. The sentence breaks off at \\"has\\" and continues in the next one."}, {"id": 10, "explain": "\\"As well\\" means also, too. This short sentence says that the baby is actually with the parents too, at the place where this part of the show is being recorded."}]
"""

_thread_local = threading.local()


def _opener() -> urllib.request.OpenerDirector:
    """One opener per thread so proxy env changes cannot leak across threads."""
    if not hasattr(_thread_local, "opener"):
        _thread_local.opener = urllib.request.build_opener()
    return _thread_local.opener


def api_key() -> str:
    key = os.environ.get("QWEN_API_KEY", "").strip()
    if key:
        return key
    try:
        return API_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def chat(messages: list[dict], *, endpoint: str, model: str, key: str,
         max_tokens: int, timeout: int, temperature: float = 0.3) -> str:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        # Qwen3 emits its reasoning inline unless thinking is switched off.
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(endpoint, data=body, headers=headers)
    with _opener().open(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


_JSON_ARRAY = re.compile(r"\[.*\]", re.S)


def parse_explanations(text: str) -> list[dict]:
    """Pull the JSON array out of a model reply, tolerating fences and prose."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    m = _JSON_ARRAY.search(t)
    if not m:
        raise ValueError(f"no JSON array in reply: {text[:200]!r}")
    raw = m.group(0)
    try:
        parsed = json.loads(raw)
    except ValueError:
        # trailing commas before ] or } are the usual single failure
        repaired = re.sub(r",(\s*[\]}])", r"\1", raw)
        parsed = json.loads(repaired)
    if not isinstance(parsed, list):
        raise ValueError("reply JSON is not an array")
    out = []
    for item in parsed:
        if not isinstance(item, dict) or "id" not in item:
            continue
        explain = str(item.get("explain", "")).strip()
        if explain:
            out.append({"id": int(item["id"]), "explain": explain})
    if not out:
        raise ValueError("reply array held no usable explanations")
    return out


def explain_batch(sentences: list[dict], meta: dict, *, endpoint: str, model: str,
                  key: str, timeout: int, retries: int = 3) -> dict[int, str]:
    """Explanations for one batch of sentences; missing ids are retried alone."""
    context = (f"Episode: {meta.get('title', '')}\n"
               f"Show: {meta.get('show', '')}   Date: {meta.get('date', '')}")
    user = (context + "\n\nExplain these transcript sentences:\n"
            + json.dumps([{"id": s["id"], "text": s["text"]} for s in sentences],
                         ensure_ascii=False))
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user}]

    # ~90 tokens of note per sentence, with headroom.
    max_tokens = min(8192, 200 + 110 * len(sentences))
    got: dict[int, str] = {}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            reply = chat(messages, endpoint=endpoint, model=model, key=key,
                         max_tokens=max_tokens, timeout=timeout)
            for item in parse_explanations(reply):
                got[item["id"]] = item["explain"]
            if all(s["id"] in got for s in sentences):
                return got
            last = ValueError("reply omitted some ids")
            break
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < retries:
                continue

    # Fall back to one sentence per request for whatever is still missing.
    for s in sentences:
        if s["id"] in got:
            continue
        try:
            reply = chat([{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content":
                           context + "\n\nExplain this transcript sentence:\n"
                           + json.dumps([{"id": s["id"], "text": s["text"]}],
                                        ensure_ascii=False)}],
                         endpoint=endpoint, model=model, key=key,
                         max_tokens=600, timeout=timeout)
            for item in parse_explanations(reply):
                if item["id"] == s["id"]:
                    got[s["id"]] = item["explain"]
        except Exception as exc:  # keep going; report at the end
            last = exc
    if not got and last:
        raise last
    return got


def process_chunk(path: Path, args) -> tuple[str, int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sentences = payload.get("sentences") or []
    meta = {k: payload.get(k, "") for k in ("episode", "title", "show", "date")}
    out_path = RESULTS / path.name
    if out_path.exists() and not args.force:
        return f"skip (exists) {path.name}", 0, 0

    got: dict[int, str] = {}
    batch = max(1, args.batch)
    for start in range(0, len(sentences), batch):
        part = sentences[start:start + batch]
        got.update(explain_batch(part, meta, endpoint=args.endpoint,
                                 model=args.model, key=args.key,
                                 timeout=args.timeout))
    ordered = [{"id": s["id"], "explain": got[s["id"]]}
               for s in sentences if s["id"] in got]
    if not ordered:
        raise RuntimeError("no explanations produced")
    if args.dry_run:
        return f"dry-run {path.name}: {len(ordered)}/{len(sentences)}", 0, 0
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return (f"wrote {out_path.name}: {len(ordered)}/{len(sentences)} notes",
            len(ordered), len(sentences))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default=os.environ.get("QWEN_ENDPOINT",
                                                         DEFAULT_ENDPOINT))
    ap.add_argument("--model", default=os.environ.get("QWEN_MODEL", DEFAULT_MODEL))
    ap.add_argument("--batch", type=int, default=8,
                    help="sentences per request (default 8)")
    ap.add_argument("--workers", type=int, default=4,
                    help="chunks processed in parallel (default 4)")
    ap.add_argument("--timeout", type=int, default=600, help="per-request timeout")
    ap.add_argument("--slug", default=None, help="only this episode slug")
    ap.add_argument("--limit", type=int, default=0, help="at most N chunks (0 = all)")
    ap.add_argument("--force", action="store_true", help="regenerate existing results")
    ap.add_argument("--dry-run", action="store_true", help="do not write results")
    args = ap.parse_args()
    args.key = api_key()

    chunks = sorted(p for p in CHUNKS.glob("*.json") if p.name != "manifest.json")
    if args.slug:
        chunks = [p for p in chunks if p.name.startswith(args.slug + "_")]
    if args.limit:
        chunks = chunks[:args.limit]
    if not chunks:
        print("no chunk files to process")
        return 0

    if not args.dry_run:
        try:
            chat([{"role": "user", "content": "hi"}], endpoint=args.endpoint,
                 model=args.model, key=args.key, max_tokens=8, timeout=60)
        except Exception as exc:
            print(f"cannot reach Qwen at {args.endpoint}: {exc}", file=sys.stderr)
            return 2

    print(f"{len(chunks)} chunk(s) · model {args.model} · batch {args.batch} "
          f"· workers {args.workers}")
    failures = 0
    done_notes = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for msg, n_ok, n_tot in pool.map(lambda p: _safe(p, args), chunks):
            if msg.startswith("!"):
                failures += 1
            done_notes += n_ok
            print("  " + msg, flush=True)
    print(f"total: {done_notes} notes · {failures} failed chunk(s)")
    return 1 if failures else 0


def _safe(path: Path, args) -> tuple[str, int, int]:
    try:
        return process_chunk(path, args)
    except Exception as exc:
        return f"! {path.name}: {type(exc).__name__}: {exc}", 0, 0


if __name__ == "__main__":
    sys.exit(main())
