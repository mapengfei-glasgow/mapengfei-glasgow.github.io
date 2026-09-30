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
`{"id": <sentence id>, "explain": "<English note>", "zh": "<Chinese note>"}`,
ids matching the chunk file. `zh` is the same sentence rendered for a Chinese
learner — a natural Simplified-Chinese translation followed by the Chinese
meanings of the hard terms in full-width parentheses. A sentence counts as done
only when both languages came back, so a reply that drops the Chinese is retried
rather than published as English-only.

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

import yaml

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
CHUNKS = TOOLS / "a2_chunks"
RESULTS = CHUNKS / "results"
CONTENT = REPO / "english-site" / "content" / "episodes"
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

You ALSO write a Chinese note for the same sentence, for the same learner:

1. Translate the whole sentence into natural spoken Simplified Chinese, the way a
   Chinese news podcast would phrase it. Translate the meaning, not word for word.
2. Then add one pair of full-width parentheses listing the hard terms you chose:
   （term 中文；term2 中文2）
   Keep each English term as written in the sentence, give a short Chinese
   meaning, separate the pairs with a full-width semicolon. At most three terms.
   If the sentence has no hard term at all, omit the parentheses.

Rules for the Chinese note:
- Simplified Chinese only, one single line (no newlines).
- Keep people, place and organisation names in their usual Chinese form; leave
  BBC, NATO and similar as they are rather than inventing a translation.
- The transcript may be broken or oddly spaced; translate the intended meaning.
  For a cut-off fragment, end with …… to show it continues.
- No grammar talk, no commentary, and never mention being an AI.

Return ONLY a JSON array, with one object per input sentence, in the same order:
[{"id": <id>, "explain": "<English note>", "zh": "<Chinese note>"}]
No markdown fences, no text before or after the array.

Two real published examples of the house style:

Input:
[{"id": 15, "text": "Our correspondent in Nablus has"}, {"id": 10, "text": "And the baby is as well"}]

Output:
[{"id": 15, "explain": "A \\"correspondent\\" is a reporter who reports news from a particular place. \\"Nablus\\" is a city in the West Bank. The presenter says the details will come soon, but first takes you to a village south of Nablus. The sentence breaks off at \\"has\\" and continues in the next one.", "zh": "我们驻纳布卢斯的记者……（correspondent 记者；Nablus 纳布卢斯，约旦河西岸城市）"}, {"id": 10, "explain": "\\"As well\\" means also, too. This short sentence says that the baby is actually with the parents too, at the place where this part of the show is being recorded.", "zh": "宝宝也在场。（as well 也，同样）"}]
"""

SYSTEM_PROMPT_ZH = """\
You write the Chinese note that helps a Chinese learner of English follow a BBC
podcast transcript. You are given English sentences from an automatic
transcript; return a Chinese note for each one.

The note has two parts, on one single line:
1. The whole sentence translated into natural spoken Simplified Chinese, phrased
   the way a Chinese news podcast would say it. Translate the meaning, not word
   for word.
2. Then one pair of full-width parentheses listing the terms that are hard for a
   learner: （term 中文；term2 中文2）
   Keep each English term as written in the sentence, give a short Chinese
   meaning, and separate the pairs with a full-width semicolon. At most three
   terms. If nothing in the sentence is hard, omit the parentheses.

Rules:
- Simplified Chinese only, one single line, no newlines.
- Keep people, place and organisation names in their usual Chinese form; leave
  BBC, NATO and similar as they are rather than inventing a translation.
- The transcript may be broken or oddly spaced ("o 'clock", "women -free zone").
  Translate the intended meaning; never comment on the spacing.
- For a cut-off fragment, end with …… to show it continues in the next sentence.
- For a station ident, an advert or a trailer, just translate it plainly.
- No grammar talk, no commentary, and never mention being an AI.

Return ONLY a JSON array, with one object per input sentence, in the same order:
[{"id": <id>, "zh": "<Chinese note>"}]
No markdown fences, no text before or after the array.

Example:

Input:
[{"id": 15, "text": "Our correspondent in Nablus has"}, {"id": 10, "text": "And the baby is as well"}]

Output:
[{"id": 15, "zh": "我们驻纳布卢斯的记者……（correspondent 记者；Nablus 纳布卢斯，约旦河西岸城市）"}, {"id": 10, "zh": "宝宝也在场。（as well 也，同样）"}]
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
        zh = " ".join(str(item.get("zh", "")).split())
        if explain or zh:          # zh-only replies carry no "explain"
            out.append({"id": int(item["id"]), "explain": explain, "zh": zh})
    if not out:
        raise ValueError("reply array held no usable notes")
    return out


def explain_batch(sentences: list[dict], meta: dict, *, endpoint: str, model: str,
                  key: str, timeout: int, retries: int = 3,
                  zh_only: bool = False) -> dict[int, dict]:
    """Notes for one batch; ids missing a language are retried alone.

    Returns {id: {"explain": ..., "zh": ...}}. In the default (both) mode a
    sentence counts as done only when both languages came back, so a reply that
    quietly drops the Chinese is retried rather than published as English-only.
    With zh_only=True the 💡 English notes are left untouched and only the
    Chinese is requested — that is how the already-published notes were kept
    while Chinese was added.
    """
    system = SYSTEM_PROMPT_ZH if zh_only else SYSTEM_PROMPT
    context = (f"Episode: {meta.get('title', '')}\n"
               f"Show: {meta.get('show', '')}   Date: {meta.get('date', '')}")
    user = (context + "\n\nExplain these transcript sentences:\n"
            + json.dumps([{"id": s["id"], "text": s["text"]} for s in sentences],
                         ensure_ascii=False))
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]

    # Chinese needs ~80 tokens a sentence; the English note ~90 on top of that.
    per_sentence = 130 if zh_only else 210
    max_tokens = min(16384, 300 + per_sentence * len(sentences))
    got: dict[int, dict] = {}

    def complete() -> bool:
        for s in sentences:
            g = got.get(s["id"], {})
            if not g.get("zh"):
                return False
            if not zh_only and not g.get("explain"):
                return False
        return True

    last: Exception | None = None
    for attempt in range(retries):
        try:
            reply = chat(messages, endpoint=endpoint, model=model, key=key,
                         max_tokens=max_tokens, timeout=timeout)
            for item in parse_explanations(reply):
                cur = got.setdefault(item["id"], {})
                if item["explain"]:
                    cur["explain"] = item["explain"]
                if item["zh"]:
                    cur["zh"] = item["zh"]
            if complete():
                return got
            last = ValueError("reply omitted some ids or Chinese notes")
            break
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < retries:
                continue

    # Fall back to one sentence per request for whatever is still incomplete.
    for s in sentences:
        have = got.get(s["id"], {})
        if have.get("zh") and (zh_only or have.get("explain")):
            continue
        try:
            reply = chat([{"role": "system", "content": system},
                          {"role": "user", "content":
                           context + "\n\nExplain this transcript sentence:\n"
                           + json.dumps([{"id": s["id"], "text": s["text"]}],
                                        ensure_ascii=False)}],
                         endpoint=endpoint, model=model, key=key,
                         max_tokens=1200, timeout=timeout)
            for item in parse_explanations(reply):
                if item["id"] == s["id"]:
                    cur = got.setdefault(item["id"], {})
                    if item["explain"]:
                        cur["explain"] = item["explain"]
                    if item["zh"]:
                        cur["zh"] = item["zh"]
        except Exception as exc:  # keep going; report at the end
            last = exc
    if not got and last:
        raise last
    return got


def process_episode_zh(md: Path, args) -> tuple[str, int, int]:
    """Chinese note for EVERY sentence of one episode -> results/<slug>_zh.json.

    The A2 chunks only carry sentences that contain something beyond A2, so a
    translation built from them has holes: ordinary sentences such as "It's a
    huge deal in and of itself." are never flagged, yet a reader following along
    still needs them translated. This pass therefore walks the episode
    frontmatter directly and covers every sentence.
    """
    slug = md.stem
    fm = yaml.safe_load(md.read_text(encoding="utf-8").split("---\n", 2)[1]) or {}
    sentences = fm.get("sentences") or []
    out_path = RESULTS / f"{slug}_zh.json"
    if not sentences:
        return f"skip (no sentences) {slug}", 0, 0

    existing: dict[int, str] = {}
    if out_path.exists():
        try:
            existing = {int(e["id"]): e["zh"]
                        for e in json.loads(out_path.read_text(encoding="utf-8"))
                        if e.get("zh")}
        except (OSError, ValueError, KeyError, TypeError):
            existing = {}

    todo = [{"id": i, "text": s["text"]}
            for i, s in enumerate(sentences) if i not in existing]
    if not todo and not args.force:
        return f"skip (zh done) {slug}", 0, 0
    if args.force:
        todo = [{"id": i, "text": s["text"]} for i, s in enumerate(sentences)]

    meta = {"title": fm.get("title", ""), "show": fm.get("show", ""),
            "date": str(fm.get("date", ""))[:10]}
    got: dict[int, dict] = {}
    batch = max(1, args.batch)
    for start in range(0, len(todo), batch):
        part = todo[start:start + batch]
        got.update(explain_batch(part, meta, endpoint=args.endpoint,
                                 model=args.model, key=args.key,
                                 timeout=args.timeout, zh_only=True))

    zh = dict(existing)
    for item in todo:
        z = got.get(item["id"], {}).get("zh")
        if z:
            zh[item["id"]] = z
    if args.dry_run:
        return (f"dry-run {slug}: {len(zh)}/{len(sentences)} sentences"), 0, 0
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = [{"id": i, "zh": zh[i]} for i in sorted(zh)]
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    missing = len(sentences) - len(zh)
    msg = f"wrote {out_path.name}: {len(zh)}/{len(sentences)} sentences"
    if missing:
        msg += f" — {missing} WITHOUT zh"
    return msg, len(zh), len(sentences)


def process_chunk(path: Path, args) -> tuple[str, int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sentences = payload.get("sentences") or []
    meta = {k: payload.get(k, "") for k in ("episode", "title", "show", "date")}
    out_path = RESULTS / path.name

    existing: dict[int, dict] = {}
    if out_path.exists():
        try:
            existing = {int(e["id"]): e
                        for e in json.loads(out_path.read_text(encoding="utf-8"))}
        except (OSError, ValueError, KeyError, TypeError):
            existing = {}

    if out_path.exists() and not args.force:
        if not args.zh_only:
            return f"skip (exists) {path.name}", 0, 0
        if all(existing.get(s["id"], {}).get("zh") for s in sentences):
            return f"skip (zh done) {path.name}", 0, 0

    got: dict[int, dict] = {}
    batch = max(1, args.batch)
    for start in range(0, len(sentences), batch):
        part = sentences[start:start + batch]
        got.update(explain_batch(part, meta, endpoint=args.endpoint,
                                 model=args.model, key=args.key,
                                 timeout=args.timeout, zh_only=args.zh_only))

    # Anything the run did not produce falls back to what the chunk already had,
    # so `--zh-only` adds Chinese without dropping the published English notes.
    ordered, no_zh = [], 0
    for s in sentences:
        g = got.get(s["id"], {})
        prev = existing.get(s["id"], {})
        explain = g.get("explain") or prev.get("explain")
        zh = g.get("zh") or prev.get("zh")
        if not explain and not zh:
            continue
        entry = {"id": s["id"]}
        if explain:
            entry["explain"] = explain
        if zh:
            entry["zh"] = zh
        else:
            no_zh += 1
        ordered.append(entry)
    if not ordered:
        raise RuntimeError("no explanations produced")
    if args.dry_run:
        note = f"dry-run {path.name}: {len(ordered)}/{len(sentences)}"
        return (note + (f" ({no_zh} missing zh)" if no_zh else "")), 0, 0
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    msg = f"wrote {out_path.name}: {len(ordered)}/{len(sentences)} notes"
    if no_zh:
        msg += f" — {no_zh} WITHOUT zh"
    return msg, len(ordered), len(sentences)


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
    ap.add_argument("--zh-only", dest="zh_only", action="store_true",
                    help="only write the Chinese notes, keeping the existing "
                         "💡 English ones (used to add Chinese to episodes that "
                         "were published before it existed)")
    ap.add_argument("--all-sentences", dest="all_sentences", action="store_true",
                    help="translate EVERY sentence of each episode into "
                         "results/<slug>_zh.json instead of working from the A2 "
                         "chunks (which only hold sentences that contain "
                         "something beyond A2, leaving holes in the Chinese)")
    ap.add_argument("--dry-run", action="store_true", help="do not write results")
    args = ap.parse_args()
    args.key = api_key()

    if args.all_sentences:
        episodes = sorted(p for p in CONTENT.glob("*.md") if p.name != "_index.md")
        if args.slug:
            episodes = [p for p in episodes if p.stem == args.slug]
        if not episodes:
            print("no episode pages to translate")
            return 0
        if not args.dry_run:
            try:
                chat([{"role": "user", "content": "hi"}], endpoint=args.endpoint,
                     model=args.model, key=args.key, max_tokens=8, timeout=60)
            except Exception as exc:
                print(f"cannot reach Qwen at {args.endpoint}: {exc}", file=sys.stderr)
                return 2
        print(f"{len(episodes)} episode(s) · every sentence · model {args.model} "
              f"· batch {args.batch} · workers {args.workers}")
        failures = done = 0
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for msg, n_ok, _ in pool.map(lambda p: _safe_ep(p, args), episodes):
                if msg.startswith("!"):
                    failures += 1
                done += n_ok
                print("  " + msg, flush=True)
        print(f"total: {done} sentences translated · {failures} failed episode(s)")
        return 1 if failures else 0

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


def _safe_ep(path: Path, args) -> tuple[str, int, int]:
    try:
        return process_episode_zh(path, args)
    except Exception as exc:
        return f"! {path.name}: {type(exc).__name__}: {exc}", 0, 0


if __name__ == "__main__":
    sys.exit(main())
