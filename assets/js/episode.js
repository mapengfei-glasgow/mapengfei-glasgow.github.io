/* 单集页绑定器：把本页的音频 / 句子数据交给全局底部播放条（player.js）。
 *
 * 播放逻辑全部在 window.EpisodePlayer 里；本文件只在每次页面出现时
 * （turbo:load，含首次硬加载）把 .episode 上的数据交过去、给句子和
 * 「播放全部」按钮绑事件。跳转走 Turbo 后本页 DOM 会被销毁，下一次
 * 页面出现时重新绑一遍（dataset.playerWired 防止同一页重复绑）。
 *
 * data-turbo-eval="false"（见 single.html）：文件本身不随跳转重新下载执行，
 * 上面注册的 turbo:load 监听器挂在 document 上，跨页面长期有效。
 */
(function () {
  "use strict";

  function onVisit() {
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
      icon: art.dataset.icon || "🎧",
      audioSrc: art.dataset.audio,
      duration: parseFloat(art.dataset.duration || "0"),
      items: items,
      starts: starts,
      ends: ends
    });

    var playAllBtn = document.getElementById("play-all");
    if (playAllBtn) {
      playAllBtn.addEventListener("click", function () {
        EP.playAll();
      });
    }

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

  document.addEventListener("turbo:load", onVisit);
})();
