/* 全局底部播放条 —— 与 Hotwire Turbo 配套。
 *
 * baseof.html 里的 #player-bar 带 data-turbo-permanent：页面跳转时 Turbo 按 id
 * 保留整个节点（连同里面的 <audio> 元素），所以：
 *   1. 播放中的音频在跳转到任何页面时不中断；
 *   2. 播放状态（当前集 / 当前句 / 进度 / 自动连播开关）常驻页面底部；
 *   3. 位置用 localStorage 持久化，硬刷新 / 重新打开也接着上次的位置。
 *
 * 单集页由本文件里的 wireEpisodePage() 在每次 turbo:load 时调用
 * EpisodePlayer.setEpisode() 交接本页数据；非集页面则保留上次载入的集
 * （继续播 / 继续显示）。
 *
 * data-turbo-eval="false"（见 baseof.html）：本文件只在硬加载时执行一次，
 * 所有跨页行为通过这里注册的 document 级监听器实现（document 不随跳转销毁）。
 */
(function () {
  "use strict";
  if (window.EpisodePlayer) return; // 双保险：正常只会执行一次

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

  /* ---------- 状态 ---------- */
  var ep = null;        // {slug,title,show,icon,audioSrc,duration,items,starts,ends}
  var idx = -1;         // 当前句序号（-1 = 未定位到句）
  var mode = "off";     // "follow"（连贯播完）| "single"（播完本句停）| "off"
  var autoNext = true;  // 点句时的默认连播开关（底部条上的按钮）
  var rafId = 0;
  var uiTime = 0;       // 显示的播放头（可能来自 localStorage 恢复，尚未下到音频）
  var uiDuration = 0;   // 显示的总时长（音频元数据没下来前用模板里存的值）
  var lastWholeSec = -1;
  var lastSaveAt = 0;
  var seeking = false;  // 用户正在拖进度条

  /* ---------- 持久化 ---------- */

  /* 结构：{ autoNext, last: "<slug>", bySlug: { "<slug>": {title,show,icon,audioSrc,duration,t,idx} } }
     每集各记各的位置 —— 换集不会冲掉上一集，来回切换都能接上 */
  function loadStore() {
    try { return JSON.parse(localStorage.getItem(LS_KEY) || "null") || {}; } catch (e) { return {}; }
  }

  /* 旧版 bug：data-icon 属性里的 emoji 被 Go html/template 百分号编码
     （%f0%9f%8c%8d），随 ep.icon 存进了 localStorage。读回时识别并解码，
     用户浏览器里已存的脏值自动愈合，无需清缓存。 */
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

  /* ---------- 时间 ---------- */

  function realDuration() {
    var d = audio.duration;
    return (isFinite(d) && d > 0) ? d : 0;
  }

  function curTime() {
    // preload="none"：没开始下载前 audio.currentTime 恒 0，用恢复值兜底
    return realDuration() > 0 ? audio.currentTime : uiTime;
  }

  function fmt(t) {
    if (!isFinite(t) || t < 0) t = 0;
    t = Math.floor(t);
    var m = Math.floor(t / 60), s = t % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  /* ---------- 播放条 UI ---------- */

  function showBar() {
    bar.hidden = false;
    document.body.classList.add("player-open");
  }

  function setPlayingIcon(playing) {
    btnPlay.textContent = playing ? "⏸" : "▶";
    btnPlay.setAttribute("aria-label", playing ? "暂停" : "播放");
  }

  function updateAutoBtn() {
    btnAuto.setAttribute("aria-pressed", String(autoNext));
    btnAuto.textContent = autoNext ? "自动连播 ●" : "自动连播 ○";
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
      if (!el.isConnected) continue; // 旧页面节点已随跳转销毁，跳过
      el.classList.toggle("done", j < i);
      el.classList.toggle("playing", j === i);
    }
    // 播放条上的句位计数（如 "13 / 291"）
    elIdx.textContent = (i >= 0 ? (i + 1) + " / " + n : "");
  }

  function revealExplain(li) {
    if (!ep || !ep.items) return;
    for (var j = 0; j < ep.items.length; j++) {
      var el = ep.items[j];
      if (el.isConnected) el.classList.toggle("show-explain", el === li);
    }
  }

  /* ---------- 核心播放 ---------- */

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

    if (mode === "follow" && n > 0 && idx >= 0) {
      var i = idx;
      // 走到播放头所在的句（±30ms 迟滞，防边界抖动）
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
      // 单句模式：本句播完即停
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
          // preload="none" 时播放开始才下载，seek 可能被冲掉，回补一次
          if (afterSeek != null && Math.abs(audio.currentTime - afterSeek) > 0.25) {
            audio.currentTime = afterSeek;
          }
        } catch (e) {}
      });
    }
    if (p && typeof p.catch === "function") {
      p.catch(function (e) {
        if (e && (e.name === "AbortError" || e.name === "NotAllowedError")) return;
        if (audio.paused) return; // 期间用户已停
        elSentence.textContent = "⚠ 无法播放: " + ((e && e.message) || e);
        stopPlayback();
      });
    }
  }

  function seekAndPlay(target, i, follow) {
    idx = i;
    mode = follow ? "follow" : "single";
    uiTime = target;
    uiDuration = realDuration() || (ep ? ep.duration : 0);
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
      // 整集已播完再按播放 → 从头再来
      var d0 = realDuration() || ep.duration;
      if (audio.ended && d0 > 0 && uiTime >= d0 - 1) {
        uiTime = 0; idx = -1; mode = "off";
      }
      var i = idx >= 0 ? idx : 0;
      var target = ep.starts[i];
      // 暂停在半句中间：从暂停点继续，而不是跳回句首
      if (idx >= 0 && uiTime > 0.5 && Math.abs(uiTime - ep.starts[i]) > 0.4) {
        target = uiTime;
      }
      var follow = (mode === "follow") || (mode === "off" && autoNext);
      seekAndPlay(target, i, follow);
    } else {
      // 无句级数据（非集页面硬刷新恢复出来的状态）：直接跳到保存位置
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

  /* ---------- 集数据交接（每页 turbo:load 调用） ---------- */

  function setEpisode(data) {
    if (ep && ep.slug === data.slug) {
      // 同一集：刷新本页节点引用（跳转回来的页面是全新的 DOM）
      ep.items = data.items; ep.starts = data.starts; ep.ends = data.ends;
      ep.title = data.title; ep.show = data.show; ep.icon = data.icon;
      ep.duration = ep.duration || data.duration;
      // 硬刷新恢复出来的位置没有句号（恢复时还没有句子数据），拿到 items 后补齐
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
    // 换集：保存旧集位置，停掉旧音轨（不销毁 audio 元素本身）
    if (ep) { saveNow(); stopLoop(); audio.pause(); setPlayingIcon(false); }
    ep = data;
    idx = -1;
    mode = "off";
    uiTime = 0;
    uiDuration = data.duration || 0;
    lastWholeSec = -1;
    lastSaveAt = 0;
    audio.src = data.audioSrc; // preload="none"：先不下载

    // 恢复这一集上次的位置（同一次会话内换走再换回，或硬刷新后首次进集页）
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

  /* ---------- 音频事件 ---------- */

  audio.addEventListener("play", function () {
    setPlayingIcon(true);
    if (!rafId) startLoop();
  });

  audio.addEventListener("pause", function () {
    stopLoop();
    setPlayingIcon(false);
    refreshTimeUI();
    saveNow();
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
    elSentence.textContent = "⚠ 音频加载失败";
    stopPlayback();
  });

  audio.addEventListener("loadedmetadata", refreshTimeUI);
  audio.addEventListener("durationchange", refreshTimeUI);

  /* ---------- 播放条按钮 ---------- */

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
    if (d > 0) { try { audio.currentTime = t; } catch (e) {} }
    // 把句定位同步到新位置
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

  /* ---------- 键盘（全局：播放状态在底部，快捷键也应全局有效） ---------- */

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

  /* ---------- 单集页绑定（原 episode.js 并入） ----------
   * 每次页面出现（turbo:load，含首次硬加载）把 .episode 上的数据交给播放条，
   * 并给句子绑点击事件。跳转后旧页 DOM 销毁，下次页面出现重新绑
   * （dataset.playerWired 防止同一页重复绑）。
   *
   * 为什么不在单集页里挂独立 script：Turbo SPA 跳转时，新 body 里的
   * <script data-turbo-eval="false"> 不会被执行（只有硬加载才会），
   * 从非集页 SPA 进集页会永远缺这个绑定。挂在 document 级监听器里
   * （document 不随跳转销毁）就没有这个洞。
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
        // 点到 ☆ 收藏按钮时不触发播放（appwrite.js 的星号自己处理）
        if (e.target && e.target.closest && e.target.closest(".star")) return;
        var st = EP.state();
        if (st.playing && st.idx === i) EP.pause();   // 再点正在播的这句 = 暂停
        else EP.playFrom(i, EP.autoNext);
      });
    });
  }

  /* ---------- Turbo 生命周期 ---------- */

  // <body> 元素每次跳转都会被换成新的（常驻节点除外），class 会丢，这里补回；
  // 先绑本页（可能让播放条显示出来），再按播放条可见性同步 body class
  document.addEventListener("turbo:load", function () {
    wireEpisodePage();
    document.body.classList.toggle("player-open", !bar.hidden);
  });

  /* ---------- 硬刷新恢复：把上次的播放状态摆回底部（不下载音频） ---------- */

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

  /* ---------- 对外 API（episode.js 用） ---------- */

  window.EpisodePlayer = {
    setEpisode: setEpisode,
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
        slug: ep ? ep.slug : null
      };
    }
  };
})();
