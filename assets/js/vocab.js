/* Vocabulary book + sign-in via the site Worker — static-site integration.
 *
 * There is no third-party backend any more. `tools/site-api/worker.js` holds the
 * vocabulary in a PRIVATE R2 bucket behind one shared secret ("sync code", the
 * Worker's SITE_TOKEN). You type that code once per device; this file keeps it in
 * localStorage and sends it as `Authorization: Bearer …` on every call.
 *
 * Why not AppWrite (what this replaced): its free plan pauses a project after 7
 * days without *console* development activity — API/SDK/visitor traffic does not
 * count — so an idle week silently broke the vocabulary book and /files/.
 *
 * DOM contract (shared with layouts/, static/css/main.css and portal.js):
 *   #auth-modal[data-api]      the sync-code dialog, and where the API base lives
 *   #auth-form / #auth-token   the one field, and its submit button
 *   #auth-chip                 header button: "Sign in" ⇄ "📖 Vocabulary"
 *   .episode[data-slug]        an episode page: ☆ buttons live in its sentences
 *   #vocab-list                the /words/ page: one .vocab-item per saved line
 *   #vocab-logout / #vocab-import  its sign-out and import controls
 *   window.SiteAuth            what portal.js (/files/) calls
 */
(function () {
  "use strict";

  var TOKEN_KEY = "site-sync-code";
  var WINDOW = 250;             // how many saved sentences to pull in one go

  var apiBase = "";
  var token = null;
  var user = null;
  var sdkReady = null;          // "is the stored sync code accepted?" (single flight)
  var docCache = null;
  var docLoad = null;
  var modal = null;

  /* ---------- configuration + storage ---------- */

  function readApi() {
    var el = document.querySelector("#auth-modal[data-api], [data-api]");
    var base = (el && el.dataset ? el.dataset.api : "") || "";
    if (!base || base === "none") return "";
    return base.replace(/\/+$/, "");
  }

  function stored() {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }

  function store(value) {
    try {
      if (value) localStorage.setItem(TOKEN_KEY, value);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) {}
  }

  /* ---------- worker calls ---------- */

  function api(method, path, body) {
    return Promise.resolve().then(function () {
      if (!apiBase) throw new Error("No sync backend configured (params.apiBase is empty).");
      if (!token) throw new Error("Not signed in.");
      var init = { method: method, headers: { Authorization: "Bearer " + token } };
      if (body !== undefined) {
        init.headers["content-type"] = "application/json";
        init.body = JSON.stringify(body);
      }
      return fetch(apiBase + path, init);
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var err = new Error(data.error || ("HTTP " + res.status));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  /* ---------- sign-in state ---------- */

  function loggedIn() { return !!user; }

  /* Single flight: several callers may ask at once (the chip, /files/, /words/).
     A 401 clears the code; a network failure keeps it, so a flaky connection
     does not look like being signed out. */
  function ensureSession() {
    if (sdkReady) return sdkReady;
    sdkReady = Promise.resolve().then(function () {
      apiBase = readApi();
      if (!apiBase) return false;
      token = stored();
      if (!token) return false;
      return api("GET", "/api/whoami").then(function () {
        user = { name: "this device" };
        return true;
      }).catch(function (err) {
        if (err && err.status === 401) { token = null; store(""); return false; }
        user = { name: "this device" };   // offline: keep the code, assume it is fine
        return true;
      });
    }).then(function (okState) {
      updateChip();
      return okState;
    });
    return sdkReady;
  }

  function updateChip() {
    var c = chip();
    if (!c) return;
    c.hidden = false;
    if (user) {
      c.textContent = "📖 Vocabulary";
      c.title = "This device is synced — open the vocabulary book";
      c.dataset.state = "in";
    } else {
      c.textContent = "Sign in";
      c.title = "Enter your sync code to sync saved sentences across devices";
      c.dataset.state = "out";
    }
    document.dispatchEvent(new CustomEvent("ds-auth", { detail: { user: user } }));
  }

  function signOut() {
    token = null;
    user = null;
    docCache = null;
    docLoad = null;
    sdkReady = null;
    store("");
    updateChip();
    return Promise.resolve(true);
  }

  /* ---------- the sync-code dialog ---------- */

  function chip() { return document.getElementById("auth-chip"); }

  function openModal() {
    if (!modal) return;
    var field = modal.querySelector("#auth-token");
    if (field) field.value = "";
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
    modal.hidden = false;
    document.body.classList.add("modal-open");
    if (field) field.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
  }

  function fail(msg) {
    var err = modal && modal.querySelector("#auth-err");
    if (err) err.textContent = msg;
  }

  function submitCode(code) {
    var btn = modal.querySelector(".auth-submit");
    var previous = token;
    if (btn) { btn.disabled = true; btn.textContent = "Checking…"; }

    apiBase = apiBase || readApi();
    token = code;
    sdkReady = null;
    return api("GET", "/api/whoami").then(function () {
      store(code);
      user = { name: "this device" };
      closeModal();
      updateChip();
    }).catch(function (err) {
      token = previous;
      if (err && err.status === 401) fail("That sync code was refused. Check it and try again.");
      else if (!apiBase) fail("This site has no sync backend configured.");
      else fail("Could not reach the sync backend: " + ((err && err.message) || err));
    }).then(function () {
      if (btn) { btn.disabled = false; btn.textContent = "Sync this device"; }
    });
  }

  function wireModal() {
    modal = document.getElementById("auth-modal");
    if (!modal || modal.dataset.wired === "1") return;
    modal.dataset.wired = "1";
    apiBase = readApi();
    if (apiBase) document.documentElement.dataset.vocab = "on";

    var close = modal.querySelector("#auth-close");
    if (close) close.addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    var form = modal.querySelector("#auth-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var field = modal.querySelector("#auth-token");
        var code = (field && field.value || "").trim();
        if (!code) { fail("Paste your sync code first."); return; }
        submitCode(code);
      });
    }
  }

  /* ---------- saved sentences ---------- */

  /* Single-flight load of the whole book; callers share one request. */
  function loadDocs() {
    if (docLoad) return docLoad;
    docLoad = api("GET", "/api/vocab?limit=" + WINDOW).then(function (res) {
      var cache = {};
      (res.items || []).forEach(function (it) { cache[it.slug + ":" + it.idx] = it; });
      docCache = cache;
      return cache;
    }).catch(function (e) {
      console.warn("vocabulary load failed:", (e && e.message) || e);
      docLoad = null;                 // allow a retry on the next call
      docCache = docCache || {};
      return docCache;
    });
    return docLoad;
  }

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
      // FIRST child, not last: .star floats right, and a float only rises to the
      // top-right corner of the sentence when nothing has been laid out before
      // it (see the .sentence rules in static/css/main.css). insertBefore keeps
      // this ES5-friendly, like the rest of the file.
      li.insertBefore(btn, li.firstChild);
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

  function sentenceItem(li) {
    var art = li.closest(".episode");
    var textEl = li.querySelector(".text");
    var exEl = li.querySelector(".explain");
    return {
      slug: slug(),
      idx: parseInt(li.dataset.i, 10),
      show: (art && art.dataset.show) || "",
      title: (art && art.dataset.title) || "",
      text: textEl ? textEl.textContent.trim() : "",
      explain: exEl ? exEl.textContent.trim() : ""
    };
  }

  function toggleStar(li, btn) {
    var s = slug();
    if (!s) return;
    if (!loggedIn()) { openModal(); return; }
    var key = s + ":" + li.dataset.i;
    var on = !(docCache && docCache[key]);
    btn.disabled = true;
    var call = on ? api("POST", "/api/vocab/add", sentenceItem(li))
                  : api("POST", "/api/vocab/remove", { slug: s, idx: parseInt(li.dataset.i, 10) });
    call.then(function (res) {
      if (!docCache) docCache = {};
      // Trust the server's copy: on add it echoes the stored record.
      if (on) docCache[key] = (res && res.item) || sentenceItem(li);
      else delete docCache[key];
      btn.classList.toggle("on", on);
      btn.textContent = on ? "★" : "☆";
    }).catch(function (err) {
      console.warn("star failed:", (err && err.message) || err);
      btn.title = "⚠ Could not save: " + ((err && err.message) || err);
      setTimeout(function () { btn.title = ""; }, 4000);
      if (err && err.status === 401) { signOut(); openModal(); }
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

  function importFile(input) {
    var file = input.files && input.files[0];
    if (!file) return;
    var status = document.getElementById("vocab-status");
    var say = function (msg) {
      if (!status) return;
      status.textContent = msg;
      status.hidden = !msg;
    };
    say("Importing " + file.name + "…");
    file.text().then(function (text) {
      var parsed;
      try { parsed = JSON.parse(text); } catch (e) { throw new Error("that file is not JSON"); }
      return api("POST", "/api/vocab/import", parsed);
    }).then(function (res) {
      docCache = null;
      docLoad = null;
      say("Imported " + res.added + " new sentence" + (res.added === 1 ? "" : "s") +
          (res.skipped ? " (" + res.skipped + " already saved)" : "") +
          " — " + res.count + " in the book.");
      renderVocab();
    }).catch(function (err) {
      say("Import failed: " + ((err && err.message) || err));
    }).then(function () {
      input.value = "";
    });
  }

  function wireVocabPage() {
    var box = document.getElementById("vocab-list");
    if (!box || box.dataset.wired === "1") return;
    box.dataset.wired = "1";
    var empty = document.getElementById("vocab-empty");
    var logout = document.getElementById("vocab-logout");
    var importBtn = document.getElementById("vocab-import-btn");
    var importInput = document.getElementById("vocab-import");

    renderVocab();

    if (logout) logout.addEventListener("click", function () {
      signOut().then(renderVocab);
    });
    if (importBtn && importInput) {
      importBtn.addEventListener("click", function () { importInput.click(); });
    }
    if (importInput) importInput.addEventListener("change", function () { importFile(importInput); });

    /* Play a saved sentence: load that episode into the bottom player, then play
       from this sentence's index. The timestamps come from the episode page the
       player fetches on demand — the book only stores where the sentence is. */
    function playSavedItem(li) {
      var EP = window.EpisodePlayer;
      if (!EP || !EP.loadFromPage) return;
      var slug = li.dataset.slug || "";
      var idx = parseInt(li.dataset.idx || "-1", 10);
      if (!slug || idx < 0) return;
      var st = EP.state ? EP.state() : {};
      if (st.has && st.slug === slug && st.sentences > 0) {
        if (st.playing && st.idx === idx) { EP.pause(); return; }
        EP.playFrom(idx, EP.autoNext);
        return;
      }
      EP.loadFromPage(episodesBase() + encodeURIComponent(slug) + "/")
        .then(function () { EP.playFrom(idx, EP.autoNext); })
        .catch(function (err) { console.warn("could not load episode:", (err && err.message) || err); });
    }

    /* One delegated click handler: the ✕ deletes, ▶ and the sentence text play. */
    box.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      var li = t.closest(".vocab-item");
      if (!li) return;
      if (t.closest(".vocab-del")) {
        var del = t.closest(".vocab-del");
        del.disabled = true;
        api("POST", "/api/vocab/remove", {
          slug: li.dataset.slug, idx: parseInt(li.dataset.idx, 10)
        }).then(function () {
          if (docCache) delete docCache[li.dataset.slug + ":" + li.dataset.idx];
          renderVocab();
        }).catch(function (err) {
          console.warn("delete failed:", (err && err.message) || err);
          del.disabled = false;
        });
        return;
      }
      if (t.closest(".vocab-ep")) return;      // the link handles itself
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

    function renderVocab() {
      if (importBtn) importBtn.hidden = !loggedIn();
      if (logout) logout.hidden = !loggedIn();
      if (!loggedIn()) {
        box.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      loadDocs().then(function () {
        var docs = Object.keys(docCache || {}).map(function (k) { return docCache[k]; })
          .sort(function (a, b) {
            return String(b.savedAt || "").localeCompare(String(a.savedAt || ""));
          });
        if (!docs.length) {
          box.innerHTML = "";
          if (empty) empty.hidden = false;
          return;
        }
        if (empty) empty.hidden = true;   // we have items: make sure the empty note is gone
        var base = episodesBase();
        box.innerHTML = docs.map(function (d) {
          return '<li class="vocab-item" data-slug="' + esc(d.slug) + '" data-idx="' + esc(d.idx) + '">' +
            '<div class="vocab-head">' +
              '<a class="vocab-ep" href="' + esc(base) + esc(d.slug) + '/">' +
                esc(d.show || "") + " · " + esc(d.title || d.slug) +
              '</a>' +
              '<span class="vocab-actions">' +
                '<button class="vocab-play" type="button" title="Play from this sentence" aria-label="Play from this sentence">▶</button>' +
                '<button class="vocab-del" title="Delete">✕</button>' +
              '</span>' +
            '</div>' +
            '<p class="vocab-text" title="Click to play from this sentence">' + esc(d.text) + '</p>' +
            (d.explain ? '<p class="vocab-explain">💡 ' + esc(d.explain) + '</p>' : "") +
            '</li>';
        }).join("");
      });
    }

    document.addEventListener("ds-auth", renderVocab);
  }

  /* ---------- boot ---------- */

  function init() {
    wireModal();
    wireStars();
    wireVocabPage();

    var c = chip();
    if (c && c.dataset.wired !== "1") {
      c.dataset.wired = "1";
      c.addEventListener("click", function () {
        if (loggedIn()) {
          if (window.Turbo && window.Turbo.visit) window.Turbo.visit("/words/");
          else location.href = "/words/";
          return;
        }
        ensureSession().then(function (okState) { if (!okState) openModal(); });
      });
    }

    if (stored()) ensureSession().then(function () { updateChip(); });
    else updateChip();
  }

  /* ---------- public API for the /files/ portal ----------
     The Worker authenticates with the same shared secret, so the portal needs the
     current session without re-implementing any of it. */

  window.SiteAuth = {
    ready: function () { return ensureSession(); },
    user: function () { return user; },
    onChange: function (cb) {
      document.addEventListener("ds-auth", function (ev) { cb(ev.detail && ev.detail.user); });
    },
    /* the sync code itself — the portal sends it as a Bearer token */
    jwt: function () {
      return ensureSession().then(function (okState) {
        if (!okState || !token) throw new Error("not signed in");
        return token;
      });
    },
    clearJwt: function () { /* the code does not expire; nothing to clear */ },
    openSignIn: function () { openModal(); },
    signOut: function () { return signOut(); }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
  // Turbo: after each page appearance <body> is a new node, so re-wire everything.
  // With data-turbo-eval="false" this file runs once; document listeners persist.
  // Each wire* function uses data-wired to avoid double-binding within a page.
  document.addEventListener("turbo:load", init);
})();
