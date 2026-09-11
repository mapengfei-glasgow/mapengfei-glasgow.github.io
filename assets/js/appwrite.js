/* Vocabulary book via AppWrite — static-site integration (no build step).
 *
 * Backend (AppWrite Cloud, fra region) is configured (2026-09-06):
 *   1. Authentication → Methods: Email & Password enabled (signup/signin verified E2E).
 *      Anonymous sessions are off: the guests role on this deployment lacks the
 *      account scope, so the site only offers email signup / sign-in.
 *      Note: AppWrite 2.0 self-signup requires a client-supplied userId (username);
 *      the form asks for 1–36 characters (the server accepts as few as 1).
 *   2. Database `site` / collection `vocab`, attributes:
 *        slug    String  128  (episode slug)
 *        idx     Integer          (sentence index, 0-based)
 *        show    String  128  (show name)
 *        title   String  256  (episode title)
 *        text    String  4096 (sentence text)
 *        explain String  32768 (plain-English note, nullable)
 *      Index idx_slug (slug, idx); documentSecurity=true; collection create("users"),
 *      and documents get read/update/delete("user:<creator>") (2.0 has no owner role).
 *   3. Web platform created (hostname=mapengfei-glasgow.github.io); origin verified.
 *
 * Key AppWrite 2.0 vs 1.x differences (this site uses SDK 26.2.0):
 *   - self-signup must pass a userId (≤36 chars of [a-zA-Z0-9._-], leading letter/digit)
 *   - signup does not sign you in; call /account/sessions/email afterwards
 *   - document path: /databases/{db}/collections/{coll}/documents; create payload under data
 *   - listDocuments(db, coll, queries, transactionId, total, ttl); limit via Query.limit()
 *   - session fallback: x-fallback-cookies header (JSON) → localStorage → X-Fallback-Cookies header
 */
(function () {
  "use strict";

  var CONFIG = {
    endpoint: "https://fra.cloud.appwrite.io/v1",
    projectId: "6a9d0e7c002b1fabe1e9",
    db: "site",
    collection: "vocab"
  };

  if (!CONFIG.projectId || CONFIG.projectId === "YOUR_PROJECT_ID") return;
  document.documentElement.dataset.vocab = "on";

  var SDK_URL = "https://cdn.jsdelivr.net/npm/appwrite@26.2.0/dist/iife/sdk.js";

  var account = null, dbSvc = null, user = null;
  var sdkPromise = null, sessionPromise = null, docCache = null, docLoad = null;
  var modal = null, mode = "login";

  /* ---------- Lazy SDK loading (fetch the 469KB SDK only when needed) ---------- */

  function loadSDK() {
    if (window.Appwrite && window.Appwrite.Client) return Promise.resolve(window.Appwrite);
    if (!sdkPromise) {
      sdkPromise = new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = SDK_URL;
        s.async = true;
        s.onload = function () { resolve(window.Appwrite); };
        s.onerror = function () { sdkPromise = null; reject(new Error("Failed to load the AppWrite SDK")); };
        document.head.appendChild(s);
      });
    }
    return sdkPromise;
  }

  function initClient() {
    // note: the 2.0 Client constructor takes no arguments (1.x's new Client({...}) is
    // silently ignored and requests hit the default US region); configure via setters
    var AW = window.Appwrite;
    var client = new AW.Client().setEndpoint(CONFIG.endpoint).setProject(CONFIG.projectId);
    account = new AW.Account(client);
    dbSvc = new AW.Databases(client);
  }

  // restore/confirm the session (a previous session may be in cookie or localStorage)
  function ensureSession() {
    if (!sessionPromise) {
      sessionPromise = loadSDK().then(function () {
        initClient();
        return account.get();
      }).then(function (u) {
        user = u; updateChip(); return true;
      }).catch(function () {
        user = null; updateChip(); return false;
      });
    }
    return sessionPromise;
  }

  function loggedIn() { return !!user; }

  /* ---------- Header button ---------- */

  function chip() { return document.getElementById("auth-chip"); }

  function updateChip() {
    var c = chip();
    if (c) {
      c.hidden = false;
      if (user) {
        c.textContent = "📖 " + (user.name || user.email || "Vocabulary");
        c.title = "My vocabulary (" + (user.email || user.name) + ")";
        c.dataset.state = "in";
      } else {
        c.textContent = "Sign in";
        c.title = "Sign in / sign up to sync saved sentences across devices";
        c.dataset.state = "out";
      }
    }
    fireAuth();
  }

  function fireAuth() {
    document.dispatchEvent(new CustomEvent("ds-auth", { detail: { user: user } }));
  }

  /* ---------- Auth modal ---------- */

  function openModal(m) {
    if (!modal) return;
    setTab(m || "login");
    modal.hidden = false;
    document.body.classList.add("modal-open");
    var f = modal.querySelector(mode === "signup" ? "#auth-uid" : "#auth-email");
    if (f) f.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
  }

  function setTab(m) {
    mode = m;
    modal.querySelectorAll(".auth-tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.mode === m);
    });
    var name = modal.querySelector("#auth-name");
    if (name) name.hidden = (m !== "signup");
    var uid = modal.querySelector("#auth-uid");
    if (uid) uid.hidden = (m !== "signup");
    var pw = modal.querySelector("#auth-password");
    if (pw) pw.autocomplete = (m === "signup" ? "new-password" : "current-password");
    var sub = modal.querySelector(".auth-submit");
    if (sub) sub.textContent = (m === "signup" ? "Sign up & sign in" : "Sign in");
    var title = modal.querySelector("#auth-title");
    if (title) title.textContent = (m === "signup" ? "Create account" : "Sign in");
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
  }

  function fail(msg) {
    var err = modal && modal.querySelector("#auth-err");
    if (err) err.textContent = msg;
  }

  var UID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$/;

  function errMsg(e) {
    var m = (e && e.message) || String(e);
    var t = (e && e.type) || "";
    if (t === "user_already_exists" || (/userid|user.*id/i.test(m) && /exist|already/i.test(m))) return "That username is already taken — try another one.";
    if (/duplicate|already (exists|used)|user.exists/i.test(m)) return "That email is already registered — switch to “Sign in”.";
    if (t === "user_invalid_credentials" || /password|credentials/i.test(m)) return "Wrong email or password.";
    if (/valid.*email|email.*valid/i.test(m)) return "That email address does not look right.";
    return m;
  }

  function finishAuth() {
    return account.get().then(function (u) {
      user = u;
      closeModal();
      updateChip();
    });
  }

  function wireModal() {
    modal = document.getElementById("auth-modal");
    if (!modal || modal.dataset.wired === "1") return;
    modal.dataset.wired = "1";
    modal.querySelector("#auth-close").addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    });
    modal.querySelectorAll(".auth-tab").forEach(function (b) {
      b.addEventListener("click", function () { setTab(b.dataset.mode); });
    });

    modal.querySelector("#auth-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var email = modal.querySelector("#auth-email").value.trim();
      var password = modal.querySelector("#auth-password").value;
      var name = (modal.querySelector("#auth-name").value || "").trim();
      var uidEl = modal.querySelector("#auth-uid");
      var uid = uidEl ? uidEl.value.trim() : "";
      if (mode === "signup" && !UID_RE.test(uid)) {
        fail("Username: 1–36 characters, starting with a letter or digit; letters, digits, underscore, hyphen and dot are allowed.");
        return;
      }
      var btn = modal.querySelector(".auth-submit");
      btn.disabled = true;
      btn.textContent = "Please wait…";
      ensureSession().then(function () {
        if (mode === "login") {
          return account.createEmailPasswordSession(email, password).then(finishAuth);
        }
        // AppWrite 2.0: self-signup must pass userId (the username)
        return account.create(uid, email, password, name || email.split("@")[0])
          .then(function () {
            // make sure a session exists after signup (fallback sign-in)
            return account.get().catch(function () {
              return account.createEmailPasswordSession(email, password);
            });
          }).then(finishAuth);
      }).catch(function (err) {
        // note: setTab clears #auth-err, so a tab switch must happen before fail(),
        // and setTab must not run afterwards or the error message is swallowed
        if (mode === "signup" && /duplicate|already (exists|used)|user.exists|user_already_exists/i.test(((err && err.message) || "") + " " + ((err && err.type) || ""))) {
          setTab("login");
          fail("That email is already registered — just sign in.");
        } else {
          fail(errMsg(err));
        }
      }).then(function () {
        btn.disabled = false;
        btn.textContent = (mode === "signup" ? "Sign up & sign in" : "Sign in");
      });
    });

  }

  /* ---------- Vocabulary data ---------- */

  /* Single-flight: concurrent callers share one promise. The old version stored a
     truthy {} placeholder before the request, so a second caller ("is it cached?")
     saw an empty cache and rendered the empty state while the request was still in
     flight — and nothing hid it again once the real documents arrived. */
  function loadDocs() {
    if (docLoad) return docLoad;
    docLoad = loadSDK().then(function () {
      initClient();
      // 2.0 signature: listDocuments(databaseId, collectionId, queries, transactionId, total, ttl)
      return dbSvc.listDocuments(CONFIG.db, CONFIG.collection, [window.Appwrite.Query.limit(250)]);
    }).then(function (res) {
      var cache = {};
      (res.documents || []).forEach(function (d) {
        cache[d.slug + ":" + d.idx] = d;
      });
      docCache = cache;
      return docCache;
    }).catch(function (e) {
      console.warn("vocab load failed:", (e && e.message) || e);
      docLoad = null;                  // allow a retry on the next call
      docCache = docCache || {};
      return docCache;
    });
    return docLoad;
  }

  /* ---------- Episode pages: the ☆ save button ---------- */

  function slug() {
    var art = document.querySelector(".episode");
    return art ? art.dataset.slug : null;
  }

  function makeStar(li) {
    var btn = li.querySelector(".star");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.className = "star";
      btn.textContent = "☆";
      btn.setAttribute("aria-label", "Save this sentence");
      li.appendChild(btn);
    }
    return btn;
  }

  function hydrateStars() {
    var art = document.querySelector(".episode");
    if (!art || !art.dataset.slug) return;
    var s = art.dataset.slug;
    loadDocs().then(function () {
      art.querySelectorAll(".sentence").forEach(function (li) {
        var btn = li.querySelector(".star");
        if (btn && docCache[s + ":" + li.dataset.i]) {
          btn.classList.add("on");
          btn.textContent = "★";
        }
      });
    });
  }

  function toggleStar(li, btn) {
    var s = slug();
    if (!s) return;
    if (!loggedIn()) { openModal("login"); return; }
    var key = s + ":" + li.dataset.i;
    var textEl = li.querySelector(".text");
    var exEl = li.querySelector(".explain");
    btn.disabled = true;
    loadSDK().then(function () {
      initClient();
      var d = docCache && docCache[key];
      if (d) return dbSvc.deleteDocument(CONFIG.db, CONFIG.collection, d.$id);
      // 2.0: without explicit permissions the server grants the creator read/update/delete
      // (collection create("users") + documentSecurity=true keeps each document private)
      return dbSvc.createDocument(CONFIG.db, CONFIG.collection, window.Appwrite.ID.unique(), {
        slug: s,
        idx: parseInt(li.dataset.i, 10),
        show: (li.closest(".episode").dataset.show || ""),
        title: (li.closest(".episode").dataset.title || ""),
        text: textEl ? textEl.textContent.trim() : "",
        explain: exEl ? exEl.textContent.trim() : ""
      });
    }).then(function (res) {
      var nowOn = !(docCache && docCache[key]);
      if (!docCache) docCache = {};
      if (nowOn && res && res.$id) docCache[key] = res;
      else delete docCache[key];
      btn.classList.toggle("on", nowOn);
      btn.textContent = nowOn ? "★" : "☆";
    }).catch(function (err) {
      console.warn("star failed:", (err && err.message) || err);
      btn.title = "⚠ Could not save: " + ((err && err.message) || err);
      setTimeout(function () { btn.title = ""; }, 4000);
    }).then(function () {
      btn.disabled = false;
    });
  }

  function wireStars() {
    var art = document.querySelector(".episode");
    if (!art || !art.dataset.slug) return;
    var ol = art.querySelector("ol.sentences");
    if (!ol || ol.dataset.wired === "1") return;
    ol.dataset.wired = "1";
    art.querySelectorAll(".sentence").forEach(makeStar);
    ol.addEventListener("click", function (e) {
      var t = e.target;
      var btn = t && t.closest ? t.closest(".star") : null;
      if (!btn) return;
      e.stopPropagation();
      var li = btn.closest(".sentence");
      toggleStar(li, btn);
    });
    document.addEventListener("ds-auth", function (ev) {
      if (ev.detail && ev.detail.user) hydrateStars();
    });
  }

  /* ---------- /words/ page ---------- */

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  /* Episode pages live under a base path (baseURL-safe); read it from the markup. */
  function episodesBase() {
    var box = document.getElementById("vocab-list");
    var b = (box && box.dataset.episodesBase) || "/episodes/";
    return b.charAt(b.length - 1) === "/" ? b : b + "/";
  }

  function wireVocabPage() {
    var box = document.getElementById("vocab-list");
    if (!box || box.dataset.wired === "1") return;
    box.dataset.wired = "1";
    var empty = document.getElementById("vocab-empty");
    var logout = document.getElementById("vocab-logout");

    function render() {
      if (logout) logout.hidden = !user;
      if (!user) {
        box.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      loadDocs().then(function () {
        var docs = Object.keys(docCache || {}).map(function (k) { return docCache[k]; })
          .sort(function (a, b) {
            return String(b.$createdAt || "").localeCompare(String(a.$createdAt || ""));
          });
        if (!docs.length) {
          box.innerHTML = "";
          if (empty) empty.hidden = false;
          return;
        }
        if (empty) empty.hidden = true;  // we have items: make sure the empty note is gone
        var base = episodesBase();
        box.innerHTML = docs.map(function (d) {
          return '<li class="vocab-item" data-slug="' + esc(d.slug) + '" data-idx="' + esc(d.idx) + '">' +
            '<div class="vocab-head">' +
              '<a class="vocab-ep" href="' + esc(base) + esc(d.slug) + '/">' +
                esc(d.show || "") + " · " + esc(d.title || d.slug) +
              '</a>' +
              '<span class="vocab-actions">' +
                '<button class="vocab-play" type="button" title="Play from this sentence" aria-label="Play from this sentence">▶</button>' +
                '<button class="vocab-del" data-id="' + esc(d.$id) + '" title="Delete">✕</button>' +
              '</span>' +
            '</div>' +
            '<p class="vocab-text" title="Click to play from this sentence">' + esc(d.text) + '</p>' +
            (d.explain ? '<p class="vocab-explain">💡 ' + esc(d.explain) + '</p>' : "") +
            '</li>';
        }).join("");
        box.querySelectorAll(".vocab-del").forEach(function (b) {
          b.addEventListener("click", function () {
            b.disabled = true;
            dbSvc.deleteDocument(CONFIG.db, CONFIG.collection, b.dataset.id)
              .then(function () {
                var k;
                for (k in docCache) if (docCache[k].$id === b.dataset.id) delete docCache[k];
                render();
              })
              .catch(function (err) { console.warn("delete failed:", (err && err.message) || err); })
              .then(function () { b.disabled = false; });
          });
        });
      });
    }

    if (logout) logout.addEventListener("click", function () {
      if (!account) return;
      account.deleteSessions().then(function () {
        user = null;
        docCache = null;
        docLoad = null;
        updateChip();
        render();
      }).catch(function (err) { console.warn("logout failed:", (err && err.message) || err); });
    });

    /* Play a saved sentence: load that episode into the bottom player, then play
       from this sentence's index. Nothing extra is stored in AppWrite — the
       timestamps come from the episode page the player fetches on demand. */
    function playSavedItem(li) {
      var EP = window.EpisodePlayer;
      if (!EP || !EP.loadFromPage) return;
      var slug = li.dataset.slug || "";
      var idx = parseInt(li.dataset.idx || "-1", 10);
      if (!slug || idx < 0) return;
      var st = EP.state ? EP.state() : {};
      // Same episode AND its sentences are known: seek (or pause if it is already
      // playing this very sentence). Otherwise load the episode page first —
      // a restored player knows the slug but not the sentence timings.
      if (st.has && st.slug === slug && st.sentences > 0) {
        if (st.playing && st.idx === idx) { EP.pause(); return; }
        EP.playFrom(idx, EP.autoNext);
        return;
      }
      EP.loadFromPage(episodesBase() + encodeURIComponent(slug) + "/")
        .then(function () { EP.playFrom(idx, EP.autoNext); })
        .catch(function (err) { console.warn("could not load episode:", (err && err.message) || err); });
    }

    /* One delegated click handler: the play button and the sentence text both
       start playback from that saved sentence (re-renders need no re-wiring). */
    box.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      if (t.closest(".vocab-del") || t.closest(".vocab-ep")) return; // they handle themselves
      var li = t.closest(".vocab-item");
      if (!li) return;
      if (t.closest(".vocab-play") || t.closest(".vocab-text")) playSavedItem(li);
    });

    /* Reflect the player state: highlight whichever saved sentence is playing. */
    document.addEventListener("ds-player-change", function (ev) {
      var d = ev.detail || {};
      Array.prototype.forEach.call(box.querySelectorAll(".vocab-item"), function (li) {
        var same = !!d.slug && li.dataset.slug === d.slug && String(d.idx) === String(li.dataset.idx);
        li.classList.toggle("playing", same);
        li.classList.toggle("paused", same && !d.playing);
        var btn = li.querySelector(".vocab-play");
        if (btn) {
          btn.textContent = same && d.playing ? "⏸" : "▶";
          btn.title = same && d.playing ? "Pause" : "Play from this sentence";
        }
      });
    });

    render();
    document.addEventListener("ds-auth", render);
  }

  /* ---------- Boot ---------- */

  function init() {
    wireModal();
    wireStars();
    wireVocabPage();

    var c = chip();
    if (c && c.dataset.wired !== "1") {
      c.dataset.wired = "1";
      c.addEventListener("click", function () {
        if (loggedIn()) {
          // use Turbo navigation when available (keeps the bottom bar alive), else a normal link
          if (window.Turbo && window.Turbo.visit) window.Turbo.visit("/words/");
          else location.href = "/words/";
          return;
        }
        ensureSession().then(function (ok) {
          if (!ok) openModal("login");
        });
      });
    }

    var hint = null;
    try { hint = localStorage.getItem("cookieFallback"); } catch (e) {}
    if (hint) {
      // a previous session may exist; restore it silently. ensureSession is cached,
      // but the chip is a fresh node after navigation, so refresh it every time
      ensureSession().then(function () { updateChip(); });
    } else {
      updateChip();    // no session trace → show "Sign in"
    }
  }

  /* ---------- Public API for other pages (the /files/ portal) ----------
     The R2 portal Worker authenticates with an AppWrite JWT, so the portal page
     needs the current session without re-implementing sign-in. */

  var jwtCache = null; // { jwt, until }

  window.SiteAuth = {
    /* resolves true/false once the stored session has been checked */
    ready: function () { return ensureSession(); },
    user: function () { return user; },
    onChange: function (cb) {
      document.addEventListener("ds-auth", function (ev) { cb(ev.detail && ev.detail.user); });
    },
    /* a fresh JWT (cached ~10 minutes) to hand to the Worker */
    jwt: function () {
      if (jwtCache && jwtCache.until > Date.now()) return Promise.resolve(jwtCache.jwt);
      return ensureSession().then(function (okLoggedIn) {
        if (!okLoggedIn) throw new Error("not signed in");
        return loadSDK().then(function () {
          initClient();
          return account.createJWT();
        });
      }).then(function (res) {
        jwtCache = { jwt: res.jwt, until: Date.now() + 10 * 60 * 1000 };
        return res.jwt;
      });
    },
    /* drop the cached JWT (e.g. after signing out) */
    clearJwt: function () { jwtCache = null; },
    openSignIn: function () { openModal("login"); },
    signOut: function () {
      return ensureSession().then(function () { return account.deleteSessions(); }).then(function () {
        user = null;
        docCache = null;
        docLoad = null;
        jwtCache = null;
        updateChip();
        return true;
      });
    }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
  // Turbo: after each page appearance <body> is a new node, so re-wire everything.
  // With data-turbo-eval="false" this file runs once; document listeners persist.
  // Each wire* function uses data-wired to avoid double-binding within a page.
  document.addEventListener("turbo:load", init);
})();
