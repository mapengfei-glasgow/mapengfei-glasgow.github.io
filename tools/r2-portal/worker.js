/**
 * R2 file portal for the listening site — authenticated with AppWrite login.
 *
 * The /files/ page sends the visitor's AppWrite JWT (created client-side by the
 * SDK the site already uses); this Worker verifies it against the AppWrite API
 * and only then lets the request through. No shared token in the browser.
 *
 *   GET    /api/whoami                → { ok, user: { id, email, name } }
 *   GET    /api/list?prefix=&cursor=  → { files: [...], truncated, cursor }
 *   POST   /api/upload                → multipart/form-data (`file` fields, `prefix`)
 *   POST   /api/delete                → JSON { key }
 *   GET    /api/health                → { ok: true }            (no auth)
 *
 * Auth: `Authorization: Bearer <appwrite-jwt>`. The JWT is checked with
 * GET {APPWRITE_ENDPOINT}/account + X-Appwrite-JWT, then the resulting user must
 * match ALLOWED_USERS (comma separated ids/emails/names; empty = any signed-in
 * user). Verified users are cached briefly to keep listing cheap.
 *
 * Worker vars:
 *   APPWRITE_ENDPOINT  https://fra.cloud.appwrite.io/v1
 *   APPWRITE_PROJECT   the AppWrite project id
 *   ALLOWED_USERS      e.g. "aa" or "aa,someone@example.com" (empty = any account)
 *   PUBLIC_BASE        https://bucket.r2.mapengfei.cn
 *   ALLOWED_ORIGIN     https://mapengfei-glasgow.github.io
 *   UPLOAD_PREFIX      uploads
 * Binding: BUCKET → the R2 bucket
 */

const DEFAULT_PREFIX = "uploads";
const MAX_UPLOAD_BYTES = 95 * 1024 * 1024; // Workers request body limit is ~100 MB
const JWT_CACHE_MS = 60 * 1000;             // remember a verified JWT for a minute
const jwtCache = new Map();                 // jwt → { user, until }

function json(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extraHeaders },
  });
}

function corsHeaders(env, origin) {
  const allowed = (env.ALLOWED_ORIGIN || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const ok = origin && (allowed.length === 0 || allowed.includes(origin));
  return {
    "access-control-allow-origin": ok ? origin : allowed[0] || "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization,content-type",
    "access-control-max-age": "86400",
    vary: "Origin",
  };
}

/** Public URL for a key: encode each segment, keep the slashes. */
function publicUrl(env, key) {
  const base = (env.PUBLIC_BASE || "").replace(/\/+$/, "");
  const path = key.split("/").map(encodeURIComponent).join("/");
  return `${base}/${path}`;
}

/** Reject traversal / absolute paths; collapse whitespace. */
function safeKey(name, prefix) {
  const cleaned = String(name || "")
    .replace(/\\/g, "/")
    .split("/")
    .filter((seg) => seg && seg !== "." && seg !== "..")
    .join("/")
    .replace(/[\u0000-\u001f]/g, "")
    .trim();
  if (!cleaned) return null;
  const base = (prefix || DEFAULT_PREFIX).replace(/^\/+|\/+$/g, "");
  return cleaned.startsWith(base + "/") ? cleaned : `${base}/${cleaned}`;
}

/** Is this AppWrite user allowed to use the portal? */
function userAllowed(env, user) {
  const list = (env.ALLOWED_USERS || "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (!list.length) return true; // no allowlist configured → any signed-in account
  const ids = [user.$id, user.email, user.name, user.phone]
    .filter(Boolean)
    .map((v) => String(v).toLowerCase());
  return ids.some((id) => list.includes(id));
}

/** Ask AppWrite who this JWT belongs to (null when invalid/expired). */
async function appwriteUser(env, jwt) {
  if (!jwt) return null;
  const cached = jwtCache.get(jwt);
  if (cached && cached.until > Date.now()) return cached.user;

  const url = `${(env.APPWRITE_ENDPOINT || "").replace(/\/+$/, "")}/account`;
  let res;
  try {
    res = await fetch(url, {
      headers: { "X-Appwrite-Project": env.APPWRITE_PROJECT || "", "X-Appwrite-JWT": jwt },
    });
  } catch (err) {
    return null;
  }
  if (!res.ok) return null;
  const user = await res.json().catch(() => null);
  if (!user || !user.$id) return null;
  jwtCache.set(jwt, { user, until: Date.now() + JWT_CACHE_MS });
  return user;
}

function bearer(request) {
  return (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
}

async function listFiles(env, prefix, limit, cursor) {
  const listed = await env.BUCKET.list({
    prefix: prefix ? prefix.replace(/^\/+/, "") : undefined,
    limit: Math.min(Math.max(parseInt(limit || "1000", 10) || 1000, 1), 1000),
    cursor: cursor || undefined,
  });
  const files = (listed.objects || []).map((o) => ({
    key: o.key,
    size: o.size,
    uploaded: o.uploaded ? new Date(o.uploaded).toISOString() : null,
    url: publicUrl(env, o.key),
  }));
  return { files, truncated: Boolean(listed.truncated), cursor: listed.cursor || null };
}

/** "report.pdf" → "report-2.pdf" when the key is taken. */
async function uniqueKey(env, key) {
  if (!(await env.BUCKET.head(key))) return key;
  const slash = key.lastIndexOf("/");
  const dot = key.lastIndexOf(".");
  const stem = dot > slash ? key.slice(0, dot) : key;
  const ext = dot > slash ? key.slice(dot) : "";
  for (let i = 2; i < 100; i++) {
    const candidate = `${stem}-${i}${ext}`;
    if (!(await env.BUCKET.head(candidate))) return candidate;
  }
  return `${stem}-${Date.now()}${ext}`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(env, origin);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/api/health") return json({ ok: true }, 200, cors);

    const user = await appwriteUser(env, bearer(request));
    if (!user) return json({ error: "sign in required" }, 401, cors);
    if (!userAllowed(env, user)) {
      return json({ error: "this account is not allowed", user: { id: user.$id, email: user.email } }, 403, cors);
    }

    try {
      if (url.pathname === "/api/whoami") {
        return json({ ok: true, user: { id: user.$id, email: user.email, name: user.name } }, 200, cors);
      }

      if (url.pathname === "/api/list" && request.method === "GET") {
        const data = await listFiles(env, url.searchParams.get("prefix") || "",
                                     url.searchParams.get("limit"), url.searchParams.get("cursor"));
        return json(data, 200, cors);
      }

      if (url.pathname === "/api/upload" && request.method === "POST") {
        const form = await request.formData();
        const uploads = form.getAll("file").filter((f) => typeof f === "object" && f.name);
        if (!uploads.length) return json({ error: "no file in the request" }, 400, cors);

        const prefix = form.get("prefix") || env.UPLOAD_PREFIX || DEFAULT_PREFIX;
        const saved = [];
        for (const file of uploads) {
          if (file.size > MAX_UPLOAD_BYTES) {
            return json({ error: `file too large: ${file.name} (${file.size} bytes)` }, 413, cors);
          }
          const key = await uniqueKey(env, safeKey(file.name, prefix));
          if (!key) return json({ error: `bad file name: ${file.name}` }, 400, cors);
          await env.BUCKET.put(key, await file.arrayBuffer(), {
            httpMetadata: { contentType: file.type || "application/octet-stream" },
          });
          saved.push({ key, size: file.size, url: publicUrl(env, key) });
        }
        return json({ files: saved }, 200, cors);
      }

      if (url.pathname === "/api/delete" && request.method === "POST") {
        const body = await request.json().catch(() => ({}));
        const raw = String(body.key || "");
        if (!raw) return json({ error: "key is required" }, 400, cors);
        if (!safeKey(raw, "") || raw.includes("..")) return json({ error: "bad key" }, 400, cors);
        await env.BUCKET.delete(raw);
        return json({ ok: true, key: raw }, 200, cors);
      }

      return json({ error: "not found" }, 404, cors);
    } catch (err) {
      return json({ error: String((err && err.message) || err) }, 500, cors);
    }
  },
};

// exported for the unit tests
export { corsHeaders, publicUrl, safeKey, userAllowed, appwriteUser, listFiles, uniqueKey };
