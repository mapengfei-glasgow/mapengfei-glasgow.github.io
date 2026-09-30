# Site API Worker

One Cloudflare Worker behind two pages of the site:

| page | what it needs |
| --- | --- |
| **/files/** | list the R2 bucket, upload files, delete them |
| **/words/** and every ☆ on an episode page | the vocabulary book: read, add, remove, import |

```
GET    /api/health                       → { ok: true }                    (no auth)
GET    /api/whoami                       → { ok: true, service }
GET    /api/list?prefix=&limit=&cursor=   → { files: [{ key, size, uploaded, url }] }
POST   /api/upload                       → multipart/form-data (`file` fields, `prefix`)
POST   /api/delete                       → JSON { key }
GET    /api/vocab                        → { items: [...], count, updated }
POST   /api/vocab/add                    → JSON { slug, idx, show, title, text, explain }
POST   /api/vocab/remove                 → JSON { slug, idx }
POST   /api/vocab/import                 → JSON { items|documents:[...] }  (merges, dedupes)
```

Every request except `/api/health` needs `Authorization: Bearer <SITE_TOKEN>`,
compared byte-wise in constant time. CORS is restricted to `ALLOWED_ORIGIN`.

`SITE_TOKEN` is the **sync code** you type once per device (the site keeps it in
`localStorage`; it is also what unlocks `/files/`). With it unset the Worker
answers 401 to everything but `/api/health` — it fails closed, unlike the old
AppWrite allowlist, where "empty" meant "any signed-in user" and sign-up was open
to the world.

## Why this replaced AppWrite

The Worker used to verify an AppWrite JWT and the vocabulary lived in an AppWrite
collection. AppWrite's free plan [pauses a project after 7 days without
development activity in the
Console](https://appwrite.io/changelog/entry/2026-02-20-1) — and, as their team
[confirmed in the community
thread](https://appwrite.io/threads/1481574986136158322), API calls, SDK usage and
visitor traffic explicitly **do not count**, and the detection is deliberately
undocumented so it cannot be gamed. An idle week therefore took both pages down,
with no cron trick to prevent it. Cloudflare has no such policy, so everything
now lives there.

## Deploy (dashboard, ~3 minutes)

The Worker keeps the name it was created with (`r2-portal`), so the URL in
`hugo.toml` (`params.apiBase`) stays valid.

1. **Create the private bucket** — dashboard → **R2** → *Create bucket* → name
   `site-private`. Do **not** attach a custom domain: this bucket holds the
   vocabulary and is reachable only through the Worker's binding.
2. **Paste the code** — **Workers & Pages** → `r2-portal` → *Edit code* → replace
   everything with `worker.js` from this folder → **Deploy**.
3. **Variables and Secrets** (add the secret as *Secret*):

   | name | value |
   | --- | --- |
   | `SITE_TOKEN` | *Secret* — a long random string, e.g. `openssl rand -hex 24` |
   | `PUBLIC_BASE` | `https://bucket.r2.mapengfei.cn` |
   | `ALLOWED_ORIGIN` | `https://mapengfei-glasgow.github.io` |
   | `UPLOAD_PREFIX` | `uploads` (optional, this is the default) |

   The old `APPWRITE_ENDPOINT` / `APPWRITE_PROJECT` / `ALLOWED_USERS` variables are
   unused now — deleting them saves confusion.
4. **Bindings → R2 bucket**: keep `BUCKET` → `aorta-data`, and add
   `PRIVATE` → `site-private`.
5. **Check it**: `curl -s https://<worker>.workers.dev/api/health` → `{"ok":true}`,
   and `curl -s -H "Authorization: Bearer $CODE" https://<worker>.workers.dev/api/vocab`
   → `{"items":[],"count":0}`.
6. **On each device**: open `/words/` (or the header *Sign in*) and paste the sync
   code once. `/files/` uses the same code.

> Prefer the CLI? `npx wrangler deploy` from this folder with `CLOUDFLARE_API_TOKEN`
> set to a token that has **Workers Scripts: Edit** plus R2 access. The R2-only
> token some hosts keep in `.ref/r2.env` cannot deploy Workers (the API answers 403).
> `npx wrangler secret put SITE_TOKEN` sets the secret, and the bucket bindings come
> from `wrangler.toml` — create `site-private` first.

## Restoring a backup (the old AppWrite book was abandoned)

The AppWrite vocabulary was dropped rather than migrated, and no export tool ships
with the site. `POST /api/vocab/import` stays as the way back in: it accepts a bare
array, `{ items }` or `{ documents }`, merges by `slug:idx` and reports how many it
added, so importing twice is harmless.

```bash
curl -H "Authorization: Bearer $SITE_TOKEN" -H 'content-type: application/json' \
     --data @vocab.json https://<worker>.workers.dev/api/vocab/import
```

## Rotating the sync code

Change `SITE_TOKEN` in the Worker settings and every device must enter the new code
once (the old code stops working immediately). Nothing else depends on it.

## Limits & notes

- Workers request bodies are capped at ~100 MB per request (the Worker rejects
  anything over 95 MB with HTTP 413); uploads stay under `UPLOAD_PREFIX` and `..`
  segments are refused.
- The vocabulary is a single object (`vocab/v1.json`) read-modify-written per
  change: it is one person's list, so there is nothing to contend for, and R2 is
  read-after-write consistent (KV is not — a star could look lost for up to a
  minute). Limits: 5000 sentences, 2 MB.
- The sync code sits in `localStorage`, so anything running in the page's origin
  can read it — the same trust model as the old `PORTAL_TOKEN`, minus the open
  sign-up.
- The file list itself is no longer public: listing, uploading and deleting all
  need the code. Only the R2 public URLs of individual objects stay open.

## Tests

```bash
node tools/site-api/worker.test.mjs     # 62 assertions, no network needed
```

Covers the constant-time token check (including the fail-closed case), file
listing/upload/delete, and the vocabulary CRUD + import + storage edge cases.
