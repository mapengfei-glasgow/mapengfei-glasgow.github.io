/**
 * Site API for the listening site — one Worker behind two pages:
 *
 *   /files/   the R2 bucket browser  (GET /api/list, POST /api/upload, /api/delete)
 *   /words/   the vocabulary book    (GET /api/vocab, POST /api/vocab/add, …)
 *   ☆        the episode pages       (POST /api/vocab/add | /api/vocab/remove)
 *
 * Auth: ONE shared secret — `Authorization: Bearer <SITE_TOKEN>`, compared in
 * constant time; the browser keeps it in localStorage and you type it once per
 * device. There are no accounts and no sign-up, so nothing here is reachable by
 * a stranger who registers.
 *
 * Why AppWrite is gone: this Worker used to verify an AppWrite JWT, and the
 * vocabulary book lived in an AppWrite collection. AppWrite's free plan pauses
 * projects after 7 days without *development activity in the Console* — API
 * traffic, SDK calls and visitor traffic explicitly do not count, and the
 * detection is deliberately not published — so one idle week silently took both
 * pages down. Everything now lives in Cloudflare, which does not sleep.
 *
 * Routes:
 *   GET    /api/health                    → { ok: true }                  (no auth)
 *   GET    /api/whoami                    → { ok: true, service }
 *   GET    /api/list?prefix=&limit=&cursor= → { files: [...], truncated, cursor }
 *   POST   /api/upload                    → multipart/form-data (`file` fields, `prefix`)
 *   POST   /api/delete                    → JSON { key }
 *   GET    /api/vocab                     → { items: [...], count }
 *   POST   /api/vocab/add                 → JSON { slug, idx, show, title, text, explain }
 *   POST   /api/vocab/remove              → JSON { slug, idx }
 *   POST   /api/vocab/import              → JSON { items: [...] }  (merge, dedupes)
 *
 * Worker vars:
 *   SITE_TOKEN      the shared secret (set it as a *Secret*; empty = nobody gets in)
 *   PUBLIC_BASE     https://bucket.r2.mapengfei.cn
 *   ALLOWED_ORIGIN  https://mapengfei-glasgow.github.io
 *   UPLOAD_PREFIX   uploads
 * Bindings:
 *   BUCKET   → the public R2 bucket (audio, uploads)
 *   PRIVATE  → a PRIVATE R2 bucket; the vocabulary is one object in it
 *              (`vocab/v1.json`), never reachable through the public bucket domain
 *
 * The vocabulary is a single JSON object, read-modify-written per change. That is
 * deliberate: it is one person's list, so there is no contention to lose, and a
 * toggle stays one read plus one write. R2 (unlike KV) is read-after-write
 * consistent, so a star tapped a moment ago is still there on the next page load.
 */

const DEFAULT_PREFIX = "uploads";
const MAX_UPLOAD_BYTES = 95 * 1024 * 1024; // Workers request body limit is ~100 MB
const VOCAB_KEY = "vocab/v1.json";
const VOCAB_MAX_ITEMS = 5000;
const VOCAB_MAX_BYTES = 2 * 1024 * 1024;   // the whole document, serialised

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

function bearer(request) {
  return (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
}

/**
 * Is the shared secret right? Byte-wise constant time, so a wrong guess cannot be
 * narrowed down by how long the comparison took.
 *
 * Failing CLOSED when SITE_TOKEN is unset is the important half: the old AppWrite
 * version treated an empty allowlist as "any signed-in user", and open sign-up
 * made that "anyone on the internet".
 */
function tokenOk(env, given) {
  const want = env.SITE_TOKEN;
  if (!want || !given) return false;
  const a = new TextEncoder().encode(String(want));
  const b = new TextEncoder().encode(String(given));
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
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

/* ---------- vocabulary document ---------- */

function privateBucket(env) {
  if (!env.PRIVATE) {
    const err = new Error("the PRIVATE R2 binding is not configured");
    err.status = 503;
    throw err;
  }
  return env.PRIVATE;
}

function clip(value, max) {
  const s = value == null ? "" : String(value);
  return s.length > max ? s.slice(0, max) : s;
}

/**
 * One stored sentence, or null when the record is unusable. The field names are
 * the old AppWrite collection's, so an export of that data imports unchanged.
 */
function cleanItem(raw) {
  if (!raw || typeof raw !== "object") return null;
  const slug = clip(raw.slug, 128).trim();
  const idx = parseInt(raw.idx, 10);
  if (!slug || !Number.isFinite(idx) || idx < 0) return null;
  return {
    slug,
    idx,
    show: clip(raw.show, 128),
    title: clip(raw.title, 256),
    text: clip(raw.text, 4096),
    explain: clip(raw.explain, 32768),
    savedAt: clip(raw.savedAt || raw.$createdAt || new Date().toISOString(), 40),
  };
}

const itemKey = (item) => `${item.slug}:${item.idx}`;

async function readVocab(env) {
  const obj = await privateBucket(env).get(VOCAB_KEY);
  if (!obj) return { items: [], updated: null };
  let doc;
  try {
    doc = JSON.parse(await obj.text());
  } catch (err) {
    return { items: [], updated: null, corrupt: true };
  }
  const items = Array.isArray(doc) ? doc : doc.items;
  return {
    items: (Array.isArray(items) ? items : []).map(cleanItem).filter(Boolean),
    updated: (doc && doc.updated) || null,
  };
}

async function writeVocab(env, items) {
  if (items.length > VOCAB_MAX_ITEMS) {
    const err = new Error(`too many saved sentences (limit ${VOCAB_MAX_ITEMS})`);
    err.status = 413;
    throw err;
  }
  const body = JSON.stringify({ v: 1, updated: new Date().toISOString(), items });
  if (body.length > VOCAB_MAX_BYTES) {
    const err = new Error("the vocabulary book is too large");
    err.status = 413;
    throw err;
  }
  await privateBucket(env).put(VOCAB_KEY, body, {
    httpMetadata: { contentType: "application/json; charset=utf-8" },
  });
  return items.length;
}

/** Merge incoming records into the stored ones, keyed by slug:idx. */
function mergeVocab(existing, incoming) {
  const byKey = new Map(existing.map((it) => [itemKey(it), it]));
  let added = 0;
  for (const raw of incoming) {
    const item = cleanItem(raw);
    if (!item) continue;
    const key = itemKey(item);
    if (byKey.has(key)) byKey.set(key, { ...byKey.get(key), ...item });
    else { byKey.set(key, item); added++; }
  }
  return { items: [...byKey.values()], added };
}

const readJson = (request) => request.json().catch(() => ({}));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(env, origin);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/api/health") return json({ ok: true }, 200, cors);

    if (!tokenOk(env, bearer(request))) {
      const why = env.SITE_TOKEN ? "bad sync code" : "SITE_TOKEN is not configured on the Worker";
      return json({ error: why }, 401, cors);
    }

    try {
      if (url.pathname === "/api/whoami") {
        return json({ ok: true, service: "site-api" }, 200, cors);
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
        const body = await readJson(request);
        const raw = String(body.key || "");
        if (!raw) return json({ error: "key is required" }, 400, cors);
        if (!safeKey(raw, "") || raw.includes("..")) return json({ error: "bad key" }, 400, cors);
        await env.BUCKET.delete(raw);
        return json({ ok: true, key: raw }, 200, cors);
      }

      if (url.pathname === "/api/vocab" && request.method === "GET") {
        const doc = await readVocab(env);
        return json({ items: doc.items, count: doc.items.length, updated: doc.updated }, 200, cors);
      }

      if (url.pathname === "/api/vocab/add" && request.method === "POST") {
        const item = cleanItem(await readJson(request));
        if (!item) return json({ error: "slug and a non-negative idx are required" }, 400, cors);
        const doc = await readVocab(env);
        const { items } = mergeVocab(doc.items, [item]);
        const count = await writeVocab(env, items);
        return json({ ok: true, item, count }, 200, cors);
      }

      if (url.pathname === "/api/vocab/remove" && request.method === "POST") {
        const body = await readJson(request);
        const slug = clip(body.slug, 128).trim();
        const idx = parseInt(body.idx, 10);
        if (!slug || !Number.isFinite(idx)) {
          return json({ error: "slug and idx are required" }, 400, cors);
        }
        const doc = await readVocab(env);
        const items = doc.items.filter((it) => itemKey(it) !== `${slug}:${idx}`);
        const count = await writeVocab(env, items);
        return json({ ok: true, count, removed: doc.items.length - items.length }, 200, cors);
      }

      if (url.pathname === "/api/vocab/import" && request.method === "POST") {
        const body = await readJson(request);
        // Accept the AppWrite export as it comes: { items } | { documents } | [ … ].
        const incoming = Array.isArray(body) ? body
          : Array.isArray(body.items) ? body.items
          : Array.isArray(body.documents) ? body.documents
          : null;
        if (!incoming) return json({ error: "expected an array of saved sentences" }, 400, cors);
        const doc = await readVocab(env);
        const { items, added } = mergeVocab(doc.items, incoming);
        const count = await writeVocab(env, items);
        return json({ ok: true, count, added, skipped: incoming.length - added }, 200, cors);
      }

      return json({ error: "not found" }, 404, cors);
    } catch (err) {
      return json({ error: String((err && err.message) || err) }, (err && err.status) || 500, cors);
    }
  },
};

// exported for the unit tests
export {
  corsHeaders, publicUrl, safeKey, tokenOk, listFiles, uniqueKey,
  cleanItem, mergeVocab, readVocab, writeVocab,
};
