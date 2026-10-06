/* Exercise library — /exercises/
 *
 * Data: static/exercises/exercises.json (1,324 exercises), built by
 * tools/build_exercises.py from github.com/hasaneyldrm/exercises-dataset.
 * Media: not in this repo — thumbnails and GIFs are © Gym visual and the
 * dataset's licence does not cover them, so `data-media-base` (hugo.toml →
 * params.exercises.mediaBase) points at jsDelivr, which serves them from the
 * upstream repository. Every screen shows data-attribution for that reason.
 *
 * Everything the user creates (favourites, plans) lives in localStorage: there
 * is no account and no server, so this page keeps working offline once the data
 * file and the media have been cached.
 *
 * DOM contract (shared with layouts/exercises/list.html and
 * assets/css/exercises.css):
 *   #ex-app[data-src][data-media-base][data-attribution][data-upstream]
 *   .ex-tab[data-view]          动作库 / 收藏 / 训练计划
 *   #ex-search #ex-cat #ex-equip #ex-target #ex-sort #ex-clear
 *   #ex-grid #ex-more #ex-count #ex-empty        the library
 *   #ex-fav-grid #ex-fav-count #ex-fav-empty #ex-fav-toplan #ex-fav-badge
 *   #ex-plan-select #ex-plan-list #ex-plan-* #ex-plan-badge
 *   #ex-detail*                                  the detail modal
 *   #ex-timer*                                   the guided session
 */
(function () {
  "use strict";

  var PAGE_SIZE = 60;              // cards rendered per "加载更多"
  var STORE = {
    favs: "exercise-favorites",
    plans: "exercise-plans",
    lang: "exercise-lang"
  };
  var DEFAULT_PLAN = "我的训练";

  /* ---------- Chinese names for the upstream (English) facet values ----------
     Upstream keeps raw English in the data; the page is Chinese, so labels are
     translated here. An unknown value (upstream adds a new piece of equipment)
     falls through to the English string rather than disappearing. */
  var LABELS = {
    category: {
      "back": "背部", "cardio": "有氧", "chest": "胸部", "lower arms": "前臂",
      "lower legs": "小腿", "neck": "颈部", "shoulders": "肩部",
      "upper arms": "上臂", "upper legs": "腿部", "waist": "腰腹"
    },
    equipment: {
      "body weight": "徒手", "dumbbell": "哑铃", "cable": "绳索", "barbell": "杠铃",
      "leverage machine": "固定器械", "band": "弹力带", "smith machine": "史密斯机",
      "kettlebell": "壶铃", "weighted": "负重", "stability ball": "健身球",
      "ez barbell": "曲杆铃", "assisted": "辅助", "sled machine": "雪橇机",
      "medicine ball": "药球", "rope": "绳索", "roller": "滚轮",
      "resistance band": "阻力带", "bosu ball": "波速球", "olympic barbell": "奥杆",
      "wheel roller": "健腹轮", "upper body ergometer": "上肢功率车",
      "skierg machine": "滑雪机", "hammer": "锤", "stationary bike": "动感单车",
      "tire": "轮胎", "trap bar": "六角杠铃", "elliptical machine": "椭圆机",
      "stepmill machine": "爬楼机"
    },
    muscle: {
      "abs": "腹肌", "abdominals": "腹肌", "obliques": "腹斜肌", "core": "核心",
      "pectorals": "胸大肌", "chest": "胸大肌", "biceps": "肱二头肌",
      "triceps": "肱三头肌", "forearms": "前臂", "wrist flexors": "腕屈肌",
      "wrist extensors": "腕伸肌", "wrists": "手腕", "hands": "手部",
      "delts": "三角肌", "deltoids": "三角肌", "shoulders": "肩部",
      "rotator cuff": "肩袖", "traps": "斜方肌", "trapezius": "斜方肌",
      "upper back": "上背", "lats": "背阔肌", "latissimus dorsi": "背阔肌",
      "rhomboids": "菱形肌", "spine": "竖脊肌", "lower back": "下背",
      "glutes": "臀肌", "quads": "股四头肌", "quadriceps": "股四头肌",
      "hamstrings": "腘绳肌", "adductors": "内收肌", "abductors": "外展肌",
      "hip flexors": "髋屈肌", "calves": "小腿", "soleus": "比目鱼肌",
      "ankles": "踝关节", "ankle stabilizers": "踝稳定肌",
      "serratus anterior": "前锯肌", "levator scapulae": "肩胛提肌",
      "cardiovascular system": "心肺系统"
    }
  };

  /* ---------- tiny DOM helpers ---------- */
  function $(sel) { return document.querySelector(sel); }

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function label(kind, value) {
    if (!value) return "";
    var table = LABELS[kind];
    return (table && table[value]) || value;
  }

  function fmtClock(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function read(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) { return fallback; }
  }

  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }

  /* ---------- state ---------- */
  var app, data = null, byId = {};
  var view = "lib";
  var favs = [];                   // array of exercise ids
  var planStore = { active: null, plans: [] };
  var lang = "zh";                 // which instruction language is shown
  var filters = { q: "", category: "", equipment: "", target: "", sort: "name" };
  var list = [];                   // what the library currently shows
  var shown = 0;                   // how many of `list` are in the DOM
  var detailList = null, detailIndex = -1;
  var session = null;
  var toastEl = null, toastTimer = null;

  /* ---------- data loading ---------- */
  function boot() {
    app = $("#ex-app");
    if (!app) return;

    favs = read(STORE.favs, []) || [];
    lang = read(STORE.lang, "zh") === "en" ? "en" : "zh";
    planStore = read(STORE.plans, null) || { active: null, plans: [] };
    if (!planStore.plans || !planStore.plans.length) {
      planStore = { active: "p1", plans: [{ id: "p1", name: DEFAULT_PLAN, items: [] }] };
    }
    if (!planStore.plans.some(function (p) { return p.id === planStore.active; })) {
      planStore.active = planStore.plans[0].id;
    }

    $("#ex-credit-text").innerHTML = esc(app.dataset.attribution) +
      ' · 数据来自 <a href="' + esc(app.dataset.upstream) + '" target="_blank" rel="noopener">exercises-dataset</a>' +
      '（MIT），演示媒体版权归 Gym visual 所有，此处引用其授权分发。';

    var favBadge = $("#ex-fav-badge");
    favBadge.hidden = !favs.length;
    favBadge.textContent = favs.length;

    bindChrome();
    renderPlans();

    fetch(app.dataset.src, { credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (payload) {
        data = payload;
        data.exercises.forEach(function (e) { byId[e.id] = e; });
        buildControls();
        apply();
        $("#ex-loading").hidden = true;
        renderFavs();
        // Plans were rendered before the data arrived (only ids are stored), so
        // they need a second pass to pick up names and thumbnails.
        renderPlans();
      })
      .catch(function (err) {
        $("#ex-loading").hidden = true;
        var box = $("#ex-error");
        box.hidden = false;
        box.textContent = "动作数据载入失败（" + err.message + "）。请刷新重试。";
      });
  }

  /* ---------- tabs ---------- */
  function showView(next) {
    view = next;
    Array.prototype.forEach.call(document.querySelectorAll(".ex-tab"), function (tab) {
      tab.setAttribute("aria-selected", String(tab.dataset.view === next));
    });
    Array.prototype.forEach.call(document.querySelectorAll(".ex-view"), function (sec) {
      sec.hidden = sec.dataset.view !== next;
    });
    if (next === "fav") renderFavs();
    if (next === "plan") renderPlans();
  }

  function bindChrome() {
    Array.prototype.forEach.call(document.querySelectorAll(".ex-tab"), function (tab) {
      tab.addEventListener("click", function () { showView(tab.dataset.view); });
    });

    var search = $("#ex-search");
    var timer = null;
    search.addEventListener("input", function () {
      clearTimeout(timer);
      // 1,324 records make a keystroke-by-keystroke re-render pointless; 120 ms
      // is under the threshold where typing feels laggy.
      timer = setTimeout(function () {
        filters.q = search.value.trim().toLowerCase();
        apply();
      }, 120);
    });

    $("#ex-clear").addEventListener("click", function () {
      filters = { q: "", category: "", equipment: "", target: "", sort: filters.sort };
      search.value = "";
      $("#ex-equip").value = "";
      $("#ex-target").value = "";
      buildChips();
      apply();
    });

    $("#ex-equip").addEventListener("change", function () { filters.equipment = this.value; apply(); });
    $("#ex-target").addEventListener("change", function () { filters.target = this.value; apply(); });
    $("#ex-sort").addEventListener("change", function () { filters.sort = this.value; apply(); });
    $("#ex-more").addEventListener("click", function () { renderChunk(); });

    // Keep filling the grid while the button is on screen (phones: no repeated
    // tapping). The button stays in the DOM so it still works without IO support.
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && !$("#ex-more").hidden) renderChunk();
        });
      }, { rootMargin: "300px" }).observe($("#ex-more"));
    }

    $("#ex-fav-toplan").addEventListener("click", function () {
      var added = 0;
      favs.forEach(function (id) { if (addToPlan(id, true)) added++; });
      savePlans();
      renderPlans();
      toast(added ? "已加入 " + added + " 个动作" : "收藏的动作都已在计划里");
    });

    $("#ex-plan-select").addEventListener("change", function () {
      planStore.active = this.value;
      savePlans();
      renderPlans();
    });
    $("#ex-plan-new").addEventListener("click", function () {
      var name = prompt("新计划名称", "训练 " + (planStore.plans.length + 1));
      if (!name) return;
      var plan = { id: "p" + Date.now(), name: name.trim(), items: [] };
      planStore.plans.push(plan);
      planStore.active = plan.id;
      savePlans();
      renderPlans();
    });
    $("#ex-plan-rename").addEventListener("click", function () {
      var plan = activePlan();
      var name = prompt("重命名计划", plan.name);
      if (!name) return;
      plan.name = name.trim();
      savePlans();
      renderPlans();
    });
    $("#ex-plan-clear").addEventListener("click", function () {
      var plan = activePlan();
      if (!plan.items.length || !confirm("清空「" + plan.name + "」里的 " + plan.items.length + " 个动作？")) return;
      plan.items = [];
      savePlans();
      renderPlans();
    });
    $("#ex-plan-del").addEventListener("click", function () {
      if (planStore.plans.length < 2) { toast("至少要留一个计划"); return; }
      var plan = activePlan();
      if (!confirm("删除计划「" + plan.name + "」？")) return;
      planStore.plans = planStore.plans.filter(function (p) { return p.id !== plan.id; });
      planStore.active = planStore.plans[0].id;
      savePlans();
      renderPlans();
    });
    $("#ex-plan-start").addEventListener("click", startSession);

    $("#ex-detail-close").addEventListener("click", closeDetail);
    $("#ex-detail").addEventListener("click", function (ev) {
      if (ev.target === this) closeDetail();
    });
    $("#ex-detail-prev").addEventListener("click", function () { stepDetail(-1); });
    $("#ex-detail-next").addEventListener("click", function () { stepDetail(1); });
    $("#ex-detail-fav").addEventListener("click", function () {
      toggleFav(detailList[detailIndex].id);
      renderDetail();
    });
    $("#ex-detail-add").addEventListener("click", function () {
      addToPlan(detailList[detailIndex].id);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".ex-lang"), function (btn) {
      btn.addEventListener("click", function () {
        lang = btn.dataset.lang;
        write(STORE.lang, lang);
        renderDetail();
      });
    });

    $("#ex-timer-close").addEventListener("click", endSession);
    $("#ex-timer-primary").addEventListener("click", timerPrimary);
    $("#ex-timer-pause").addEventListener("click", togglePause);
    $("#ex-timer-prev").addEventListener("click", function () { sessionStep(-1); });
    $("#ex-timer-next").addEventListener("click", function () { sessionStep(1); });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        if (!$("#ex-timer").hidden) endSession();
        else if (!$("#ex-detail").hidden) closeDetail();
        return;
      }
      if ($("#ex-detail").hidden) return;
      if (ev.key === "ArrowLeft") stepDetail(-1);
      if (ev.key === "ArrowRight") stepDetail(1);
    });

    // Plan rows: field edits and the ↑ ↓ ⤢ ✕ buttons (delegated, because the
    // rows are re-rendered on every change).
    $("#ex-plan-list").addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-plan]");
      if (!btn) return;
      var row = btn.closest(".ex-planrow");
      var plan = activePlan();
      var i = Number(row.dataset.idx);
      var act = btn.dataset.plan;

      if (act === "open") {
        openDetail(row.dataset.id);
      } else if (act === "del") {
        plan.items.splice(i, 1);
        savePlans();
        renderPlans();
      } else if (act === "up" && i > 0) {
        plan.items.splice(i - 1, 0, plan.items.splice(i, 1)[0]);
        savePlans();
        renderPlans();
      } else if (act === "down" && i < plan.items.length - 1) {
        plan.items.splice(i + 1, 0, plan.items.splice(i, 1)[0]);
        savePlans();
        renderPlans();
      }
    });

    $("#ex-plan-list").addEventListener("input", function (ev) {
      var input = ev.target.closest("input[data-field]");
      if (!input) return;
      var plan = activePlan();
      var item = plan.items[Number(input.closest(".ex-planrow").dataset.idx)];
      if (!item) return;
      var field = input.dataset.field;
      if (field === "reps") {
        item.reps = input.value.slice(0, 24);
      } else {
        var value = Math.max(0, Math.min(600, Number(input.value) || 0));
        item[field] = field === "sets" ? Math.max(1, value) : value;
      }
      savePlans();
      // Only the summary depends on these numbers, so it is refreshed in place:
      // re-rendering the rows would take focus away from the field being typed in.
      updatePlanSummary();
    });

    // A phone that was locked mid-rest must catch up the moment it comes back —
    // and the wake lock has to be re-requested, because browsers drop it while
    // the page is hidden.
    document.addEventListener("visibilitychange", function () {
      if (document.hidden || !session) return;
      requestWakeLock();
      tickSession();
    });
  }

  /* ---------- library ---------- */
  function buildControls() {
    var equip = $("#ex-equip");
    var target = $("#ex-target");
    data.facets.equipment.forEach(function (f) {
      equip.insertAdjacentHTML("beforeend",
        '<option value="' + esc(f.value) + '">' + esc(label("equipment", f.value)) +
        " (" + f.count + ")</option>");
    });
    data.facets.target.forEach(function (f) {
      target.insertAdjacentHTML("beforeend",
        '<option value="' + esc(f.value) + '">' + esc(label("muscle", f.value)) +
        " (" + f.count + ")</option>");
    });
    buildChips();
  }

  function buildChips() {
    var box = $("#ex-cat");
    var html = '<button type="button" class="ex-chip" data-cat="" aria-pressed="' +
      (filters.category ? "false" : "true") + '">全部</button>';
    data.facets.category.forEach(function (f) {
      html += '<button type="button" class="ex-chip" data-cat="' + esc(f.value) +
        '" aria-pressed="' + (filters.category === f.value) + '">' +
        esc(label("category", f.value)) +
        '<span class="ex-chip-n">' + f.count + "</span></button>";
    });
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll(".ex-chip"), function (chip) {
      chip.addEventListener("click", function () {
        filters.category = chip.dataset.cat;
        buildChips();
        apply();
      });
    });
  }

  function matches(ex) {
    if (filters.category && ex.category !== filters.category) return false;
    if (filters.equipment && ex.equipment !== filters.equipment) return false;
    if (filters.target && ex.target !== filters.target) return false;
    if (!filters.q) return true;

    // Search across both languages: the name is English upstream, so typing a
    // Chinese word has to reach the translated labels (腹肌 → abs) as well as
    // the muscle names the record carries.
    var hay = [
      ex.name, ex.id, ex.category, label("category", ex.category),
      ex.equipment, label("equipment", ex.equipment),
      ex.target, label("muscle", ex.target),
      ex.muscleGroup, label("muscle", ex.muscleGroup),
      ex.secondaryMuscles.join(" ")
    ].join(" ").toLowerCase();
    return filters.q.split(/\s+/).every(function (word) { return hay.indexOf(word) >= 0; });
  }

  function apply() {
    list = data.exercises.filter(matches);
    var sort = filters.sort;
    list.sort(function (a, b) {
      if (sort === "category") {
        return label("category", a.category).localeCompare(label("category", b.category), "zh") ||
          a.name.localeCompare(b.name);
      }
      if (sort === "equipment") {
        return label("equipment", a.equipment).localeCompare(label("equipment", b.equipment), "zh") ||
          a.name.localeCompare(b.name);
      }
      return a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
    });

    $("#ex-grid").innerHTML = "";
    shown = 0;
    renderChunk();

    var active = filters.q || filters.category || filters.equipment || filters.target;
    $("#ex-clear").hidden = !active;
    $("#ex-count").textContent = active
      ? "匹配 " + list.length + " / " + data.count + " 个动作"
      : "共 " + data.count + " 个动作";
    $("#ex-empty").hidden = list.length > 0;
  }

  function renderChunk() {
    var slice = list.slice(shown, shown + PAGE_SIZE);
    var html = slice.map(cardHTML).join("");
    $("#ex-grid").insertAdjacentHTML("beforeend", html);
    shown += slice.length;
    var more = $("#ex-more");
    more.hidden = shown >= list.length;
    more.textContent = "加载更多（还有 " + (list.length - shown) + " 个）";
  }

  function mediaURL(ex, kind) {
    var ext = kind === "gif" ? "gif" : "jpg";
    return app.dataset.mediaBase + "/" + (kind === "gif" ? "videos" : "images") +
      "/" + ex.id + "-" + ex.mediaId + "." + ext;
  }

  function cardHTML(ex) {
    var fav = favs.indexOf(ex.id) >= 0;
    return '<article class="ex-card' + (fav ? " is-fav" : "") + '" data-id="' + esc(ex.id) + '">' +
      '<button type="button" class="ex-card-media" data-act="open" aria-label="查看 ' + esc(ex.name) + '">' +
      '<img src="' + esc(mediaURL(ex, "jpg")) + '" alt="' + esc(ex.name) + '" loading="lazy" decoding="async">' +
      "</button>" +
      '<div class="ex-card-body">' +
      '<h3 class="ex-card-name">' + esc(ex.name) + "</h3>" +
      '<p class="ex-card-meta">' + esc(label("muscle", ex.target)) + " · " +
      esc(label("equipment", ex.equipment)) + "</p>" +
      '<div class="ex-card-acts">' +
      '<button type="button" class="ex-btn ghost small grow" data-act="fav" title="收藏">' +
      (fav ? "★ 已收藏" : "☆ 收藏") + "</button>" +
      '<button type="button" class="ex-btn ghost small grow" data-act="add" title="加入当前计划">＋ 计划</button>' +
      "</div></div></article>";
  }

  // One delegated listener for every grid (library + favourites).
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest("[data-act]") : null;
    if (!btn || !app || !app.contains(btn)) return;
    var act = btn.dataset.act;
    if (act === "golib") { ev.preventDefault(); showView("lib"); return; }

    var card = btn.closest(".ex-card");
    var id = card && card.dataset.id;
    if (!id) return;

    if (act === "open") openDetail(id);
    else if (act === "fav") {
      toggleFav(id);
      // Repaint this card in place: re-rendering the grid would throw away the
      // scroll position (and the 60+ thumbnails already in the DOM).
      card.outerHTML = cardHTML(byId[id]);
      if (view === "fav") renderFavs();
    } else if (act === "add") addToPlan(id);
  });

  /* ---------- favourites ---------- */
  function toggleFav(id) {
    var at = favs.indexOf(id);
    if (at >= 0) favs.splice(at, 1);
    else favs.push(id);
    write(STORE.favs, favs);
    var badge = $("#ex-fav-badge");
    badge.hidden = !favs.length;
    badge.textContent = favs.length;
  }

  function renderFavs() {
    if (!data) return;
    var grid = $("#ex-fav-grid");
    var items = favs.map(function (id) { return byId[id]; }).filter(Boolean);
    grid.innerHTML = items.map(cardHTML).join("");
    $("#ex-fav-empty").hidden = items.length > 0;
    $("#ex-fav-count").textContent = items.length ? "已收藏 " + items.length + " 个动作" : "";
    $("#ex-fav-toplan").hidden = items.length === 0;
  }

  /* ---------- detail ---------- */
  function openDetail(id) {
    // Prev/next walks whatever the user is looking at: the filtered library, or
    // the favourites grid.
    detailList = view === "fav"
      ? favs.map(function (fid) { return byId[fid]; }).filter(Boolean)
      : list;
    detailIndex = detailList.findIndex(function (ex) { return ex.id === id; });
    if (detailIndex < 0) { detailList = [byId[id]]; detailIndex = 0; }
    renderDetail();
    $("#ex-detail").hidden = false;
    document.body.classList.add("ex-modal-open");
  }

  function closeDetail() {
    $("#ex-detail").hidden = true;
    $("#ex-detail-gif").removeAttribute("src");
    if ($("#ex-timer").hidden) document.body.classList.remove("ex-modal-open");
  }

  function stepDetail(delta) {
    var next = detailIndex + delta;
    if (next < 0 || next >= detailList.length) return;
    detailIndex = next;
    renderDetail();
  }

  function renderDetail() {
    var ex = detailList[detailIndex];
    if (!ex) return;
    var useLang = ex.instructions[lang] ? lang : Object.keys(ex.instructions)[0];

    $("#ex-detail-name").textContent = ex.name;
    $("#ex-detail-gif").src = mediaURL(ex, "gif");
    $("#ex-detail-gif").alt = ex.name + " 动作演示";

    var badges = [
      '<span class="ex-pill target">' + esc(label("muscle", ex.target)) + "</span>",
      '<span class="ex-pill">' + esc(label("category", ex.category)) + "</span>",
      '<span class="ex-pill">' + esc(label("equipment", ex.equipment)) + "</span>",
      '<span class="ex-pill">' + esc(ex.id) + "</span>"
    ].join("");
    $("#ex-detail-badges").innerHTML = badges;

    var fav = favs.indexOf(ex.id) >= 0;
    $("#ex-detail-fav").textContent = fav ? "★ 已收藏" : "☆ 收藏";
    Array.prototype.forEach.call(document.querySelectorAll(".ex-lang"), function (btn) {
      btn.setAttribute("aria-pressed", String(btn.dataset.lang === useLang));
      btn.hidden = !ex.instructions[btn.dataset.lang];
    });

    $("#ex-detail-instr").textContent = ex.instructions[useLang] || "";
    $("#ex-detail-steps").innerHTML = (ex.steps[useLang] || []).map(function (step) {
      return "<li>" + esc(step) + "</li>";
    }).join("");

    var muscles = "主要肌群：" + label("muscle", ex.muscleGroup);
    if (ex.secondaryMuscles && ex.secondaryMuscles.length) {
      muscles += "　协同肌群：" + ex.secondaryMuscles.map(function (m) {
        return label("muscle", m);
      }).join("、");
    }
    $("#ex-detail-muscles").textContent = muscles;

    $("#ex-detail-pos").textContent = (detailIndex + 1) + " / " + detailList.length;
    $("#ex-detail-prev").disabled = detailIndex === 0;
    $("#ex-detail-next").disabled = detailIndex === detailList.length - 1;
  }

  /* ---------- plans ---------- */
  function activePlan() {
    var plan = planStore.plans.filter(function (p) { return p.id === planStore.active; })[0];
    if (!plan) {
      plan = { id: "p1", name: DEFAULT_PLAN, items: [] };
      planStore.plans.push(plan);
      planStore.active = plan.id;
    }
    return plan;
  }

  function savePlans() { write(STORE.plans, planStore); }

  function addToPlan(id, quiet) {
    var plan = activePlan();
    var exists = plan.items.some(function (item) { return item.id === id; });
    if (!exists) {
      plan.items.push({ id: id, sets: 3, reps: "12", rest: 60, secs: 0 });
      savePlans();
      renderPlans();
    }
    if (!quiet) {
      toast(exists ? "「" + byId[id].name + "」已在计划里" : "已加入「" + plan.name + "」");
    }
    return !exists;
  }

  function renderPlans() {
    var badge = $("#ex-plan-badge");
    var plan = activePlan();
    badge.hidden = !plan.items.length;
    badge.textContent = plan.items.length;

    $("#ex-plan-select").innerHTML = planStore.plans.map(function (p) {
      return '<option value="' + esc(p.id) + '"' + (p.id === planStore.active ? " selected" : "") +
        ">" + esc(p.name) + "（" + p.items.length + "）</option>";
    }).join("");

    var rows = plan.items.map(function (item, i) {
      var ex = byId[item.id];
      if (!ex) return "";
      return '<li class="ex-planrow" data-idx="' + i + '" data-id="' + esc(ex.id) + '">' +
        '<span class="ex-planidx">' + (i + 1) + "</span>" +
        '<img src="' + esc(mediaURL(ex, "jpg")) + '" alt="" loading="lazy" decoding="async">' +
        '<div class="ex-planmain">' +
        '<p class="ex-planname">' + esc(ex.name) + "</p>" +
        '<div class="ex-planfields">' +
        '<label>组数 <input type="number" min="1" max="20" value="' + item.sets + '" data-field="sets"></label>' +
        '<label>次数 <input type="text" class="ex-reps" value="' + esc(item.reps) + '" data-field="reps"></label>' +
        '<label>组间休息 <input type="number" min="0" max="600" step="5" value="' + item.rest + '" data-field="rest"> 秒</label>' +
        '<label>每组时长 <input type="number" min="0" max="600" step="5" value="' + item.secs + '" data-field="secs"> 秒</label>' +
        "</div></div>" +
        '<div class="ex-planacts">' +
        '<button type="button" class="ex-btn ghost small" data-plan="up" title="上移"' + (i === 0 ? " disabled" : "") + ">↑</button>" +
        '<button type="button" class="ex-btn ghost small" data-plan="down" title="下移"' + (i === plan.items.length - 1 ? " disabled" : "") + ">↓</button>" +
        '<button type="button" class="ex-btn ghost small" data-plan="open" title="查看动作">⤢</button>' +
        '<button type="button" class="ex-btn ghost small" data-plan="del" title="移出计划">✕</button>' +
        "</div></li>";
    }).join("");

    $("#ex-plan-list").innerHTML = rows;
    $("#ex-plan-empty").hidden = plan.items.length > 0;
    $("#ex-plan-foot").hidden = plan.items.length === 0;
    updatePlanSummary();
  }

  /* "共 N 个动作、M 组，预计 X 分钟" — also called while the number fields are
     being typed in, so it must never rebuild the rows. */
  function updatePlanSummary() {
    var plan = activePlan();
    if (!plan.items.length) {
      $("#ex-plan-summary").textContent = "";
      return;
    }
    var sets = plan.items.reduce(function (n, item) { return n + item.sets; }, 0);
    // Untimed sets still take time: count them as 35 s of work each, which is
    // close enough for a rough "how long will this take" number.
    var seconds = plan.items.reduce(function (n, item) {
      return n + item.sets * ((item.secs > 0 ? item.secs : 35) + item.rest);
    }, 0);
    $("#ex-plan-summary").textContent = "「" + plan.name + "」共 " + plan.items.length +
      " 个动作、" + sets + " 组，预计 " + Math.max(1, Math.round(seconds / 60)) + " 分钟";
  }

  /* ---------- toast ---------- */
  function toast(message) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "ex-toast";
      app.appendChild(toastEl);
    }
    toastEl.textContent = message;
    toastEl.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-on"); }, 1800);
  }

  /* ---------- guided session ---------- */
  /* Steps are expanded up front (3 sets → 3 steps) so prev/next can move through
     the whole workout linearly. Timing is deadline-based rather than
     tick-counting: a backgrounded tab throttles timers, and a phone that was
     locked for a minute must come back with the correct remaining time. */
  function buildSteps(plan) {
    var steps = [];
    plan.items.forEach(function (item, itemIndex) {
      var ex = byId[item.id];
      if (!ex) return;
      var last = itemIndex === plan.items.length - 1;
      for (var set = 1; set <= item.sets; set++) {
        steps.push({
          ex: ex,
          set: set,
          sets: item.sets,
          reps: item.reps,
          rest: item.rest,
          secs: item.secs,
          // No rest after the very last set of the workout.
          restAfter: !(last && set === item.sets)
        });
      }
    });
    return steps;
  }

  function startSession() {
    var plan = activePlan();
    var steps = buildSteps(plan);
    if (!steps.length) { toast("计划里还没有动作"); return; }

    session = {
      plan: plan,
      steps: steps,
      i: 0,
      phase: "ready",      // ready → work → rest → (next) … → done
      deadline: 0,
      startedAt: 0,
      paused: false,
      pausedLeft: 0,
      interval: null,
      wakeLock: null
    };

    $("#ex-timer").hidden = false;
    document.body.classList.add("ex-modal-open");
    requestWakeLock();
    renderSession();
  }

  function requestWakeLock() {
    // Best effort: keeps the screen on while training. Unsupported browsers and
    // a rejected request (battery saver) simply leave the screen to time out.
    try {
      if (navigator.wakeLock && navigator.wakeLock.request) {
        navigator.wakeLock.request("screen").then(function (lock) {
          if (session) session.wakeLock = lock;
          else lock.release();
        }).catch(function () {});
      }
    } catch (e) {}
  }

  function releaseWakeLock() {
    try { if (session && session.wakeLock) session.wakeLock.release(); } catch (e) {}
  }

  function currentStep() { return session && session.steps[session.i]; }

  function renderSession() {
    var step = currentStep();
    if (!step) return;
    var phaseText = { ready: "准备", work: "进行中", rest: "休息" };
    var total = session.steps.length;

    $("#ex-timer-progress").textContent = "第 " + (session.i + 1) + " / " + total + " 组 · " +
      step.ex.name;
    $("#ex-timer-name").textContent = step.ex.name;
    $("#ex-timer-gif").src = mediaURL(step.ex, "gif");
    $("#ex-timer-gif").alt = step.ex.name;

    var phase = $("#ex-timer-phase");
    phase.textContent = phaseText[session.phase] + " · 第 " + step.set + " / " + step.sets + " 组";
    phase.dataset.phase = session.phase;

    $("#ex-timer-target").textContent = "目标 " + step.reps + " 次" +
      (step.secs > 0 ? "（每组 " + step.secs + " 秒计时）" : "");

    var primary = $("#ex-timer-primary");
    if (session.phase === "ready") primary.textContent = step.secs > 0 ? "开始本组（" + step.secs + " 秒）" : "开始本组";
    else if (session.phase === "work") primary.textContent = "完成本组";
    else primary.textContent = "跳过休息";

    $("#ex-timer-pause").hidden = session.phase === "ready";
    $("#ex-timer-pause").textContent = session.paused ? "继续" : "暂停";

    var next = session.steps[session.i + 1];
    $("#ex-timer-nextup").textContent = next
      ? "接下来：" + next.ex.name + "（第 " + next.set + " / " + next.sets + " 组）"
      : "这是最后一组，加油。";
  }

  function timerPrimary() {
    if (!session) return;
    if (session.phase === "ready") beginWork();
    else if (session.phase === "work") completeStep();
    else if (session.phase === "rest") endRest();
  }

  function beginWork() {
    var step = currentStep();
    session.phase = "work";
    session.paused = false;
    session.startedAt = Date.now();
    // A timed set counts down; an untimed one counts up so you can see how long
    // the set is taking without being rushed by a clock.
    session.deadline = step.secs > 0 ? Date.now() + step.secs * 1000 : 0;
    startTicking();
    renderSession();
  }

  function beginRest() {
    var step = currentStep();
    session.phase = "rest";
    session.paused = false;
    session.deadline = Date.now() + step.rest * 1000;
    startTicking();
    renderSession();
  }

  function completeStep() {
    var step = currentStep();
    stopTicking();
    // A 0-second "rest" would only flash the rest screen and chime at nobody.
    if (step.restAfter && step.rest > 0) beginRest();
    else advance(1);
  }

  function endRest() {
    stopTicking();
    advance(1);
  }

  function advance(delta) {
    stopTicking();
    var next = session.i + delta;
    if (next >= session.steps.length) { finishSession(); return; }
    if (next < 0) next = 0;
    session.i = next;
    session.phase = "ready";
    session.paused = false;
    renderSession();
  }

  function sessionStep(delta) {
    if (!session) return;
    if (delta > 0 && session.phase !== "ready") { advance(1); return; }
    advance(delta);
  }

  function startTicking() {
    stopTicking();
    session.interval = setInterval(tickSession, 200);
    tickSession();
  }

  function stopTicking() {
    if (session && session.interval) {
      clearInterval(session.interval);
      session.interval = null;
    }
  }

  function remaining() {
    var step = currentStep();
    if (!session || !step) return 0;
    if (session.phase === "rest") return (session.deadline - Date.now()) / 1000;
    if (session.phase === "work") {
      return step.secs > 0 ? (session.deadline - Date.now()) / 1000
        : (Date.now() - session.startedAt) / 1000;
    }
    return 0;
  }

  function tickSession() {
    if (!session) return;
    var step = currentStep();
    if (!step || session.phase === "ready" || session.phase === "done") return;

    if (session.paused) {
      $("#ex-timer-clock").textContent = fmtClock(session.pausedLeft);
      return;
    }

    var left = remaining();
    var clock = $("#ex-timer-clock");
    clock.textContent = fmtClock(Math.abs(left));
    clock.classList.toggle("is-ending", session.phase === "rest" && left <= 5);

    if (session.phase === "rest" && left <= 0) {
      chime(2);
      vibrate([90, 60, 90]);
      endRest();
    } else if (session.phase === "work" && step.secs > 0 && left <= 0) {
      chime(1);
      vibrate(120);
      completeStep();
    }
  }

  function togglePause() {
    if (!session || session.phase === "ready") return;
    if (session.paused) {
      // Shift the deadline by however long the pause lasted.
      var drift = session.pausedLeft * 1000;
      session.paused = false;
      if (session.phase === "rest" || (currentStep() && currentStep().secs > 0)) {
        session.deadline = Date.now() + drift;
      } else {
        session.startedAt = Date.now() - (session.pausedWall - session.startedAt);
      }
      startTicking();
    } else {
      session.pausedLeft = remaining();
      session.pausedWall = Date.now();
      session.paused = true;
      stopTicking();
      tickSession();
    }
    renderSession();
  }

  function finishSession() {
    var name = session.plan.name;
    stopTicking();
    releaseWakeLock();
    session = null;
    closeTimer();
    toast("「" + name + "」完成，练得不错 💪");
  }

  function endSession() {
    if (!session) { closeTimer(); return; }
    if (!confirm("结束这次训练？进度不会保存。")) return;
    stopTicking();
    releaseWakeLock();
    session = null;
    closeTimer();
  }

  function closeTimer() {
    $("#ex-timer").hidden = true;
    $("#ex-timer-gif").removeAttribute("src");
    if ($("#ex-detail").hidden) document.body.classList.remove("ex-modal-open");
  }

  /* ---------- sound + haptics ---------- */
  var audioCtx = null;
  function chime(times) {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      if (!audioCtx) audioCtx = new Ctx();
      if (audioCtx.state === "suspended") audioCtx.resume();
      for (var i = 0; i < times; i++) {
        var at = audioCtx.currentTime + i * 0.22;
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, at);
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.18);
        osc.connect(gain).connect(audioCtx.destination);
        osc.start(at);
        osc.stop(at + 0.2);
      }
    } catch (e) {}
  }

  function vibrate(pattern) {
    try { if (navigator.vibrate) navigator.vibrate(pattern); } catch (e) {}
  }

  /* ---------- go ---------- */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
