// Unit tests for the site API Worker (Node has fetch/Request/FormData/Response).
// Run: node tools/site-api/worker.test.mjs
import worker, {
  safeKey, publicUrl, corsHeaders, tokenOk, cleanItem, mergeVocab, readVocab, writeVocab,
} from "./worker.js";

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
    async put(key, body) {
      const text = typeof body === "string" ? body : "";
      const size = typeof body === "string" ? body.length : (body.byteLength ?? 0);
      store.set(key, { size, text, uploaded: new Date() });
      return { key };
    },
    async delete(key) { store.delete(key); },
    async get(key) {
      const v = store.get(key);
      return v ? { text: async () => v.text, size: v.size, uploaded: v.uploaded } : null;
    },
  };
}

const TOKEN = "test-token-0123456789abcdef";
const ENV = {
  BUCKET: fakeBucket({
    "audio/x/episode.mp3": { size: 100, uploaded: new Date("2026-09-10T09:00:00Z") },
    "tethered-tube-partition.zip": { size: 4301440, uploaded: new Date("2026-09-11T10:00:00Z") },
    "LV0D3D/plain_p1/vtk/plain_00141.vtu": { size: 55, uploaded: new Date("2026-09-09T10:00:00Z") },
  }),
  PRIVATE: fakeBucket(),
  SITE_TOKEN: TOKEN,
  PUBLIC_BASE: "https://bucket.r2.mapengfei.cn",
  ALLOWED_ORIGIN: "https://mapengfei-glasgow.github.io",
  UPLOAD_PREFIX: "uploads",
};

const call = (path, init = {}, env = ENV) =>
  worker.fetch(new Request("https://api.example" + path, init), env);
const auth = (token = TOKEN) => ({ headers: { authorization: "Bearer " + token } });
const post = (path, body, token = TOKEN) => call(path, {
  method: "POST",
  headers: { ...auth(token).headers, "content-type": "application/json" },
  body: JSON.stringify(body),
});

console.log("\nhelpers");
ok("safeKey prefixes a plain name", safeKey("report.pdf", "uploads") === "uploads/report.pdf");
ok("safeKey strips traversal", safeKey("../../etc/passwd", "uploads") === "uploads/etc/passwd");
ok("safeKey keeps the prefix once", safeKey("uploads/a/b.txt", "uploads") === "uploads/a/b.txt");
ok("safeKey rejects empty", safeKey("   ", "uploads") === null);
ok("publicUrl encodes segments", publicUrl(ENV, "a b/c+d.zip") === "https://bucket.r2.mapengfei.cn/a%20b/c%2Bd.zip");
ok("cors only for allowed origin",
  corsHeaders(ENV, "https://evil.example")["access-control-allow-origin"] === "https://mapengfei-glasgow.github.io");

console.log("\nshared-secret auth");
ok("the right token passes", tokenOk(ENV, TOKEN));
ok("a wrong token fails", !tokenOk(ENV, TOKEN + "x"));
ok("a same-length wrong token fails", !tokenOk(ENV, "test-token-0123456789abcdeX"));
ok("an empty token fails", !tokenOk(ENV, ""));
ok("no SITE_TOKEN configured fails closed", !tokenOk({ SITE_TOKEN: "" }, "anything"));
ok("missing SITE_TOKEN counts as unset", !tokenOk({}, TOKEN));

console.log("\ncleanItem / mergeVocab");
ok("cleanItem keeps the known fields",
  (() => { const it = cleanItem({ slug: "s", idx: "3", text: "hi", explain: "note", junk: 1 });
           return it.slug === "s" && it.idx === 3 && it.text === "hi" && !("junk" in it); })());
ok("cleanItem rejects a missing slug", cleanItem({ idx: 1 }) === null);
ok("cleanItem rejects a negative idx", cleanItem({ slug: "s", idx: -1 }) === null);
ok("cleanItem rejects a non-numeric idx", cleanItem({ slug: "s", idx: "x" }) === null);
ok("cleanItem accepts AppWrite's $createdAt",
  cleanItem({ slug: "s", idx: 1, $createdAt: "2026-09-06T00:00:00.000Z" }).savedAt === "2026-09-06T00:00:00.000Z");
ok("mergeVocab dedupes by slug:idx",
  mergeVocab([{ slug: "a", idx: 1, text: "old" }], [{ slug: "a", idx: 1, text: "new" }]).items.length === 1);
ok("mergeVocab lets the incoming record win",
  mergeVocab([{ slug: "a", idx: 1, text: "old" }], [{ slug: "a", idx: 1, text: "new" }]).items[0].text === "new");
ok("mergeVocab counts only new records",
  mergeVocab([{ slug: "a", idx: 1 }], [{ slug: "a", idx: 1 }, { slug: "b", idx: 2 }]).added === 1);
ok("mergeVocab drops unusable records",
  mergeVocab([], [{ slug: "", idx: 1 }, null, { slug: "b", idx: 2 }]).items.length === 1);

const run = async () => {
  console.log("\nauth");
  const health = await (await call("/api/health")).json();
  ok("health is public", health.ok === true);
  ok("no token → 401", (await call("/api/list")).status === 401);
  ok("wrong token → 401", (await call("/api/list", auth("nope"))).status === 401);
  ok("the 401 says which half is wrong",
    (await (await call("/api/list", auth("nope"))).json()).error === "bad sync code");
  ok("an unconfigured Worker says so",
    (await (await call("/api/list", auth("nope"), { ...ENV, SITE_TOKEN: "" })).json()).error
      === "SITE_TOKEN is not configured on the Worker");
  const who = await (await call("/api/whoami", auth())).json();
  ok("whoami identifies the service", who.ok === true && who.service === "site-api");

  console.log("\nlist + pagination");
  const p1 = await (await call("/api/list?limit=2", auth())).json();
  ok("first page has 2 files and a cursor", p1.files.length === 2 && p1.truncated && p1.cursor);
  const p2 = await (await call("/api/list?limit=2&cursor=" + p1.cursor, auth())).json();
  ok("second page continues without overlap",
    p2.files.length === 1 && p2.files[0].key !== p1.files[0].key, JSON.stringify(p2.files.map((f) => f.key)));
  ok("list entries carry size + public url",
    p2.files[0].url.startsWith("https://bucket.r2.mapengfei.cn/"));

  console.log("\nupload + delete");
  const form = new FormData();
  form.append("file", new File([new Uint8Array([1, 2, 3, 4, 5])], "my results.zip", { type: "application/zip" }));
  const up = await (await call("/api/upload", { method: "POST", body: form, ...auth() })).json();
  ok("upload → key under the prefix", up.files[0].key === "uploads/my results.zip", up.files[0].key);
  ok("upload returns the public url", up.files[0].url.endsWith("/uploads/my%20results.zip"));
  ok("upload wrote to the binding", ENV.BUCKET.store.has("uploads/my results.zip"));

  const form2 = new FormData();
  form2.append("file", new File([new Uint8Array([9])], "my results.zip"));
  const up2 = await (await call("/api/upload", { method: "POST", body: form2, ...auth() })).json();
  ok("second upload of the same name → -2", up2.files[0].key === "uploads/my results-2.zip", up2.files[0].key);

  ok("upload without a file → 400",
    (await call("/api/upload", { method: "POST", body: new FormData(), ...auth() })).status === 400);
  ok("upload without auth → 401",
    (await call("/api/upload", { method: "POST", body: new FormData() })).status === 401);

  const del = await post("/api/delete", { key: "uploads/my results.zip" });
  ok("delete → 200 and removes the object",
    del.status === 200 && !ENV.BUCKET.store.has("uploads/my results.zip"));
  ok("delete rejects traversal", (await post("/api/delete", { key: "../../evil" })).status === 400);
  ok("delete without auth → 401",
    (await call("/api/delete", { method: "POST", body: "{}" })).status === 401);

  ok("unknown route → 404", (await call("/api/nope", auth())).status === 404);
  ok("preflight → 204", (await call("/api/list", { method: "OPTIONS" })).status === 204);

  console.log("\nvocabulary");
  const empty = await (await call("/api/vocab", auth())).json();
  ok("an empty book is [] rather than an error", Array.isArray(empty.items) && empty.count === 0);
  ok("no vocab without auth", (await call("/api/vocab")).status === 401);

  const add = await (await post("/api/vocab/add", {
    slug: "2026-09-21-elections", idx: 4, show: "Global News", title: "German Chancellor",
    text: "These are our main stories.", explain: "the headline items",
  })).json();
  ok("add stores the sentence", add.ok === true && add.count === 1);
  ok("add echoes the stored record", add.item.slug === "2026-09-21-elections" && add.item.idx === 4);
  ok("the document lives under vocab/v1.json", ENV.PRIVATE.store.has("vocab/v1.json"));

  const again = await (await post("/api/vocab/add", {
    slug: "2026-09-21-elections", idx: 4, text: "changed",
  })).json();
  ok("re-adding the same sentence upserts instead of duplicating", again.count === 1);
  ok("the upsert keeps the newest text",
    (await (await call("/api/vocab", auth())).json()).items[0].text === "changed");

  const second = await (await post("/api/vocab/add", { slug: "other", idx: 0 })).json();
  ok("a second sentence bumps the count", second.count === 2);
  ok("add rejects a bad record", (await post("/api/vocab/add", { idx: 4 })).status === 400);

  const removed = await (await post("/api/vocab/remove", { slug: "other", idx: 0 })).json();
  ok("remove deletes just that sentence", removed.count === 1 && removed.removed === 1);
  const removedAgain = await (await post("/api/vocab/remove", { slug: "other", idx: 0 })).json();
  ok("removing a missing sentence is a no-op", removedAgain.count === 1 && removedAgain.removed === 0);
  ok("remove needs slug + idx", (await post("/api/vocab/remove", { slug: "x" })).status === 400);

  // the AppWrite export, as it comes out of the console/SDK
  const imported = await (await post("/api/vocab/import", {
    documents: [
      { $id: "d1", $createdAt: "2026-09-06T10:00:00.000Z", slug: "a", idx: 1, text: "one", explain: "note" },
      { $id: "d2", slug: "a", idx: 2, text: "two" },
      { $id: "d3", slug: "2026-09-21-elections", idx: 4, text: "dupe of the stored one" },
    ],
  })).json();
  ok("import merges the export and dedupes", imported.ok === true && imported.count === 3, JSON.stringify(imported));
  ok("import reports what it added", imported.added === 2);
  const book = await (await call("/api/vocab", auth())).json();
  ok("the imported note survives", book.items.some((it) => it.slug === "a" && it.explain === "note"));
  ok("import accepts a bare array too",
    (await (await post("/api/vocab/import", [{ slug: "b", idx: 1 }])).json()).count === 4);
  ok("import needs an array", (await post("/api/vocab/import", { nope: 1 })).status === 400);

  console.log("\nvocabulary storage edge cases");
  ENV.PRIVATE.store.set("vocab/v1.json", { size: 5, text: "{oops", uploaded: new Date() });
  ok("a corrupt document reads as empty instead of throwing",
    (await (await call("/api/vocab", auth())).json()).count === 0);
  ENV.PRIVATE.store.delete("vocab/v1.json");
  ok("no PRIVATE binding → 503 with a readable reason",
    (await (await call("/api/vocab", auth(), { ...ENV, PRIVATE: undefined })).json()).error
      === "the PRIVATE R2 binding is not configured");

  const tooMany = Array.from({ length: 5001 }, (_, i) => ({ slug: "s", idx: i }));
  const refused = await writeVocab(ENV, tooMany).then(() => null).catch((e) => e);
  ok("writeVocab enforces the item limit", refused && refused.status === 413, String(refused));

  ok("a bare array document still reads",
    await (async () => {
      ENV.PRIVATE.store.set("vocab/v1.json", { text: JSON.stringify([{ slug: "z", idx: 1 }]), size: 10 });
      const doc = await readVocab(ENV);
      ENV.PRIVATE.store.delete("vocab/v1.json");
      return doc.items.length === 1;
    })());

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
};
run();
