/* Global bottom player bar — pairs with Hotwire Turbo.
 *
 * #player-bar carries data-turbo-permanent, so on navigation Turbo keeps the
 * whole node (including its <audio> element) by id, which means:
 *   1. audio keeps playing while you navigate anywhere;
 *   2. state (episode, sentence, progress, auto-continue) lives in the bottom bar;
 *   3. the position is persisted in localStorage, so a refresh resumes it.
 *
 * On episode pages wireEpisodePage() hands the page data to
 * EpisodePlayer.setEpisode(); other pages keep whatever was loaded before
 * (playback and the bar simply continue).
 *
 * With data-turbo-eval="false" this file executes once per hard load;
 * every cross-page behaviour hangs off document-level listeners (document survives).
 */
(function () {
  "use strict";
  if (window.EpisodePlayer) return; // belt and braces: normally runs only once

  var bar = document.getElementById("player-bar");
  var audio = document.getElementById("player-audio");
  if (!bar || !audio) return;

  var elIcon = document.getElementById("player-icon");
  var elTitle = document.getElementById("player-title");
  var elSentence = document.getElementById("player-sentence");
  var elLink = document.getElementById("player-link");
  var btnPlay = document.getElementById("player-play");
  var btnPrev = document.getElementById("player-prev");
  var btnNext = document.getElementById("player-next");
  var btnAuto = document.getElementById("player-autonext");
  var elProgress = document.getElementById("player-progress");
  var elTime = document.getElementById("player-time");
  var elIdx = document.getElementById("player-idx");

  var LS_KEY = "ds-player-state-v2";

  /* ---------- State ---------- */
  var ep = null;        // {slug,title,show,icon,audioSrc,duration,items,starts,ends}
  var idx = -1;         // current sentence index (-1 = not positioned)
  var mode = "off";     // "follow" (play on) | "single" (stop after this sentence) | "off"
  var autoNext = true;  // default auto-continue toggle (the button in the bottom bar)
  var rafId = 0;
  var uiTime = 0;       // displayed playhead (may come from a localStorage restore)
  var uiDuration = 0;   // displayed duration (page value until audio metadata arrives)
  var lastWholeSec = -1;
  var lastSaveAt = 0;
  var seeking = false;  // user is dragging the progress bar
  var pendingSeek = null; // a seek requested before the media was seekable

  /* ---------- Persistence ---------- */

  /* Shape: { autoNext, last: "<slug>", bySlug: { "<slug>": {title,show,icon,audioSrc,duration,t,idx} } }
     Each episode keeps its own position, so switching back and forth resumes. */
  function loadStore() {
    try { return JSON.parse(localStorage.getItem(LS_KEY) || "null") || {}; } catch (e) { return {}; }
  }

  /* Old bug: emoji in the data-icon attribute were percent-encoded by Go
        html/template (%f0%9f%8c%8d) and stored with ep.icon in localStorage.
        We detect and decode them on read, healing existing values. */
  function cleanIcon(s) {
    if (!s) return "🎧";
    if (/^%[0-9a-fA-F]{2}/.test(s)) {
      try { var d = decodeURIComponent(s); if (d) return d; } catch (e) {}
    }
    return s;
  }

  function saveNow() {
    if (!ep || !ep.audioSrc) return;
    var store = loadStore();
    store.autoNext = autoNext;
    store.bySlug = store.bySlug || {};
    store.bySlug[ep.slug] = {
      title: ep.title,
      show: ep.show,
      icon: ep.icon,
      audioSrc: ep.audioSrc,
      duration: ep.duration,
      t: curTime(),
      idx: idx
    };
    store.last = ep.slug;
    try { localStorage.setItem(LS_KEY, JSON.stringify(store)); } catch (e) {}
  }

  /* ---------- Time ---------- */

  function realDuration() {
    var d = audio.duration;
    return (isFinite(d) && d > 0) ? d : 0;
  }

  function curTime() {
    // with preload="none" currentTime stays 0 until playback; fall back to the restored value
    return realDuration() > 0 ? audio.currentTime : uiTime;
  }

  function fmt(t) {
    if (!isFinite(t) || t < 0) t = 0;
    t = Math.floor(t);
    var m = Math.floor(t / 60), s = t % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  /* ---------- Player bar UI ---------- */

  function showBar() {
    bar.hidden = false;
    document.body.classList.add("player-open");
  }

  function setPlayingIcon(playing) {
    btnPlay.textContent = playing ? "⏸" : "▶";
    btnPlay.setAttribute("aria-label", playing ? "Pause" : "Play");
  }

  function updateAutoBtn() {
    btnAuto.setAttribute("aria-pressed", String(autoNext));
    btnAuto.textContent = autoNext ? "Auto-continue ●" : "Auto-continue ○";
  }

  function setBarIdentity() {
    if (!ep) return;
    elIcon.textContent = ep.icon || "🎧";
    elTitle.textContent = ep.title;
    elTitle.title = ep.title + (ep.show ? " · " + ep.show : "");
    var link = "/episodes/" + ep.slug + "/";
    if (elLink.getAttribute("href") !== link) elLink.setAttribute("href", link);
  }

  function setSentenceText(i) {
    if (ep && ep.items && i >= 0 && i < ep.items.length) {
      var t = ep.items[i].querySelector(".text");
      elSentence.textContent = t ? t.textContent : "";
    } else {
      elSentence.textContent = "";
    }
  }

  function refreshTimeUI() {
    var t = curTime();
    var d = realDuration() || uiDuration;
    if (!seeking) {
      elProgress.value = String(d > 0 ? Math.min(1000, Math.round((t / d) * 1000)) : 0);
    }
    elTime.textContent = fmt(t) + " / " + fmt(d);
  }

  function markActivePage(i) {
    if (!ep || !ep.items || !ep.items.length) {
      elIdx.textContent = "";
      return;
    }
    var n = ep.items.length;
    for (var j = 0; j < n; j++) {
      var el = ep.items[j];
      if (!el.isConnected) continue; // the old page's node is gone after navigation; skip it
      el.classList.toggle("done", j < i);
      el.classList.toggle("playing", j === i);
    }
    // sentence counter in the bar (e.g. "13 / 291")
    elIdx.textContent = (i >= 0 ? (i + 1) + " / " + n : "");
    notify();
  }

  /* Broadcast playback state so other pages (the vocabulary list) can reflect it. */
  function notify() {
    var detail = {
      has: !!ep,
      playing: !!ep && !audio.paused && !audio.ended,
      idx: idx,
      slug: ep ? ep.slug : null
    };
    try {
      document.dispatchEvent(new CustomEvent("ds-player-change", { detail: detail }));
    } catch (e) {}
  }

  function revealExplain(li) {
    if (!ep || !ep.items) return;
    for (var j = 0; j < ep.items.length; j++) {
      var el = ep.items[j];
      if (el.isConnected) el.classList.toggle("show-explain", el === li);
    }
  }

  /* ---------- Core playback ---------- */

  function startLoop() {
    if (rafId) return;
    rafId = requestAnimationFrame(loop);
  }

  function stopLoop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function loop() {
    rafId = 0;
    if (!ep || audio.paused || audio.ended) return;
    var t = audio.currentTime;
    var n = ep.items.length;

    /* A seek made before the media was seekable is re-applied here. */
    if (pendingSeek != null) {
      if (Math.abs(t - pendingSeek) <= 0.25) {
        pendingSeek = null;
      } else if (audio.seekable && audio.seekable.length) {
        try { audio.currentTime = pendingSeek; } catch (e) {}
        t = audio.currentTime;
      }
      if (pendingSeek != null) {
        refreshTimeUI();
        rafId = requestAnimationFrame(loop);
        return;
      }
    }

    if (mode === "follow" && n > 0 && idx >= 0) {
      var i = idx;
      // find the sentence under the playhead (±30ms hysteresis)
      while (i < n - 1 && t >= ep.starts[i + 1] - 0.03) i++;
      while (i > 0 && t < ep.starts[i] - 0.03) i--;
      if (i !== idx) {
        idx = i;
        markActivePage(i);
        revealExplain(ep.items[i]);
        setSentenceText(i);
        if (ep.items[i].isConnected) {
          ep.items[i].scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    } else if (mode === "single" && n > 0 && idx >= 0 && t >= ep.ends[idx] + 0.1) {
      // single mode: stop when this sentence ends
      pauseAtSentenceEnd();
      return;
    }

    var sec = Math.floor(t);
    if (sec !== lastWholeSec) {
      lastWholeSec = sec;
      refreshTimeUI();
      if (t - lastSaveAt > 2) { lastSaveAt = t; saveNow(); }
    }
    if (!audio.paused && !audio.ended) rafId = requestAnimationFrame(loop);
  }

  function doPlay(afterSeek) {
    var p = audio.play();
    if (p && typeof p.then === "function") {
      p.then(function () {
        try {
          // with preload="none" a seek can be dropped right after play; retry once
          if (afterSeek != null && Math.abs(audio.currentTime - afterSeek) > 0.25) {
            audio.currentTime = afterSeek;
          }
        } catch (e) {}
      });
    }
    if (p && typeof p.catch === "function") {
      p.catch(function (e) {
        if (e && (e.name === "AbortError" || e.name === "NotAllowedError")) return;
        if (audio.paused) return; // the user paused meanwhile
        elSentence.textContent = "⚠ Cannot play: " + ((e && e.message) || e);
        stopPlayback();
      });
    }
  }

  function seekAndPlay(target, i, follow) {
    idx = i;
    mode = follow ? "follow" : "single";
    uiTime = target;
    uiDuration = realDuration() || (ep ? ep.duration : 0);
    // With preload="none" the media is not seekable yet, so remember the target
    // and let the loop / loadedmetadata re-apply it until it sticks.
    pendingSeek = target;
    try { audio.currentTime = target; } catch (e) {}
    markActivePage(i);
    if (ep.items && i >= 0 && i < ep.items.length) {
      revealExplain(ep.items[i]);
      setSentenceText(i);
      if (ep.items[i].isConnected) {
        ep.items[i].scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
    doPlay(target);
    startLoop();
    showBar();
    saveNow();
  }

  function playFrom(i, follow) {
    if (!ep || !ep.items || !ep.items.length) return;
    if (i < 0 || i >= ep.items.length) return;
    seekAndPlay(ep.starts[i], i, follow);
  }

  function resumeOrStart() {
    if (!ep) return;
    if (ep.items && ep.items.length) {
      // episode finished: pressing play starts it over
      var d0 = realDuration() || ep.duration;
      if (audio.ended && d0 > 0 && uiTime >= d0 - 1) {
        uiTime = 0; idx = -1; mode = "off";
      }
      var i = idx >= 0 ? idx : 0;
      var target = ep.starts[i];
      // paused mid-sentence: resume from there, not from the sentence start
      if (idx >= 0 && uiTime > 0.5 && Math.abs(uiTime - ep.starts[i]) > 0.4) {
        target = uiTime;
      }
      var follow = (mode === "follow") || (mode === "off" && autoNext);
      seekAndPlay(target, i, follow);
    } else {
      // no sentence data (state restored off an episode page): jump to the saved position
      var t = uiTime > 0.5 ? uiTime : 0;
      try { audio.currentTime = t; } catch (e) {}
      mode = "follow";
      doPlay(t);
      startLoop();
      showBar();
      saveNow();
    }
  }

  function userPause() {
    if (!ep || audio.paused) return;
    audio.pause();
    setPlayingIcon(false);
    saveNow();
  }

  function pauseAtSentenceEnd() {
    audio.pause();
    mode = "off";
    stopLoop();
    setPlayingIcon(false);
    refreshTimeUI();
    saveNow();
  }

  function stopPlayback() {
    audio.pause();
    mode = "off";
    stopLoop();
    setPlayingIcon(false);
  }

  function toggle() {
    if (!ep) return;
    if (!audio.paused && !audio.ended) userPause();
    else resumeOrStart();
  }

  function stepSentence(delta) {
    if (!ep || !ep.items || !ep.items.length) return;
    var n = ep.items.length;
    var j = idx < 0 ? (delta > 0 ? 0 : n - 1)
                    : Math.max(0, Math.min(n - 1, idx + delta));
    idx = j;
    uiTime = ep.starts[j];
    markActivePage(j);
    revealExplain(ep.items[j]);
    setSentenceText(j);
    if (ep.items[j].isConnected) {
      ep.items[j].scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (!audio.paused && !audio.ended) {
      mode = "follow";
      try { audio.currentTime = ep.starts[j]; } catch (e) {}
    } else {
      mode = "off";
      refreshTimeUI();
    }
    saveNow();
  }

  /* ---------- Episode data handover (called on every page load) ---------- */

  function setEpisode(data) {
    if (ep && ep.slug === data.slug) {
      // same episode: refresh node references (a revisited page has fresh DOM)
      ep.items = data.items; ep.starts = data.starts; ep.ends = data.ends;
      ep.title = data.title; ep.show = data.show; ep.icon = data.icon;
      ep.duration = ep.duration || data.duration;
      // a restored position has no sentence index; fill it in once items are known
      if (idx < 0 && uiTime > 0.5 && data.items.length) {
        var k = 0;
        while (k < data.items.length - 1 && uiTime >= data.starts[k + 1] - 0.03) k++;
        idx = k;
      }
      setBarIdentity();
      markActivePage(idx);
      setSentenceText(idx);
      showBar();
      return;
    }
    // switching episode: save the old position, stop the old track (keep the element)
    if (ep) { saveNow(); stopLoop(); audio.pause(); setPlayingIcon(false); }
    ep = data;
    idx = -1;
    mode = "off";
    uiTime = 0;
    uiDuration = data.duration || 0;
    lastWholeSec = -1;
    lastSaveAt = 0;
    audio.src = data.audioSrc; // preload="none": don't download yet

    // restore this episode's last position (switch back, or first visit after a refresh)
    var store = loadStore();
    var saved = (store.bySlug || {})[data.slug];
    autoNext = store.autoNext !== false;
    if (saved) {
      uiTime = Math.max(0, saved.t || 0);
      if (typeof saved.idx === "number" && saved.idx >= 0 && data.items.length > saved.idx) {
        idx = saved.idx;
      } else if (uiTime > 0.5 && data.items && data.items.length) {
        var j = 0;
        while (j < data.items.length - 1 && uiTime >= data.starts[j + 1] - 0.03) j++;
        idx = j;
      }
    }
    updateAutoBtn();
    setBarIdentity();
    markActivePage(idx);
    setSentenceText(idx);
    refreshTimeUI();
    setPlayingIcon(false);
    showBar();
    saveNow();
  }

  /* ---------- Audio events ---------- */

  audio.addEventListener("play", function () {
    setPlayingIcon(true);
    if (!rafId) startLoop();
    notify();
  });

  audio.addEventListener("pause", function () {
    stopLoop();
    setPlayingIcon(false);
    refreshTimeUI();
    saveNow();
    notify();
  });

  audio.addEventListener("ended", function () {
    mode = "off";
    stopLoop();
    if (ep && ep.items) {
      idx = ep.items.length - 1;
      for (var j = 0; j < ep.items.length; j++) {
        if (ep.items[j].isConnected) ep.items[j].classList.add("done");
      }
      markActivePage(idx);
    }
    refreshTimeUI();
    saveNow();
  });

  audio.addEventListener("error", function () {
    if (!audio.currentSrc) return;
    elSentence.textContent = "⚠ Audio failed to load";
    stopPlayback();
  });

  audio.addEventListener("loadedmetadata", function () {
    if (pendingSeek != null) { try { audio.currentTime = pendingSeek; } catch (e) {} }
    refreshTimeUI();
  });
  audio.addEventListener("durationchange", refreshTimeUI);

  /* ---------- Player bar buttons ---------- */

  btnPlay.addEventListener("click", toggle);
  btnPrev.addEventListener("click", function () { stepSentence(-1); });
  btnNext.addEventListener("click", function () { stepSentence(1); });
  btnAuto.addEventListener("click", function () {
    autoNext = !autoNext;
    updateAutoBtn();
    saveNow();
  });

  elProgress.addEventListener("input", function () {
    seeking = true;
    var d = realDuration() || uiDuration;
    uiTime = (elProgress.value / 1000) * (d || 0);
    refreshTimeUI();
  });

  elProgress.addEventListener("change", function () {
    seeking = false;
    var d = realDuration() || uiDuration;
    var t = (elProgress.value / 1000) * (d || 0);
    uiTime = t;
    pendingSeek = null; // an explicit drag overrides any pending seek
    if (d > 0) { try { audio.currentTime = t; } catch (e) {} }
    // sync the sentence position to the new spot
    if (ep && ep.items && ep.items.length) {
      var j = 0;
      while (j < ep.items.length - 1 && t >= ep.starts[j + 1] - 0.03) j++;
      if (j !== idx) {
        idx = j;
        markActivePage(j);
        revealExplain(ep.items[j]);
        setSentenceText(j);
      }
    }
    saveNow();
  });

  /* ---------- Keyboard (global: playback lives in the bottom bar) ---------- */

  document.addEventListener("keydown", function (e) {
    if (!ep) return;
    if (e.target && /INPUT|TEXTAREA|SELECT/i.test(e.target.tagName)) return;
    if (document.body.classList.contains("modal-open")) return;
    if (e.key === " " || e.code === "Space") {
      e.preventDefault();
      toggle();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      stepSentence(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      stepSentence(-1);
    }
  });

  /* ---------- Episode page wiring (the old episode.js, merged in) ----------
   * On every page appearance (turbo:load, including the first hard load) hand the
   * data on .episode to the player bar and bind click handlers to the sentences.
   * dataset.playerWired prevents double-binding within one page.
   *
   * Why not a per-page script: on a Turbo navigation the new body's
   * <script data-turbo-eval="false"> is not executed (only hard loads run it),
   * so entering an episode page by SPA navigation would never get wired. Hanging it
   * off a document-level listener (document survives navigation) closes that hole.
   */
  function wireEpisodePage() {
    var art = document.querySelector(".episode");
    if (!art || art.dataset.playerWired === "1") return;
    var EP = window.EpisodePlayer;
    if (!EP || !EP.setEpisode) return;
    art.dataset.playerWired = "1";

    var items = Array.prototype.slice.call(art.querySelectorAll(".sentence"));
    if (!items.length || !art.dataset.audio) return;

    var starts = [], ends = [];
    for (var i = 0; i < items.length; i++) {
      starts.push(parseFloat(items[i].dataset.start));
      ends.push(parseFloat(items[i].dataset.end));
    }

    var h1 = art.querySelector(".ep-title");
    EP.setEpisode({
      slug: art.dataset.slug || "",
      title: art.dataset.title || (h1 ? h1.textContent : ""),
      show: art.dataset.show || "",
      icon: art.dataset.emoji || "🎧",
      audioSrc: art.dataset.audio,
      duration: parseFloat(art.dataset.duration || "0"),
      items: items,
      starts: starts,
      ends: ends
    });

    items.forEach(function (li, i) {
      li.addEventListener("click", function (e) {
        // clicking the ☆ save button must not start playback (appwrite.js handles it)
        if (e.target && e.target.closest && e.target.closest(".star")) return;
        var st = EP.state();
        if (st.playing && st.idx === i) EP.pause();   // tapping the sentence that is playing pauses it
        else EP.playFrom(i, EP.autoNext);
      });
    });
  }

  /* ---------- Turbo lifecycle ---------- */

  // <body> is replaced on every navigation (barring permanent nodes), so classes are lost;
  // wire this page first (it may reveal the bar), then sync the body class
  document.addEventListener("turbo:load", function () {
    wireEpisodePage();
    document.body.classList.toggle("player-open", !bar.hidden);
  });

  // fallback without Turbo (PaperMod does full page loads): wire on first load too
  if (typeof document.addEventListener === "function") {
    document.addEventListener("DOMContentLoaded", function () {
      wireEpisodePage();
      document.body.classList.toggle("player-open", !bar.hidden);
    });
  }

  /* ---------- Hard-refresh restore: put the last state back in the bar ---------- */

  (function restore() {
    var store = loadStore();
    var slug = store.last;
    var saved = slug && (store.bySlug || {})[slug];
    if (!saved || !saved.audioSrc) return;
    ep = {
      slug: slug,
      title: saved.title || slug,
      show: saved.show || "",
      icon: cleanIcon(saved.icon),
      audioSrc: saved.audioSrc,
      duration: saved.duration || 0,
      items: [], starts: [], ends: []
    };
    idx = -1;
    mode = "off";
    autoNext = store.autoNext !== false;
    uiTime = Math.max(0, saved.t || 0);
    uiDuration = saved.duration || 0;
    audio.src = saved.audioSrc;
    updateAutoBtn();
    setBarIdentity();
    refreshTimeUI();
    setPlayingIcon(false);
    showBar();
  })();

  updateAutoBtn();
  refreshTimeUI();

  /* ---------- Loading an episode from a page URL ----------
   * Used by the vocabulary page, where a saved sentence only knows its episode
   * slug + sentence index: fetch that episode's page and parse the same
   * .episode / .sentence markup the player normally reads from the live DOM,
   * so seeking and sentence stepping work with no extra data source. */

  function episodeDataFromDoc(doc) {
    var art = doc.querySelector(".episode");
    if (!art || !art.dataset.audio) return null;
    var items = Array.prototype.slice.call(art.querySelectorAll(".sentence"));
    if (!items.length) return null;
    var starts = [], ends = [];
    for (var i = 0; i < items.length; i++) {
      starts.push(parseFloat(items[i].dataset.start));
      ends.push(parseFloat(items[i].dataset.end));
    }
    var h1 = art.querySelector(".ep-title");
    return {
      slug: art.dataset.slug || "",
      title: art.dataset.title || (h1 ? h1.textContent : ""),
      show: art.dataset.show || "",
      icon: art.dataset.emoji || "🎧",
      audioSrc: art.dataset.audio,
      duration: parseFloat(art.dataset.duration || "0"),
      items: items, starts: starts, ends: ends
    };
  }

  var pageCache = {}; // url -> episode data, so nothing is refetched needlessly

  function loadFromPage(url) {
    if (pageCache[url]) {
      setEpisode(pageCache[url]);
      return Promise.resolve(pageCache[url]);
    }
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
        return r.text();
      })
      .then(function (html) {
        var data = episodeDataFromDoc(new DOMParser().parseFromString(html, "text/html"));
        if (!data) throw new Error("no episode data in " + url);
        pageCache[url] = data;
        setEpisode(data);
        return data;
      });
  }

  /* ---------- Public API ---------- */

  window.EpisodePlayer = {
    setEpisode: setEpisode,
    loadFromPage: loadFromPage,
    playFrom: playFrom,
    play: resumeOrStart,
    pause: userPause,
    toggle: toggle,
    next: function () { stepSentence(1); },
    prev: function () { stepSentence(-1); },
    get autoNext() { return autoNext; },
    set autoNext(v) { autoNext = !!v; updateAutoBtn(); saveNow(); },
    state: function () {
      return {
        has: !!ep,
        playing: !!ep && !audio.paused && !audio.ended,
        idx: idx,
        slug: ep ? ep.slug : null,
        // 0 after a restore: the episode is known but its sentence data is not
        sentences: ep && ep.items ? ep.items.length : 0
      };
    }
  };
})();
