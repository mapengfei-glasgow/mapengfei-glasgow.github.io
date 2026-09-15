#!/usr/bin/env python3
"""Create a Hugo episode page (with per-sentence audio) from a podcast MP3.

Pipeline:
  1. Transcribe the audio with faster-whisper (word-level timestamps).
  2. Group words into sentences.
  3. Copy the full episode MP3 (one continuous stream; the player seeks
     by timestamp instead of playing per-sentence clips).
  4. Write a Hugo content file whose frontmatter lists every sentence
     with its start/end timestamps.

Usage:
  make_episode.py MP3_FILE --show "Global News Podcast" \
      [--title TITLE] [--date YYYY-MM-DD] [--slug SLUG] \
      [--model small|base|medium|large-v3] [--site PATH] [--force]

Defaults:
  --site  <repo>/english-site
  --date  today (UTC)
  --title slug-derived from the MP3 filename
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_client as r2  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FFMPEG = REPO / "bin" / "ffmpeg-static" / "ffmpeg"
FFPROBE = REPO / "bin" / "ffmpeg-static" / "ffprobe"
DICT_CSV = REPO / "tools" / "ecdict.csv"
PHRASES_TSV = REPO / "tools" / "phrase_notes.tsv"


def log(msg: str) -> None:
    print(f"[make_episode] {msg}", file=sys.stderr, flush=True)


def slugify(text: str, maxlen: int = 70) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    return text[:maxlen].strip("-") or "episode"


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        [str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def transcribe(model_name: str, mp3: Path) -> tuple[list[tuple[float, float, str]], float]:
    import os

    # keep the model cache inside the repo (home is read-only in the sandbox)
    os.environ.setdefault("HF_HOME", str(REPO / ".hf-cache"))
    from faster_whisper import WhisperModel

    log(f"loading whisper model '{model_name}' (int8, cpu)...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8",
                         cpu_threads=16)
    log(f"transcribing {mp3.name} ...")
    segments, info = model.transcribe(
        str(mp3),
        language="en",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        word_timestamps=True,
    )

    words: list[tuple[float, float, str]] = []
    for seg in segments:
        for w in seg.words or []:
            word = w.word.strip()
            if word:
                words.append((float(w.start), float(w.end), word))
    log(f"transcribed {len(words)} words "
        f"(audio {info.duration:.0f}s, language {info.language})")
    return words, info.duration


SENT_END = re.compile(r'[.!?…]["\')\]»”]*$')
SOFT_WORDS = 26      # 短于此：只在句末标点处切
HARD_WORDS = 48      # 每行的绝对上限
MIN_WORDS = 4
BIG_PAUSE = 0.6      # 足以在无标点时单独作为切点的停顿（秒）
CLAUSE_END = re.compile(r"[,;:—–-]$")
CONNECTORS = {
    "and", "but", "so", "or", "because", "while", "when", "where",
    "that", "which", "who", "whose", "if", "as",
}


def _best_cut(seg: list[tuple[float, float, str]]) -> int:
    """Pick the split position (0-based index of the last word of part 1)
    for an over-long run, preferring natural boundaries:
    long pause > pause+comma > pause > comma > connector."""
    lo = SOFT_WORDS
    hi = min(len(seg) - 1, HARD_WORDS)
    best, best_score = -1, -1.0
    for i in range(lo - 1, hi):
        gap = seg[i + 1][0] - seg[i][1]
        score = 0.0
        if gap >= BIG_PAUSE:
            score += 10
        elif gap >= 0.45:
            score += 5
        elif gap >= 0.25:
            score += 1
        if CLAUSE_END.search(seg[i][2]):
            score += 4
        if seg[i + 1][2].strip(",. ").lower() in CONNECTORS:
            score += 2
        score -= (i - (lo - 1)) * 0.15  # prefer the earliest decent boundary
        if score > best_score:
            best, best_score = i, score
    return best


def to_sentences(words: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    """Group words into listenable units.

    Pass 1: split at terminal punctuation.
    Pass 2: runs longer than SOFT_WORDS are split again at the best
            clause boundary (pause / comma / connector), never before
            SOFT_WORDS and never past HARD_WORDS.
    Pass 3: tiny fragments are merged into the previous unit.
    """
    raw: list[list[tuple[float, float, str]]] = []
    cur: list[tuple[float, float, str]] = []
    for start, end, word in words:
        cur.append((start, end, word))
        if SENT_END.search(word) and len(cur) >= MIN_WORDS:
            raw.append(cur)
            cur = []
    if cur:
        raw.append(cur)

    pieces: list[list[tuple[float, float, str]]] = []
    for seg in raw:
        while len(seg) > SOFT_WORDS:
            cut = _best_cut(seg)
            rest = seg[cut + 1:]
            if len(rest) < 2 * MIN_WORDS:
                break  # tail too short to be its own line
            pieces.append(seg[: cut + 1])
            seg = rest
        pieces.append(seg)

    merged: list[list[tuple[float, float, str]]] = []
    for s in pieces:
        if merged and len(s) < MIN_WORDS and len(merged[-1]) + len(s) <= HARD_WORDS + 10:
            merged[-1].extend(s)
        else:
            merged.append(s)
    return merged


# ---------------------------------------------------------------------------
# Vocabulary notes: per-sentence glossary of tricky words + common phrases.
# Difficulty proxy: BNC frequency rank (smaller = more common). Words in the
# top ~3000 BNC ranks are core vocabulary and get skipped.
# ---------------------------------------------------------------------------

BNC_COMMON = 3000    # BNC 前 3000 高频词不注
MAX_WORD_NOTES = 4   # 每句最多 4 个词注
MAX_NOTES = 5        # 加上短语后的总上限
MIN_RARE_LEN = 5     # 词典未收录的词至少 5 个字母才注

# 现代常用词不在 BNC 里但学习者认识，不注
BLOCKLIST = {
    "podcast", "media", "digital", "online", "offline", "internet",
    "social", "climate", "pandemic", "celebrity", "influencer", "viral",
    "audio", "video", "camera", "phone", "screen", "network", "platform",
    "content", "creator", "selfie", "email", "robot", "vaccine",
    "inflation", "recession", "artificial", "intelligence",
    "google", "youtube", "tiktok", "instagram", "twitter", "facebook",
    "app", "apps", "wifi", "blog", "streaming", "podcasts",
}


def load_dict() -> dict[str, tuple[str, str, int, int]]:
    """word -> (phonetic, first translation line, bnc rank, oxford flag)."""
    if not DICT_CSV.exists():
        sys.exit(
            f"{DICT_CSV} is missing.\n"
            "ECDICT is a 66 MB table, so it is not committed (see .gitignore).\n"
            "Fetch it once with:\n"
            "  curl -L -o tools/ecdict.csv \\\n"
            "    https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
        )
    d: dict[str, tuple[str, str, int, int]] = {}
    with open(DICT_CSV, encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if not row or not row[0]:
                continue
            word = row[0].lower()
            if word in d:
                continue
            raw = row[3] if len(row) > 3 else ""
            trans = raw.replace("\\n", "\n").split("\n")[0]
            trans = re.sub(r"\[网络\].*$", "", trans).strip()[:45]
            try:
                bnc = int(row[8] or 0)
            except ValueError:
                bnc = 0
            oxford = 1 if (len(row) > 6 and row[6] == "1") else 0
            d[word] = (row[1] or "", trans, bnc, oxford)
    return d


def load_phrases() -> list[tuple[str, str]]:
    out = []
    for line in PHRASES_TSV.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            ph, gloss = line.split("\t", 1)
            out.append((ph.strip(), gloss.strip()))
    return out


def _norm_ipa(p: str) -> str:
    # ECDICT 用 DJ 记音：ә 是西里尔字母状的中央元音，: 是长音符号
    return p.replace("\u04e9", "\u0259").replace(":", "\u02d0")


# 常用不规则变化 → 原形（词典里的变形词条 bnc 不具代表性）
IRREG = {
    "women": "woman", "children": "child", "people": "person", "men": "man",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "geese": "goose",
    "oxen": "ox", "struck": "strike", "broke": "break", "broken": "break",
    "taken": "take", "got": "get", "found": "find", "led": "lead",
    "made": "make", "sent": "send", "brought": "bring", "built": "build",
    "caught": "catch", "chose": "choose", "drove": "drive", "fell": "fall",
    "fought": "fight", "forgot": "forget", "gave": "give", "grew": "grow",
    "knew": "know", "laid": "lay", "left": "leave", "lost": "lose",
    "meant": "mean", "met": "meet", "paid": "pay", "ran": "run",
    "sang": "sing", "sat": "sit", "sold": "sell", "spoke": "speak",
    "spent": "spend", "stole": "steal", "swam": "swim", "threw": "throw",
    "told": "tell", "wore": "wear", "won": "win", "wrote": "write",
    "drew": "draw", "fed": "feed", "held": "hold", "shook": "shake",
    "shut": "shut", "slept": "sleep", "swept": "sweep", "ate": "eat",
    "blew": "blow", "dug": "dig", "froze": "freeze", "hung": "hang",
}

# 词尾还原（stunning→stun, dreadfully→dreadful, ...）
_SUFFIXES = ("est", "ing", "ed", "ly", "ful", "less", "ous", "ive",
             "able", "ible", "ment", "ness", "er")
_BASE_IN_GLOSS = re.compile(r"([a-z]+)的(?:过去式|过去分词|复数|比较级|最高级)")


def _variants(word: str, d: dict) -> list[str]:
    """Candidate base forms for frequency lookup, most specific first."""
    out: list[str] = []
    if word in IRREG:
        out.append(IRREG[word])
    e = d.get(word)
    if e and e[1]:
        m = _BASE_IN_GLOSS.search(e[1])
        if m:
            out.append(m.group(1))
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) > len(suf) + 3:
            base = word[: -len(suf)]
            out.append(base)
            if base.endswith(("e",)):
                continue
            out.append(base + "e")
            if len(base) > 3 and base[-1] == base[-2]:
                out.append(base[:-1])
    if word.endswith("ies") and len(word) > 4:
        out.append(word[:-3] + "y")
    if word.endswith("es") and len(word) > 3:
        out.append(word[:-2])
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        out.append(word[:-1])
    return [v for v in out if v not in out[:0] and v != word]


def annotate(text: str, d: dict, phrases: list[tuple[str, str]]) -> list[dict]:
    """Pick the hardest words + matched set phrases in a sentence.

    A word is core vocabulary (skipped) when its own entry or any reduced
    base form ranks in the BNC top 3000 or carries the oxford core-list
    flag. Other dictionary words get annotated; unlisted words are noted
    as 生词, except capitalized proper nouns (personal names).
    """
    cands: dict[str, tuple[str, str, str, int]] = {}
    for tok in re.findall(r"[A-Za-z][A-Za-z'\-]*", text):
        if "'" in tok or len(tok) < 4:
            continue
        w = tok.lower()
        if w in cands or w in BLOCKLIST:
            continue

        e = d.get(w)
        min_rank, min_entry = (e[2], e) if (e and e[2]) else (0, None)
        for var in _variants(w, d):
            ev = d.get(var)
            if ev and ev[2] and (min_rank == 0 or ev[2] < min_rank):
                min_rank, min_entry = ev[2], ev

        core = (min_rank and min_rank < BNC_COMMON) or bool(e and e[3]) \
            or bool(min_entry and min_entry[3])
        if core:
            continue  # 核心词（含其常见变形）

        if tok[0].isupper() and e and re.search(r"人名", e[1]):
            continue  # 人名（Melvin 等）不注；地名保留（Venezuela/Qing）
        if not min_rank:
            if tok[0].isupper():
                if not e:
                    continue  # 未收录的大写词按专有名词跳过
            elif not e and len(w) < MIN_RARE_LEN:
                continue

        if e and e[1] and not e[1].startswith("pl."):
            ipa, gloss = _norm_ipa(e[0]), e[1]
        elif min_entry and min_entry[1]:
            ipa, gloss = _norm_ipa(min_entry[0]), min_entry[1]
        else:
            ipa, gloss = "", "生词（词典未收录）"
        cands[w] = (tok, ipa, gloss, min_rank or 999999)

    # matched set phrases
    low = re.sub(r"\s+", " ", text.lower()).replace(" -", "-")
    phrase_hits = []
    for ph, gloss in phrases:
        if len(phrase_hits) >= MAX_NOTES:
            break
        if re.search(r"\b" + re.escape(ph) + r"\b", low):
            phrase_hits.append({"word": ph, "ipa": "", "gloss": gloss, "phrase": True})

    def covered(w: str) -> bool:
        return any(w in re.sub(r"\s+", " ", pn["word"]) for pn in phrase_hits)

    notes: list[dict] = []
    picked = sorted(cands.items(), key=lambda kv: (-kv[1][3], -len(kv[0])))[:MAX_WORD_NOTES]
    order = re.findall(r"[A-Za-z][A-Za-z'\-]*", text.lower())
    pos = {w: i for i, w in enumerate(order)}
    for w, (surface, ipa, gloss, _) in sorted(picked, key=lambda kv: pos.get(kv[0], 1 << 30)):
        if covered(w):
            continue
        notes.append({"word": surface, "ipa": ipa, "gloss": gloss})
    for pn in phrase_hits:
        if len(notes) < MAX_NOTES:
            notes.append(pn)
    return notes


def notes_to_yaml(notes: list[dict]) -> str:
    parts = []
    for n in notes:
        s = (f"{{word: {json.dumps(n['word'], ensure_ascii=False)}, "
             f"ipa: {json.dumps(n.get('ipa', ''), ensure_ascii=False)}, "
             f"gloss: {json.dumps(n['gloss'], ensure_ascii=False)}}}")
        if n.get("phrase"):
            s = s[:-1] + ", phrase: true}"
        parts.append(s)
    return "[ " + ", ".join(parts) + " ]"


def add_notes_to_episode(md_path: Path, d: dict, phrases: list[tuple[str, str]]) -> int:
    """Rewrite an existing episode's frontmatter, adding notes per sentence."""
    lines = md_path.read_text(encoding="utf-8").splitlines()
    out, n = [], 0
    # 兼容两种历史格式：notes 在花括号内（正确）或花括号外（旧版错误输出）
    pat = re.compile(
        r'  - \{text: (.+?), file: "(.+)", start: ([0-9.]+), end: ([0-9.]+)'
        r'(?:\}?, notes: \[.*\])?\}?\s*$')
    for ln in lines:
        m = pat.match(ln)
        if not m:
            out.append(ln)
            continue
        text = json.loads(m.group(1))
        base = (f'  - {{text: {json.dumps(text, ensure_ascii=False)}, '
                f'file: "{m.group(2)}", start: {m.group(3)}, end: {m.group(4)}')
        notes = annotate(text, d, phrases)
        if notes:
            base += ", notes: " + notes_to_yaml(notes)
            n += 1
        base += "}"
        out.append(base)
    md_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return n


def encode_episode(mp3: Path, out: Path) -> None:
    """Re-encode the full episode as CBR 96k MP3 with an Info header, so
    browsers can seek to sentence timestamps precisely (the originals have
    no Xing/LAME header and seeking them would drift)."""
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "error", "-i", str(mp3),
         "-vn", "-c:a", "libmp3lame", "-b:a", "96k", "-write_xing", "1",
         str(out)],
        check=True, capture_output=True,
    )


def write_hugo_episode(site: Path, slug: str, title: str, show: str,
                       date_str: str, sentences: list[list[tuple[float, float, str]]],
                       duration: float, mp3: Path,
                       notes: list[list[dict]] | None = None) -> Path:
    ep_dir = site / "content" / "episodes"
    ep_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = site / "static" / "audio" / slug
    audio_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        "layout: single",
        f'title: {json.dumps(title, ensure_ascii=False)}',
        f'show: {json.dumps(show, ensure_ascii=False)}',
        # file the episode under its show taxonomy page (/categories/<show>/)
        f'categories: [{json.dumps(show, ensure_ascii=False)}]',
        f'date: {date_str}T00:00:00Z',
        f'slug: "{slug}"',
        f'audioDir: "{slug}"',
        f"totalDuration: {duration:.1f}",
        "sentences:",
    ]
    for i, s in enumerate(sentences, 1):
        text = " ".join(w[2] for w in s)
        # NOTE: YAML block sequences do not allow unbraced inline mappings;
        # use flow mappings { ... } so Hugo's parser accepts them.
        line = (
            f'  - {{text: {json.dumps(text, ensure_ascii=False)}, '
            f"start: {s[0][0]:.2f}, end: {s[-1][1]:.2f}"
        )
        if notes and notes[i - 1]:
            line += ", notes: " + notes_to_yaml(notes[i - 1])
        line += "}"
        lines.append(line)
    lines += ["---", ""]
    md_path = ep_dir / f"{slug}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    for old in audio_dir.glob("*.mp3"):  # drop stale clips from earlier runs
        old.unlink()
    log(f"encoding full episode audio (single stream, CBR 96k)...")
    encode_episode(mp3, audio_dir / "episode.mp3")
    return md_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mp3", type=Path, help="episode audio file")
    ap.add_argument("--show", required=True, help='e.g. "Global News Podcast"')
    ap.add_argument("--title", default=None, help="episode title (default: filename)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--model", default="small",
                    help="whisper model: tiny/base/small/medium/large-v3")
    ap.add_argument("--site", type=Path, default=REPO / "english-site")
    ap.add_argument("--force", action="store_true", help="overwrite an existing episode")
    ap.add_argument("--retranscribe", action="store_true",
                    help="ignore the transcription cache and run whisper again")
    ap.add_argument("--notes", action="store_true",
                    help="给新剧集生成词汇注释（默认关闭）")
    ap.add_argument("--upload", dest="upload", action="store_true", default=None,
                    help="upload the episode MP3 to R2 (default: yes when credentials exist)")
    ap.add_argument("--no-upload", dest="upload", action="store_false",
                    help="keep the MP3 local and do not touch R2")
    ap.add_argument("--r2-prefix", default="audio",
                    help="key prefix inside the bucket (default: audio)")
    ap.add_argument("--keep-local", action="store_true",
                    help="keep static/audio/<slug>/episode.mp3 after a successful upload")
    ap.add_argument("--notes-only", action="store_true",
                    help="只给已有剧集加/更新词汇注释，不重跑转写、不切音频")
    args = ap.parse_args()

    mp3: Path = args.mp3.expanduser().resolve()
    if not mp3.is_file():
        log(f"no such file: {mp3}")
        return 2

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = args.title or re.sub(r"\.mp3$", "", mp3.stem, flags=re.I).replace("-", " ").strip()
    slug = args.slug or f"{date_str}-{slugify(title)}"

    md_path = args.site / "content" / "episodes" / f"{slug}.md"
    if args.notes_only:
        if not md_path.exists():
            log(f"episode not found: {md_path}")
            return 2
        d = load_dict()
        phrases = load_phrases()
        n = add_notes_to_episode(md_path, d, phrases)
        log(f"{md_path.name}: 词汇注释已更新（{n} 句带注释）")
        return 0

    if md_path.exists() and not args.force:
        log(f"episode already exists: {md_path} (use --force to overwrite)")
        return 1

    cache_file = args.site / "data" / "transcripts" / f"{slug}.{args.model}.json"
    words = duration = None
    if cache_file.exists() and not args.retranscribe:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        words = [tuple(w) for w in cached["words"]]
        duration = float(cached["duration"])
        log(f"using cached transcription ({len(words)} words)")
    else:
        words, duration = transcribe(args.model, mp3)
        if words:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps({"words": words, "duration": duration},
                           ensure_ascii=False),
                encoding="utf-8",
            )
            log(f"transcription cached at {cache_file}")
    if not words:
        log("transcription produced no words — giving up")
        return 1
    sentences = to_sentences(words)
    log(f"{len(sentences)} sentences, audio {duration:.0f}s")

    notes = None
    if args.notes:
        d = load_dict()
        phrases = load_phrases()
        notes = [annotate(" ".join(w[2] for w in s), d, phrases) for s in sentences]
        log(f"notes on {sum(1 for n in notes if n)} sentences")

    md_path = write_hugo_episode(args.site, slug, title, args.show, date_str,
                                 sentences, duration, mp3, notes)
    log(f"wrote {md_path}")

    audio_file = args.site / "static" / "audio" / slug / "episode.mp3"
    if args.upload is not False:
        cfg = r2.resolve_config()
        if cfg["access_key"] and cfg["secret_key"]:
            key = f"{args.r2_prefix.strip('/')}/{slug}/episode.mp3"
            ok, msg = r2.put_file(cfg, audio_file, key)
            if ok:
                url = r2.public_url(cfg, key)
                log(f"uploaded to R2: {msg}")
                log(f"public URL: {url}")
                text = md_path.read_text(encoding="utf-8")
                text = text.replace(f'audioDir: "{slug}"',
                                    f'audioDir: "{slug}"\naudioURL: "{url}"', 1)
                md_path.write_text(text, encoding="utf-8")
                # The site keeps only pages; the audio lives in R2 from here on.
                if not args.keep_local:
                    shutil.rmtree(audio_file.parent, ignore_errors=True)
                    log("removed the local copy (git stays small; R2 serves the audio)")
            else:
                log(f"R2 upload failed ({msg}) — keeping the local file as fallback")
        else:
            log("no R2 credentials found — keeping the audio local")
    log(f"audio: {audio_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
