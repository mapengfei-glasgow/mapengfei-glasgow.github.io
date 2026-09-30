#!/usr/bin/env python3
"""Route the BBC through a node that can actually reach it.

WHY THIS EXISTS
---------------
The subscription's `自动选择` group is a url-test whose health-check URL is
Google's `generate_204`. It therefore parks on whichever node is fastest *for
Google*, which is not the same question as "can this node reach the BBC". Exit
nodes differ persistently here:

    2026-09-20  🇭🇰 香港 04 → every bbc.co.uk / bbci.co.uk URL: 503, Google: 59 ms
                🇩🇪 德国    → the same BBC URLs: 262-614 ms, fine

`自动选择` had settled on 香港 04, so the whole `🌍 国外媒体` chain answered 503 for
the BBC while Google, GitHub and HuggingFace were all healthy. The daily pipeline
could not download anything for hours and correctly failed.

(An earlier reading of the same symptom on 2026-09-18 blamed a transient
rate-limit and did not fix it. That was wrong: it is node-specific and lasts
until the url-test happens to move.)

WHAT IT DOES
------------
Idempotently adds to ~/.config/mihomo/config.yaml:

  * a `🇬🇧 BBC` url-test group whose health check is a small BBC URL on the very
    host the pipeline uses, so it only ever selects a BBC-capable node;
  * BBC rules at the TOP of `rules:`, so they win over the subscription's
    `🌍 国外媒体` catch-alls (the first matching rule wins).

It must be re-applied after a subscription refresh, because that overwrites
config.yaml. `tools/daily_bbc_pipeline.sh` calls it on every run for exactly
that reason, so the fix heals itself.

Usage:
    sudo-less, e.g.:  ./venv/bin/python tools/mihomo_bbc_route.py [--check-only]

Exit codes: 0 = route in place, 1 = could not apply, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

CONFIG = Path.home() / ".config" / "mihomo" / "config.yaml"
API = "http://127.0.0.1:9090"
GROUP = "🇬🇧 BBC"

# Small file on the host the pipeline actually downloads the feed from. A tiny
# URL matters: the group health-checks every member, so this must not be the
# 1.1 MB RSS feed.
CHECK_URL = "https://podcasts.files.bbci.co.uk/favicon.ico"

# Ordered by specificity; these are PREPENDED to `rules:`.
RULES = [
    "DOMAIN-SUFFIX,bbci.co.uk,🇬🇧 BBC",
    "DOMAIN-SUFFIX,bbc.co.uk,🇬🇧 BBC",
    "DOMAIN-SUFFIX,bbc.com,🇬🇧 BBC",
    "DOMAIN-SUFFIX,bbc.net.uk,🇬🇧 BBC",
    "DOMAIN-KEYWORD,bbcfmt,🇬🇧 BBC",
]


def quote(name: str) -> str:
    """YAML single-quoted scalar (names contain emoji, '|', ':', '[]')."""
    return "'" + name.replace("'", "''") + "'"


def node_names(cfg: dict) -> list[str]:
    return [p["name"] for p in cfg.get("proxies") or [] if p.get("name")]


def group_line(names: list[str]) -> str:
    members = ", ".join(quote(n) for n in names)
    return ("    - { name: " + quote(GROUP)
            + ", type: url-test, proxies: [" + members + "]"
            + ", url: " + quote(CHECK_URL)
            + ", interval: 300, tolerance: 50, lazy: false"
            + ", expected-status: 200 }\n")


def already_patched(text: str) -> bool:
    return GROUP in text and "bbci.co.uk,🇬🇧 BBC" in text


def check_live() -> bool:
    """Ask the running instance for the group (proves it is loaded, not just written)."""
    try:
        with urllib.request.urlopen(f"{API}/proxies", timeout=10) as r:
            return GROUP in json.load(r).get("proxies", {})
    except Exception:
        return False


def patch_text(text: str, names: list[str]) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted_group = inserted_rules = False
    for ln in lines:
        out.append(ln)
        if not inserted_group and ln.startswith("proxy-groups:"):
            out.append(group_line(names))
            inserted_group = True
        elif not inserted_rules and ln.startswith("rules:"):
            for r in RULES:
                out.append(f"    - {quote(r)}\n")
            inserted_rules = True
    if not (inserted_group and inserted_rules):
        raise SystemExit("could not find both `proxy-groups:` and `rules:` in "
                         f"{CONFIG} — refusing to write a half-patch")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check-only", action="store_true",
                    help="report whether the route is live, change nothing")
    args = ap.parse_args()

    if not CONFIG.exists():
        print(f"no mihomo config at {CONFIG}", file=sys.stderr)
        return 2

    text = CONFIG.read_text(encoding="utf-8")
    if args.check_only:
        live = check_live()
        print(f"config patched: {already_patched(text)}   live in mihomo: {live}")
        return 0 if live else 1

    if already_patched(text) and check_live():
        print(f"bbc route already in place ({GROUP} live)")
        return 0

    cfg = yaml.safe_load(text)
    names = node_names(cfg)
    if not names:
        print("no proxies in the config", file=sys.stderr)
        return 2

    backup = CONFIG.with_suffix(".yaml.bak-bbcroute")
    backup.write_text(text, encoding="utf-8")

    new = text if already_patched(text) else patch_text(text, names)
    # Validate before touching the live file: a broken config would take the
    # proxy down for everything, not just the BBC.
    parsed = yaml.safe_load(new)
    assert any(g.get("name") == GROUP for g in parsed["proxy-groups"]), "group missing"
    assert parsed["rules"][0] == RULES[0], "rules not prepended"
    CONFIG.write_text(new, encoding="utf-8")
    print(f"patched {CONFIG} ({len(names)} nodes in {GROUP}), backup at {backup.name}")

    subprocess.run(["systemctl", "--user", "restart", "mihomo"], check=False)
    for _ in range(20):
        import time
        time.sleep(2)
        if check_live():
            print(f"{GROUP} is live")
            return 0
    print("restarted mihomo but the group did not appear", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
