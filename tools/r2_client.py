#!/usr/bin/env python3
"""Minimal Cloudflare R2 (S3-compatible) client — standard library only.

Used by tools/r2_upload.py (CLI) and tools/make_episode.py (publishing pipeline).

Credentials come from, in order:
  1. an env file (default: ~/.r2.env, then <repo>/.ref/r2.env)
  2. environment variables R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY

Recognised keys: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT,
R2_BUCKET, R2_PUBLIC_BASE.
"""

from __future__ import annotations

import hashlib
import hmac
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REGION = "auto"
SERVICE = "s3"
ALGO = "AWS4-HMAC-SHA256"
DEFAULT_ENDPOINT = "https://4b0e27f38ff80311386c110a2e6b34a7.r2.cloudflarestorage.com"
DEFAULT_BUCKET = "bucket"
DEFAULT_PUBLIC_BASE = "https://bucket.r2.mapengfei.cn"

# Cloudflare's WAF answers 403 to the default "Python-urllib/x.y" agent, and some
# proxies dislike HEAD requests, so always send a plain UA and prefer ranged GETs.
USER_AGENT = "r2-upload/1.0 (python-urllib)"
CHECK_USER_AGENT = "Mozilla/5.0 (compatible; r2-upload/1.0)"

REPO = Path(__file__).resolve().parent.parent
ENV_FILE_CANDIDATES = [Path.home() / ".r2.env", REPO / ".ref" / "r2.env"]


class R2Error(Exception):
    pass


# ---------------------------------------------------------------- credentials

def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip("'\"")
    return out


def resolve_config(env_file=None, bucket: str | None = None,
                   endpoint: str | None = None,
                   public_base: str | None = None) -> dict[str, str]:
    cfg: dict[str, str] = {}
    candidates = [Path(env_file).expanduser()] if env_file else ENV_FILE_CANDIDATES
    for cand in candidates:
        if cand and cand.exists():
            cfg.update(load_env_file(cand))
            cfg["_env_file"] = str(cand)
            break

    def pick(env_name: str, key: str, default: str = "") -> str:
        return os.environ.get(env_name) or cfg.get(key) or default

    return {
        "access_key": pick("R2_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID"),
        "secret_key": pick("R2_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY"),
        "endpoint": (endpoint or pick("R2_ENDPOINT", "R2_ENDPOINT", DEFAULT_ENDPOINT)).rstrip("/"),
        "bucket": bucket or pick("R2_BUCKET", "R2_BUCKET", DEFAULT_BUCKET),
        "public_base": (public_base or pick("R2_PUBLIC_BASE", "R2_PUBLIC_BASE",
                                            DEFAULT_PUBLIC_BASE)).rstrip("/"),
        "env_file": cfg.get("_env_file", ""),
    }


# ------------------------------------------------------------------- signing

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str) -> bytes:
    k = _sign(("AWS4" + secret).encode("utf-8"), datestamp)
    k = _sign(k, REGION)
    k = _sign(k, SERVICE)
    return _sign(k, "aws4_request")


def _canonical_uri(bucket: str, key: str) -> str:
    parts = ([bucket] + [p for p in key.split("/") if p]) if key else [bucket]
    return "/" + "/".join(urllib.parse.quote(p, safe="") for p in parts)


def signed_request(cfg: dict, method: str, bucket: str, key: str = "",
                   body: bytes | None = None, content_type: str = "",
                   extra_query: str = "") -> urllib.request.Request:
    host = urllib.parse.urlparse(cfg["endpoint"]).netloc
    uri = "/" if (method == "GET" and not bucket) else _canonical_uri(bucket, key)
    payload = body if body is not None else b""
    payload_hash = hashlib.sha256(payload).hexdigest()

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")

    headers = {"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": amz_date}
    if content_type:
        headers["content-type"] = content_type

    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted(headers))
    canonical_request = "\n".join([method, uri, extra_query, canonical_headers,
                                   signed_headers, payload_hash])

    scope = f"{datestamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join([ALGO, amz_date, scope,
                                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    signature = hmac.new(_signing_key(cfg["secret_key"], datestamp),
                         string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    headers["authorization"] = (
        f"{ALGO} Credential={cfg['access_key']}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"{cfg['endpoint']}{uri}" + (f"?{extra_query}" if extra_query else "")
    req = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None,
                                 method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("User-Agent", USER_AGENT)
    return req


def do_request(cfg: dict, method: str, bucket: str, key: str = "",
               body: bytes | None = None, content_type: str = "",
               extra_query: str = "", timeout: int = 600) -> tuple[int, bytes]:
    req = signed_request(cfg, method, bucket, key, body, content_type, extra_query)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise R2Error(f"{method} {key}: {exc}") from exc


# ------------------------------------------------------------------ operations

def list_buckets(cfg: dict) -> list[str]:
    status, body = do_request(cfg, "GET", "", "")
    if status != 200:
        raise R2Error(f"ListBuckets HTTP {status}: {body[:200].decode('utf-8', 'replace')}")
    return re.findall(r"<Name>([^<]+)</Name>", body.decode("utf-8", "replace"))


def create_bucket(cfg: dict, bucket: str) -> None:
    status, body = do_request(cfg, "PUT", bucket, "")
    if status in (200, 201):
        return
    text = body[:300].decode("utf-8", "replace")
    if "BucketAlreadyOwnedByYou" in text or "BucketAlreadyExists" in text:
        return
    raise R2Error(f"CreateBucket HTTP {status}: {text}")


def guess_content_type(path: Path) -> str:
    if path.suffix.lower() == ".zip":
        return "application/zip"
    if path.suffix.lower() == ".mp3":
        return "audio/mpeg"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def put_file(cfg: dict, path: Path, key: str, content_type: str = "") -> tuple[bool, str]:
    """Upload a local file to bucket/key. Returns (ok, message)."""
    if not cfg["access_key"] or not cfg["secret_key"]:
        return False, "no R2 credentials found (see tools/r2_client.py docstring)"
    body = path.read_bytes()
    ctype = content_type or guess_content_type(path)
    try:
        status, resp = do_request(cfg, "PUT", cfg["bucket"], key, body, ctype)
    except R2Error as exc:
        return False, str(exc)
    if status in (200, 201):
        return True, f"{len(body)/1e6:.1f} MB → s3://{cfg['bucket']}/{key}"
    return False, f"HTTP {status}: {resp[:300].decode('utf-8', 'replace')}"


def delete_object(cfg: dict, key: str) -> tuple[bool, str]:
    status, body = do_request(cfg, "DELETE", cfg["bucket"], key)
    if status in (200, 204):
        return True, f"deleted {cfg['bucket']}/{key}"
    return False, f"HTTP {status}: {body[:200].decode('utf-8', 'replace')}"


def list_objects(cfg: dict, prefix: str = "") -> list[dict]:
    # R2 wants the value fully percent-encoded in the canonical query
    # (a literal "/" makes it answer SignatureDoesNotMatch).
    q = "list-type=2&prefix=" + urllib.parse.quote(prefix, safe="")
    status, body = do_request(cfg, "GET", cfg["bucket"], key="", extra_query=q)
    if status != 200:
        raise R2Error(f"ListObjects HTTP {status}: {body[:200].decode('utf-8', 'replace')}")
    text = body.decode("utf-8", "replace")
    out = []
    for e in re.findall(r"<Contents>(.*?)</Contents>", text, re.S):
        k = re.search(r"<Key>([^<]*)</Key>", e)
        sz = re.search(r"<Size>(\d+)</Size>", e)
        lm = re.search(r"<LastModified>([^<]*)</LastModified>", e)
        if k:
            out.append({
                "key": k.group(1),
                "size": int(sz.group(1)) if sz else 0,
                "uploaded": lm.group(1) if lm else None,
            })
    out.sort(key=lambda o: o["uploaded"] or "", reverse=True)
    return out


def public_url(cfg: dict, key: str) -> str:
    return f"{cfg['public_base']}/{urllib.parse.quote(key)}"


def check_public(url: str, timeout: int = 60) -> tuple[int, str]:
    """Ranged GET against the public URL (HEAD is refused by some proxies)."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0",
                                               "User-Agent": CHECK_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.headers.get("content-range") or r.headers.get("content-length") or "")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except urllib.error.URLError as exc:
        return 0, str(exc)
