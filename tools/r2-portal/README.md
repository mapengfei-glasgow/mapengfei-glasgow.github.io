# R2 portal Worker

A ~150-line Cloudflare Worker that gives the site's **/files/** page a backend:
list the bucket, upload files, delete them. The browser can never hold the R2
secret keys, so this Worker is the piece that talks to R2 with an R2 binding.

```
GET  /api/list?prefix=&limit=   → { files: [{ key, size, uploaded, url }] }
POST /api/upload                → multipart/form-data (one or more `file` fields,
                                  optional `prefix`) → { files: [{ key, size, url }] }
POST /api/delete                → JSON { key } → { ok: true }
GET  /api/health                → { ok: true }   (no auth, for probes)
```

Every request except `/api/health` needs `Authorization: Bearer <PORTAL_TOKEN>`.
CORS is restricted to `ALLOWED_ORIGIN`.

## Deploy (dashboard, ~2 minutes)

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Worker** → give it
   a name such as `r2-portal` → **Deploy**.
2. **Edit code**: delete the sample, paste `worker.js` from this folder, **Deploy**.
3. **Settings → Variables and Secrets** (add each as *Secret* where possible):

   | name | value |
   | --- | --- |
   | `PORTAL_TOKEN` | a long random string, e.g. `openssl rand -hex 24` |
   | `PUBLIC_BASE` | `https://bucket.r2.mapengfei.cn` |
   | `ALLOWED_ORIGIN` | `https://mapengfei-glasgow.github.io` |
   | `UPLOAD_PREFIX` | `uploads` (optional, this is the default) |

4. **Settings → Bindings → Add → R2 bucket**:
   variable name **`BUCKET`**, bucket **`aorta-data`** → save.
5. Copy the Worker URL (e.g. `https://r2-portal.<subdomain>.workers.dev`) and put
   it in the site config:

   ```toml
   # english-site/hugo.toml
   [params]
     portalApi = "https://r2-portal.<subdomain>.workers.dev"
   ```

   Commit and push — the /files/ page then uploads, lists live and deletes.
6. Open `/files/` and paste the `PORTAL_TOKEN` into the page's *Portal token*
   field (stored in that browser's localStorage only).

> Prefer the CLI? `npx wrangler deploy` from this folder with
> `CLOUDFLARE_API_TOKEN` set to a token that has **Workers Scripts: Edit** plus
> R2 access works too — the token currently in `.ref/r2.env` is R2-only and
> cannot deploy Workers (the API answers 403).

## Without the Worker

The page still works as a **file list with copy-link buttons**: generate the
manifest and commit it:

```bash
python3 tools/r2_upload.py --manifest english-site/static/files.json
```

Uploads and deleting then stay CLI-only (`tools/r2_upload.py file.zip`).

## Limits & notes

- Workers request bodies are limited to ~100 MB per request (the Worker rejects
  anything over 95 MB with HTTP 413).
- `PORTAL_TOKEN` is a shared secret: anyone who has it can upload and delete.
  Rotate it in the Worker settings if it leaks; the page picks up the new value
  the next time you paste it.
- The page and the file list are public; only upload/delete are gated.
- The Worker keeps uploads under `UPLOAD_PREFIX` and refuses `..` path segments.

## Tests

```bash
node tools/r2-portal/worker.test.mjs     # 25 assertions, no network needed
```

The site-side UI is covered by `.ref/jstest/pw-portal.js` (Playwright), which
runs the page against a stubbed Worker API and against the static manifest.
