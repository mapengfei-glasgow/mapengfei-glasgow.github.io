#!/usr/bin/env python3
"""Upload a file to Cloudflare R2 (S3-compatible API) — standard library only.

Credentials come from an env file (default `~/.r2.env`, then `<repo>/.ref/r2.env`)
or from the environment (R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY). Recognised
keys: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT, R2_BUCKET,
R2_PUBLIC_BASE.

Examples:
    python3 tools/r2_upload.py aorta-tether-8x-32x.zip
    python3 tools/r2_upload.py data.zip --bucket aorta-data --key releases/data.zip --create-bucket
    python3 tools/r2_upload.py --list-buckets
    python3 tools/r2_upload.py --list --prefix audio/
    python3 tools/r2_upload.py --delete audio/old/episode.mp3
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import r2_client as r2  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="file to upload")
    ap.add_argument("--bucket", help="bucket name")
    ap.add_argument("--key", help="object key (default: the file name)")
    ap.add_argument("--endpoint", help="S3 endpoint")
    ap.add_argument("--public-base", help="public base URL used for the printed link")
    ap.add_argument("--env-file", help="path to the credentials env file")
    ap.add_argument("--create-bucket", action="store_true", help="create the bucket if missing")
    ap.add_argument("--no-verify", action="store_true", help="skip the public URL check")
    ap.add_argument("--list-buckets", action="store_true", help="list buckets and exit")
    ap.add_argument("--list", action="store_true", help="list objects and exit")
    ap.add_argument("--prefix", default="", help="prefix for --list")
    ap.add_argument("--delete", metavar="KEY", help="delete an object and exit")
    ap.add_argument("--manifest", metavar="PATH",
                    help="write a files.json manifest (used by the /files/ page without the Worker)")
    args = ap.parse_args()

    cfg = r2.resolve_config(env_file=args.env_file, bucket=args.bucket,
                            endpoint=args.endpoint, public_base=args.public_base)
    if cfg["env_file"]:
        print(f"credentials: {cfg['env_file']}")
    print(f"endpoint:    {cfg['endpoint']}")
    print(f"bucket:      {cfg['bucket']}")

    if not cfg["access_key"] or not cfg["secret_key"]:
        print("No R2 credentials found. Put them in ~/.r2.env (or .ref/r2.env):\n"
              "  R2_ACCESS_KEY_ID=...\n  R2_SECRET_ACCESS_KEY=...", file=sys.stderr)
        return 2

    try:
        if args.list_buckets:
            for name in r2.list_buckets(cfg):
                print(f"  {name}")
            return 0

        if args.manifest:
            import json
            objects = r2.list_objects(cfg, args.prefix)
            for o in objects:
                o["url"] = r2.public_url(cfg, o["key"])
            payload = {"generated": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bucket": cfg["bucket"], "files": objects}
            out = Path(args.manifest).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"wrote {out} ({len(objects)} objects)")
            return 0

        if args.list:
            objects = r2.list_objects(cfg, args.prefix)
            if not objects:
                print(f"(no objects in {cfg['bucket']}/{args.prefix})")
            for o in objects:
                print(f"  {o['size']:>14,}  {o['key']}")
            return 0

        if args.delete:
            ok, msg = r2.delete_object(cfg, args.delete)
            print(msg)
            return 0 if ok else 1

        if not args.file:
            ap.print_help()
            return 2

        path = Path(args.file).expanduser()
        if not path.is_file():
            print(f"no such file: {path}", file=sys.stderr)
            return 2

        key = args.key or path.name
        if args.create_bucket:
            r2.create_bucket(cfg, cfg["bucket"])

        size = path.stat().st_size
        print(f"uploading {path} ({size/1e6:.1f} MB) → s3://{cfg['bucket']}/{key}")
        started = time.time()
        ok, msg = r2.put_file(cfg, path, key)
        if not ok:
            print(f"upload FAILED: {msg}")
            return 1
        took = max(time.time() - started, 1e-6)
        print(f"upload OK in {took:.1f}s ({size/1e6/took:.1f} MB/s)")

        url = r2.public_url(cfg, key)
        print(f"public URL: {url}")
        if not args.no_verify:
            status, detail = r2.check_public(url)
            if 200 <= status < 300:
                print(f"  verified: HTTP {status} {detail}".rstrip())
            else:
                print(f"  HTTP {status or '-'} — not reachable over the public URL {detail}".rstrip())
        return 0
    except r2.R2Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
