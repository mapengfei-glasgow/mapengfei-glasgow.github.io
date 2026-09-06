/* Episode player: one continuous audio stream per episode.
   Clicking a sentence seeks to its timestamp; with 自动连播 on, playback
   simply continues through the whole episode (no gaps, no re-fetching).
   Active only on episode pages (article.episode). */
(function () {
  "use strict";
  const art = document.querySelector(".episode");
  if (!art) return;

  const audioSrc = art.dataset.audio;
  const items = Array.from(art.querySelectorAll(".sentence"));
  const playAllBtn = document.getElementById("play-all");
  const autoNextBox = document.getElementById("auto-next");
  const nowEl = document.getElementById("now-playing");
  if (!items.length || !playAllBtn || !audioSrc) return;

  const n = items.length;
  const starts = items.map((li) => parseFloat(li.dataset.start));
  const ends = items.map((li) => parseFloat(li.dataset.end));

  const audio = new Audio(audioSrc);
  audio.preload = "none"; // 用户真的点播放才开始下载（每集 20–36MB，别浪费流量）

  let idx = -1;      // 当前句序号
  let mode = "off";  // "follow" (continuous) | "single" (stop at this sentence's end) | "off"
  let rafId = 0;
  let stopped = true; // true right after stop(); false after user-initiated pause

  // ---- UI helpers -------------------------------------------------------

  // Reveal the plain-English explanation for one sentence, hiding the others.
  function revealExplain(li) {
    for (const el of items) {
      if (el !== li) el.classList.remove("show-explain");
    }
    if (li && li.querySelector(".explain")) li.classList.add("show-explain");
  }

  function setBtn(label) { playAllBtn.textContent = label; }

  function markActive(i) {
    for (let j = 0; j < n; j++) {
      items[j].classList.toggle("done", j < i);
      items[j].classList.toggle("playing", j === i);
    }
    if (i >= 0 && i < n) nowEl.textContent = (i + 1) + " / " + n;
  }

  // ---- playback ---------------------------------------------------------

  function startLoop() {
    stopLoop();
    rafId = requestAnimationFrame(loop);
  }
  function stopLoop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function loop() {
    if (audio.paused) return;
    const t = audio.currentTime;

    if (mode === "follow") {
      let i = idx;
      // walk to the sentence containing the playhead (±30ms hysteresis)
      while (i < n - 1 && t >= starts[i + 1] - 0.03) i++;
      while (i > 0 && t < starts[i] - 0.03) i--;
      if (i !== idx) {
        idx = i;
        markActive(i);
        revealExplain(items[i]);
        items[i].scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else if (mode === "single" && t >= ends[idx] + 0.10) {
      // single-sentence mode: stop just after this sentence finishes
      stop();
      return;
    }

    if (!audio.paused) rafId = requestAnimationFrame(loop);
  }

  function playFrom(i, follow) {
    if (i < 0 || i >= n) { stop(); return; }
    // preload="none": the file may not be downloading yet, so a seek set
    // before play() can be lost once playback begins — re-assert it after.
    const target = starts[i];
    audio.currentTime = target;
    idx = i;
    mode = follow ? "follow" : "single";
    stopped = false;
    markActive(i);
    revealExplain(items[i]);
    setBtn("⏹ 停止");
    const p = audio.play();
    if (p && typeof p.then === "function") {
      p.then(function () {
        try {
          if (Math.abs(audio.currentTime - target) > 0.25) audio.currentTime = target;
        } catch (e) {}
      });
    }
    if (p && typeof p.catch === "function") {
      p.catch(function (e) {
        if (e && e.name === "AbortError") return;
        if (audio.paused) return; // user stopped in the meantime
        nowEl.textContent = "⚠ 无法播放: " + e.message;
        stop();
      });
    }
    startLoop();
    items[i].scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function playAll() { playFrom(0, true); }

  function stop() {
    audio.pause();
    mode = "off";
    stopped = true;
    stopLoop();
    if (idx >= 0) items[idx].classList.remove("playing");
    nowEl.textContent = "";
    setBtn("▶ 播放全部");
  }

  // ---- events -----------------------------------------------------------

  audio.onended = function () { stop(); nowEl.textContent = ""; };
  audio.onerror = function () {
    if (!audio.src) return;
    nowEl.textContent = "⚠ 音频加载失败: " + audioSrc;
    stop();
  };
  audio.onpause = function () {
    if (mode !== "off" && !stopped) setBtn("▶ 继续");
  };
  audio.onplay = function () {
    if (mode !== "off") {
      setBtn("⏹ 停止");
      if (!rafId) startLoop();
    }
  };

  playAllBtn.addEventListener("click", function () {
    if (!audio.paused && !audio.ended) {
      stop();
    } else {
      playAll();
    }
  });

  for (let i = 0; i < n; i++) {
    items[i].addEventListener("click", function () {
      if (!audio.paused && !audio.ended && idx === i) stop();
      else playFrom(i, autoNextBox.checked);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.target && /input|textarea/i.test(e.target.tagName)) return;
    if (e.key === " " || e.code === "Space") {
      e.preventDefault();
      if (!audio.paused && !audio.ended) {
        audio.pause();           // keep position + mode; space resumes
      } else if (mode === "off") {
        playFrom(idx < 0 ? 0 : idx, autoNextBox.checked);
      } else {
        audio.play().catch(function () {});
      }
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const delta = e.key === "ArrowDown" ? 1 : -1;
      const j = idx < 0 ? (delta > 0 ? 0 : n - 1)
                        : Math.max(0, Math.min(n - 1, idx + delta));
      idx = j;
      markActive(j);
      revealExplain(items[j]);
      audio.currentTime = starts[j];   // reposition (even while paused)
      if (!audio.paused && !audio.ended) mode = "follow";
      items[j].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
})();
