// Unit tests for the R2 portal Worker (Node 24 has fetch/Request/FormData/Response).
// Run: node tools/r2-portal/worker.test.mjs
import worker, { safeKey, publicUrl, corsHeaders, userAllowed, appwriteUser } from "./worker.js";

let pass = 0, fail = 0;
const ok = (name, cond, extra = "") => {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  → " + extra : "")); }
};

// ---- a fake R2 bucket binding -------------------------------------------------
function fakeBucket(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    store,
    async list({ prefix, cursor } = {}) {
      const all = [...store.entries()]
        .filter(([k]) => !prefix || k.startsWith(prefix))
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, v]) => ({ key, size: v.size, uploaded: v.uploaded }));
      const start = cursor ? Number(cursor) : 0;
      const page = all.slice(start, start + 2);          // pages of 2, to exercise cursors
      const next = start + 2 < all.length ? String(start + 2) : null;
      return { objects: page, truncated: Boolean(next), cursor: next };
    },
    async head(key) { const v = store.get(key); return v ? { key, size: v.size } : null; },
    async put(key, body) { store.set(key, { size: body.byteLength ?? 0, uploaded: new Date() }); return { key }; },
    async delete(key) { store.delete(key); },
  };
}

const ENV = {
  BUCKET: fakeBucket({
    "audio/x/episode.mp3": { size: 100, uploaded: new Date("2026-09-10T09:00:00Z") },
    "tethered-tube-partition.zip": { size: 4301440, uploaded: new Date("2026-09-11T10:00:00Z") },
    "LV0D3D/plain_p1/vtk/plain_00141.vtu": { size: 55, uploaded: new Date("2026-09-09T10:00:00Z") },
  }),
  APPWRITE_ENDPOINT: "https://fra.cloud.appwrite.io/v1",
  APPWRITE_PROJECT: "proj-test",
  ALLOWED_USERS: "aa",
  PUBLIC_BASE: "https://bucket.r2.mapengfei.cn",
  ALLOWED_ORIGIN: "https://mapengfei-glasgow.github.io",
  UPLOAD_PREFIX: "uploads",
};

// ---- stub the AppWrite verification call --------------------------------------
const USERS = {
  "jwt-aa": { $id: "aa", email: "aa@example.com", name: "aa" },
  "jwt-other": { $id: "someone", email: "other@example.com", name: "Other" },
};
const realFetch = globalThis.fetch;
let appwriteCalls = 0;
globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  if (url.startsWith("https://fra.cloud.appwrite.io/v1/account")) {
    appwriteCalls++;
    const jwt = (init.headers && (init.headers["X-Appwrite-JWT"] || init.headers["x-appwrite-jwt"])) || "";
    const user = USERS[jwt];
    return new Response(JSON.stringify(user || { message: "unauthorized" }), { status: user ? 200 : 401 });
  }
  return realFetch(input, init);
};

const call = (path, init = {}, env = ENV) =>
  worker.fetch(new Request("https://portal.example" + path, init), env);
const auth = (jwt) => ({ headers: { authorization: "Bearer " + jwt } });

console.log("\nhelpers");
ok("safeKey prefixes a plain name", safeKey("report.pdf", "uploads") === "uploads/report.pdf");
ok("safeKey strips traversal", safeKey("../../etc/passwd", "uploads") === "uploads/etc/passwd");
ok("safeKey keeps the prefix once", safeKey("uploads/a/b.txt", "uploads") === "uploads/a/b.txt");
ok("safeKey rejects empty", safeKey("   ", "uploads") === null);
ok("publicUrl encodes segments", publicUrl(ENV, "a b/c+d.zip") === "https://bucket.r2.mapengfei.cn/a%20b/c%2Bd.zip");
ok("cors only for allowed origin",
  corsHeaders(ENV, "https://evil.example")["access-control-allow-origin"] === "https://mapengfei-glasgow.github.io");
ok("allowlist matches the id", userAllowed(ENV, USERS["jwt-aa"]));
ok("allowlist rejects others", !userAllowed(ENV, USERS["jwt-other"]));
ok("empty allowlist allows any signed-in user", userAllowed({ ALLOWED_USERS: "" }, USERS["jwt-other"]));
ok("allowlist can match an email", userAllowed({ ALLOWED_USERS: "aa@example.com" }, USERS["jwt-aa"]));
ok("allowlist is case-insensitive", userAllowed({ ALLOWED_USERS: "AA" }, USERS["jwt-aa"]));

const run = async () => {
  console.log("\nauth");
  const health = await (await call("/api/health")).json();
  ok("health is public", health.ok === true);
  ok("no token → 401", (await call("/api/list")).status === 401);
  ok("garbage jwt → 401", (await call("/api/list", auth("nope"))).status === 401);
  const denied = await call("/api/list", auth("jwt-other"));
  ok("valid jwt but not allowlisted → 403", denied.status === 403);
  ok("403 says which account was refused",
    (await denied.json()).user.email === "other@example.com");

  const who = await (await call("/api/whoami", auth("jwt-aa"))).json();
  ok("whoami returns the user", who.user.id === "aa" && who.ok === true);

  console.log("\nlist + pagination");
  const p1 = await (await call("/api/list?limit=2", auth("jwt-aa"))).json();
  ok("first page has 2 files and a cursor", p1.files.length === 2 && p1.truncated && p1.cursor);
  const p2 = await (await call("/api/list?limit=2&cursor=" + p1.cursor, auth("jwt-aa"))).json();
  ok("second page continues without overlap",
    p2.files.length === 1 && p2.files[0].key !== p1.files[0].key, JSON.stringify(p2.files.map((f) => f.key)));
  ok("list entries carry size + public url",
    p2.files[0].url.startsWith("https://bucket.r2.mapengfei.cn/"));

  const cached = appwriteCalls;
  await call("/api/list", auth("jwt-aa"));
  ok("verified jwts are cached (no extra AppWrite call)", appwriteCalls === cached);

  console.log("\nupload + delete");
  const form = new FormData();
  form.append("file", new File([new Uint8Array([1, 2, 3, 4, 5])], "my results.zip", { type: "application/zip" }));
  const up = await (await call("/api/upload", { method: "POST", body: form, ...auth("jwt-aa") })).json();
  ok("upload → key under the prefix", up.files[0].key === "uploads/my results.zip", up.files[0].key);
  ok("upload returns the public url", up.files[0].url.endsWith("/uploads/my%20results.zip"));
  ok("upload wrote to the binding", ENV.BUCKET.store.has("uploads/my results.zip"));

  const form2 = new FormData();
  form2.append("file", new File([new Uint8Array([9])], "my results.zip"));
  const up2 = await (await call("/api/upload", { method: "POST", body: form2, ...auth("jwt-aa") })).json();
  ok("second upload of the same name → -2", up2.files[0].key === "uploads/my results-2.zip", up2.files[0].key);

  ok("upload without a file → 400",
    (await call("/api/upload", { method: "POST", body: new FormData(), ...auth("jwt-aa") })).status === 400);
  ok("upload without auth → 401",
    (await call("/api/upload", { method: "POST", body: new FormData() })).status === 401);

  const del = await call("/api/delete", {
    method: "POST", headers: { ...auth("jwt-aa").headers, "content-type": "application/json" },
    body: JSON.stringify({ key: "uploads/my results.zip" }),
  });
  ok("delete → 200 and removes the object",
    del.status === 200 && !ENV.BUCKET.store.has("uploads/my results.zip"));
  const badDel = await call("/api/delete", {
    method: "POST", headers: { ...auth("jwt-aa").headers, "content-type": "application/json" },
    body: JSON.stringify({ key: "../../evil" }),
  });
  ok("delete rejects traversal", badDel.status === 400);
  ok("delete without auth → 401",
    (await call("/api/delete", { method: "POST", body: "{}" })).status === 401);

  ok("unknown route → 404", (await call("/api/nope", auth("jwt-aa"))).status === 404);
  ok("preflight → 204", (await call("/api/list", { method: "OPTIONS" })).status === 204);

  console.log("\nappwrite verification");
  ok("appwriteUser returns null for an unknown jwt", (await appwriteUser(ENV, "jwt-nope")) === null);
  globalThis.fetch = realFetch;
  ok("appwriteUser survives a network error",
    (await appwriteUser({ ...ENV, APPWRITE_ENDPOINT: "https://127.0.0.1:1" }, "jwt-uncached")) === null);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
};
run();
