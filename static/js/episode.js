/* Sentence-by-sentence podcast player.
   Active only on episode pages (article.episode). */
(function () {
  "use strict";
  const art = document.querySelector(".episode");
  if (!art) return;

  // Always end the audio base path with exactly one "/".
  const dir = ((art.dataset.audioDir || "audio").replace(/\/+$/, "")) + "/";
  const items = Array.from(art.querySelectorAll(".sentence"));
  const playAllBtn = document.getElementById("play-all");
  const autoNextBox = document.getElementById("auto-next");
  const nowEl = document.getElementById("now-playing");
  if (!items.length || !playAllBtn) return;

  let current = null; // { li, audio, index }
  let selected = -1;

  function clearHighlights(li) {
    for (const el of items) {
      if (el !== li) {
        el.classList.remove("playing");
        el.querySelector(".progress").style.width = "0%";
      }
    }
  }

  function stop() {
    if (current) {
      current.audio.pause();
      current.audio.src = "";
      current.li.classList.remove("playing");
      current.li.querySelector(".progress").style.width = "0%";
      current = null;
    }
    nowEl.textContent = "";
    playAllBtn.textContent = "▶ 播放全部";
  }

  function playAt(i) {
    if (i < 0 || i >= items.length) {
      stop();
      return;
    }
    if (current) {
      current.audio.pause();
      current.audio.src = "";
      current = null;
    }
    const li = items[i];
    const audio = new Audio();
    audio.src = dir + li.dataset.file;
    current = { li, audio, index: i };
    selected = i;

    clearHighlights(li);
    li.classList.add("playing");
    markSelected();
    nowEl.textContent = (i + 1) + " / " + items.length;
    playAllBtn.textContent = "⏹ 停止";

    const bar = li.querySelector(".progress");
    const dur = Math.max(0.5, parseFloat(li.dataset.end) - parseFloat(li.dataset.start));
    audio.ontimeupdate = function () {
      if (current && current.audio === audio) {
        bar.style.width = Math.min(100, (audio.currentTime / dur) * 100) + "%";
      }
    };
    audio.onended = function () {
      if (!current || current.audio !== audio) return;
      bar.style.width = "0%";
      li.classList.remove("playing");
      li.classList.add("done");
      current = null;
      if (autoNextBox.checked && i + 1 < items.length) {
        playAt(i + 1);
      } else {
        nowEl.textContent = "";
        playAllBtn.textContent = "▶ 播放全部";
      }
    };
    audio.onerror = function () {
      nowEl.textContent = "⚠ 音频加载失败: " + audio.src;
      li.classList.remove("playing");
      current = null;
    };
    audio.play().catch(function (e) {
      nowEl.textContent = "⚠ 无法播放: " + e.message + " — " + audio.src;
    });
    li.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function markSelected() {
    for (const el of items) el.classList.remove("selected");
    if (selected >= 0 && selected < items.length) {
      items[selected].classList.add("selected");
    }
  }

  playAllBtn.addEventListener("click", function () {
    if (current) stop();
    else playAt(0);
  });

  for (let i = 0; i < items.length; i++) {
    items[i].addEventListener("click", function () {
      if (current && current.li === items[i]) stop();
      else playAt(i);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.target && /input|textarea/i.test(e.target.tagName)) return;
    if (e.key === " " || e.code === "Space") {
      e.preventDefault();
      if (selected < 0) return;
      if (current && current.li === items[selected]) stop();
      else playAt(selected);
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const delta = e.key === "ArrowDown" ? 1 : -1;
      if (selected < 0) selected = delta > 0 ? 0 : items.length - 1;
      else selected = Math.max(0, Math.min(items.length - 1, selected + delta));
      markSelected();
      items[selected].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
})();
