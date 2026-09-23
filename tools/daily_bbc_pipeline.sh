#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Daily BBC episode pipeline — run by bbc-daily.timer (systemd --user).
#
#   proxy -> download -> transcribe/publish -> Qwen A2 notes -> push
#
# This is the unattended version of the manual sequence documented in
# work/HOST-NOTES.md. Every stage is idempotent (the downloader keeps a state
# file, bbc_publish.py skips episodes that already have a page, qwen_explain.py
# skips chunks that already have results), so a failed run is safe to repeat:
#
#     systemctl --user start bbc-daily.service
#
# Environment overrides:
#   SHOW      BBC show to download      (default global-news)
#   DL_DIR    download directory        (default "downloads/BBC Global News Podcast")
#   SKIP_NOTES=1   skip the Qwen A2-notes stage
#
# Qwen lifecycle: the notes stage needs sglang-qwen.service on 127.0.0.1:30000.
# If it is not already serving, this script starts it and — unlike the manual
# sequence in work/HOST-NOTES.md — stops it again when the run ends, so the
# ~9 GB of resident model memory is not held for the remaining ~23.9 h of the
# day. If it was already serving (a human started it), it is left alone.
#
# Logs: journal (`journalctl --user -u bbc-daily`) and work/logs/bbc-daily-*.log
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # <repo>/.migration
SITE="$ROOT/english-site"                                 # symlink -> the Pages checkout
PY="$ROOT/venv/bin/python"

SHOW="${SHOW:-global-news}"
DL_DIR="${DL_DIR:-downloads/BBC Global News Podcast}"
SKIP_NOTES="${SKIP_NOTES:-0}"

PROXY="http://127.0.0.1:7891"
QWEN_HEALTH="http://127.0.0.1:30000/health"
BBC_FEED="https://podcasts.files.bbci.co.uk/p02nq0gn.rss"

# The BBC, HuggingFace and GitHub Pages are only reachable through the local
# Mihomo proxy on this host (see ~/memory.md).
export http_proxy="$PROXY" https_proxy="$PROXY"
export HF_HOME="$ROOT/.hf-cache"
export HF_HUB_DISABLE_XET=1

LOG_DIR="$ROOT/work/logs"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bbc-daily-$(date +%F).log") 2>&1

log()  { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
warn() { printf '[%s] WARN: %s\n' "$(date '+%F %T')" "$*"; }
fail() { printf '[%s] FAIL: %s\n' "$(date '+%F %T')" "$*"; exit 1; }

# Run a command until it succeeds. The local proxy intermittently answers 503
# for BBC hosts — observed on 2026-09-18 right after a ~160 MB burst of episode
# downloads, and gone a few minutes later: the very nodes that had failed
# answered on retry. A single-shot daily run would turn that blip into a missed
# day, so every network step is retried.
retry() {
    local attempts="$1" pause="$2" label="$3"; shift 3
    local i
    for i in $(seq 1 "$attempts"); do
        if "$@"; then
            [ "$i" -gt 1 ] && log "$label: ok on attempt $i/$attempts"
            return 0
        fi
        warn "$label failed (attempt $i/$attempts)"
        [ "$i" -lt "$attempts" ] && sleep "$pause"
    done
    return 1
}

bbc_reachable() {
    curl -sf -o /dev/null --max-time 40 "$BBC_FEED"
}

# --- stage 0b: make sure the BBC has a usable exit --------------------------
# `自动选择` health-checks against Google's generate_204, so it sits on whatever
# node is fastest *for Google* — which is not the same as being able to reach
# the BBC. On 2026-09-20 it had settled on a node where every bbc.co.uk and
# bbci.co.uk URL returned 503 while Google answered in 59 ms, and this pipeline
# could not download anything. tools/mihomo_bbc_route.py adds a BBC-specific
# url-test group; a subscription refresh rewrites config.yaml and drops it, so
# it is re-applied on every run. Non-fatal: if it cannot be confirmed, the
# reachability retry below still gets its say.
ensure_bbc_route() {
    local out
    if out="$("$PY" "$ROOT/tools/mihomo_bbc_route.py" 2>&1)"; then
        log "bbc route: $out"
    else
        warn "bbc route: could not confirm — $out"
    fi
    return 0
}

# --- stage 0: proxy --------------------------------------------------------
ensure_proxy() {
    if curl -sf -o /dev/null --max-time 10 -x "$PROXY" \
            https://www.google.com/generate_204; then
        log "proxy: ok"
        return 0
    fi
    log "proxy: not answering, starting mihomo.service"
    systemctl --user start mihomo.service 2>&1 || warn "could not start mihomo.service"
    local i
    for i in $(seq 1 30); do
        sleep 2
        if curl -sf -o /dev/null --max-time 10 -x "$PROXY" \
                https://www.google.com/generate_204; then
            log "proxy: ok after start"
            return 0
        fi
    done
    return 1
}

# --- stage 1: download -----------------------------------------------------
# A rolling window instead of `bbc_podcast.py --limit 1`, because the feed
# carries two editions per day plus cross-posted items from other programmes,
# so "the newest item" is the wrong episode as soon as an afternoon edition or
# a Happy Pod lands first. bbc_backfill.py takes the earliest item of each date
# — the edition this site has always published — and is idempotent, so a missed
# day (machine off, BBC posting late) is picked up by the next run.
WINDOW_DAYS="${WINDOW_DAYS:-3}"

run_download() {
    local from to
    from="$(date -d "$WINDOW_DAYS days ago" +%F)"
    to="$(date +%F)"
    log "download: earliest edition of each day in $from … $to"
    cd "$ROOT" || return 1
    # bbc_backfill.py raises bbc_podcast.py's timeouts for the proxy itself.
    "$PY" tools/bbc_backfill.py "$SHOW" --from "$from" --to "$to" --dir "$DL_DIR"
}

# --- stage 2: transcribe + publish ----------------------------------------
run_publish() {
    log "publish: transcribe -> R2 -> commit -> push"
    cd "$ROOT" || return 1
    "$PY" tools/bbc_publish.py
}

# --- stage 3: A2 notes via Qwen -------------------------------------------
# Set to 1 only when *this run* is what brought the service up. A daily timer
# has no business leaving an inference server resident all day: on 2026-09-22
# it started Qwen at 18:05 and the process was still holding ~9 GB at 19:45.
QWEN_STARTED_BY_US=0

ensure_qwen() {
    if curl -sf -o /dev/null --max-time 8 "$QWEN_HEALTH"; then
        log "qwen: already serving"
        return 0
    fi
    log "qwen: starting sglang-qwen.service (model load takes ~2 min)"
    systemctl --user start sglang-qwen.service 2>&1 || warn "could not start sglang-qwen.service"
    # Recorded before the readiness poll: even if the model never becomes
    # healthy, we are still the ones who started the unit and must not leak it.
    QWEN_STARTED_BY_US=1
    local i
    for i in $(seq 1 60); do
        sleep 10
        if curl -sf -o /dev/null --max-time 8 "$QWEN_HEALTH"; then
            log "qwen: ready"
            return 0
        fi
    done
    return 1
}

# Undo ensure_qwen, but only if ensure_qwen is what started it. Registered as an
# EXIT trap so every path is covered: the notes stage failing, a later `fail`,
# or an interrupted run all put Qwen back the way we found it.
release_qwen() {
    [ "$QWEN_STARTED_BY_US" = "1" ] || return 0
    QWEN_STARTED_BY_US=0
    log "qwen: stopping sglang-qwen.service (started by this run; notes are done)"
    if ! systemctl --user stop sglang-qwen.service 2>&1; then
        warn "could not stop sglang-qwen.service — stop it manually"
        return 0
    fi
    # SGLang's shutdown does not always answer the TERM in time, and systemd
    # then records the unit as failed/killed. Clear that so the next run (and
    # `systemctl --user status`) starts from a clean slate.
    systemctl --user reset-failed sglang-qwen.service 2>/dev/null || true
}

run_notes() {
    # Slugs this run just published, passed by main(). Deliberately NOT "every
    # episode without notes": the backlog (15 In Our Time episodes and four
    # Global News ones) is a separate, explicit action, and a daily timer must
    # not quietly rewrite a hundred pages.
    ensure_qwen || return 1
    log "notes: flagging sentences beyond A2"
    cd "$ROOT" || return 1
    "$PY" tools/flag_a2.py || return 1
    local slug
    for slug in "$@"; do
        # 💡 English notes: only for the sentences that contain something
        # beyond A2 (that is what flag_a2.py hands over).
        log "notes: generating explanations for $slug"
        "$PY" tools/qwen_explain.py --slug "$slug" || return 1
        # 🀄 Chinese: every sentence, because a reader following along needs the
        # ordinary sentences translated too — those are never flagged.
        log "notes: translating every sentence of $slug"
        "$PY" tools/qwen_explain.py --all-sentences --slug "$slug" || return 1
    done
    log "notes: merging explanations into frontmatter"
    "$PY" tools/merge_explain.py || return 1
    return 0
}

# --- git helpers -----------------------------------------------------------
sync_site() {
    cd "$SITE" || return 1
    git fetch --quiet origin main || { warn "git fetch failed; continuing"; return 0; }
    if git merge --ff-only origin/main >/dev/null 2>&1; then
        log "git: site up to date with origin/main"
    else
        warn "git: local main has diverged from origin/main; leaving it alone"
    fi
}

commit_notes() {
    cd "$SITE" || return 1
    # Only the episode frontmatter is staged: other workstreams commit into this
    # same repo, and `git add -A` would sweep up their unfinished files.
    git add content/episodes || return 1
    if git diff --cached --quiet; then
        log "git: no note changes to commit"
        return 0
    fi
    git commit -q -m "A2 notes: Qwen-generated plain-English explanations for new episodes" || return 1
    log "git: committed A2 notes"
    if git push -q origin main; then
        log "git: pushed"
        return 0
    fi
    warn "git: push rejected, retrying after a rebase"
    if git fetch -q origin main && git rebase origin/main && git push -q origin main; then
        log "git: pushed after rebase"
        return 0
    fi
    git rebase --abort 2>/dev/null
    warn "git: push failed; the commit stays local and will go out next run"
    return 1
}

# --- main ------------------------------------------------------------------
# Registered before any stage can start Qwen, so no exit path can skip it.
trap release_qwen EXIT

log "=== daily BBC pipeline start (show=$SHOW) ==="
sync_site

ensure_proxy || fail "proxy unavailable — cannot reach the BBC"
ensure_bbc_route
# Liveness via Google only proves the tunnel is up; the BBC is a separate hop
# with its own per-node blocks, so check the actual feed too.
retry 4 45 "BBC reachability" bbc_reachable \
    || fail "BBC unreachable through the proxy after 4 attempts"

# Snapshot the episode pages so the notes stage can tell which episodes this
# run published (bbc_publish.py does not report the slugs it produced).
BEFORE="$(mktemp)"; AFTER="$(mktemp)"
ls "$SITE/content/episodes" 2>/dev/null | sort > "$BEFORE"

retry 3 60 "download" run_download || fail "download failed"
run_publish  || fail "publish failed"

ls "$SITE/content/episodes" 2>/dev/null | sort > "$AFTER"
mapfile -t NEW_SLUGS < <(comm -13 "$BEFORE" "$AFTER" | sed -n 's/\.md$//p' | grep -v '^_index$')
rm -f "$BEFORE" "$AFTER"

if [ "$SKIP_NOTES" = "1" ]; then
    log "notes: skipped (SKIP_NOTES=1)"
elif [ "${#NEW_SLUGS[@]}" -eq 0 ]; then
    log "notes: no new episode pages this run, nothing to annotate"
elif run_notes "${NEW_SLUGS[@]}"; then
    commit_notes || warn "A2 notes produced but not pushed"
else
    warn "A2 notes stage failed; episodes are already published, continuing"
fi

log "=== daily BBC pipeline done ==="
