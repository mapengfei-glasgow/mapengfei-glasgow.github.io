// /papers/ board: view tabs, search, hide-done, group collapse, overdue flags.
// Read-only — the data lives in data/papers.yaml and is rendered by Hugo.
(function () {
  "use strict";
  var root = document.getElementById("pb");
  if (!root) return;

  function store(k, v) {
    try {
      if (v === undefined) return localStorage.getItem("pb:" + k);
      localStorage.setItem("pb:" + k, v);
    } catch (e) { return null; }
  }

  // ---- Views ----
  var tabs = root.querySelectorAll(".pb-tabs [data-view]");
  var views = root.querySelectorAll(".pb-view");
  function show(name) {
    tabs.forEach(function (t) { t.setAttribute("aria-selected", t.dataset.view === name ? "true" : "false"); });
    views.forEach(function (v) { v.hidden = v.dataset.view !== name; });
    store("view", name);
    filter();
  }
  tabs.forEach(function (t) { t.addEventListener("click", function () { show(t.dataset.view); }); });

  // ---- Overdue (relative to the viewer's today, not the build date) ----
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var overdue = 0;
  root.querySelectorAll(".pb-due").forEach(function (el) {
    var row = el.closest(".pb-row");
    var d = new Date(el.getAttribute("datetime") + "T00:00:00");
    if (row && row.dataset.status !== "done" && d < today) {
      el.classList.add("overdue");
      if (row.tagName === "TR") overdue++;
    }
  });
  var od = document.getElementById("pb-overdue");
  if (od) od.textContent = overdue;

  // ---- Group collapse ----
  root.querySelectorAll(".pb-group").forEach(function (g) {
    var btn = g.querySelector(".pb-caret");
    var key = "collapsed:" + g.dataset.paper;
    function set(c) {
      g.classList.toggle("collapsed", c);
      btn.setAttribute("aria-expanded", c ? "false" : "true");
      btn.setAttribute("aria-label", c ? "Expand group" : "Collapse group");
    }
    set(store(key) === "1");
    btn.addEventListener("click", function () {
      var c = !g.classList.contains("collapsed");
      set(c); store(key, c ? "1" : "0");
    });
  });

  // ---- Search + hide done ----
  var q = document.getElementById("pb-search");
  var hd = document.getElementById("pb-hidedone");
  var none = document.getElementById("pb-nomatch");
  hd.checked = store("hidedone") === "1";

  function filter() {
    var term = (q.value || "").trim().toLowerCase();
    var hideDone = hd.checked;
    var visible = 0;
    var active = root.querySelector(".pb-view:not([hidden])");
    root.querySelectorAll(".pb-row").forEach(function (r) {
      var hit = (!term || r.dataset.text.indexOf(term) !== -1) && !(hideDone && r.dataset.status === "done");
      r.classList.toggle("is-hidden", !hit);
      if (hit && active && active.contains(r)) visible++;
    });
    root.querySelectorAll(".pb-pcard").forEach(function (c) {
      var hit = !term || c.dataset.text.indexOf(term) !== -1;
      c.classList.toggle("is-hidden", !hit);
      if (hit && active && active.contains(c)) visible++;
    });
    root.querySelectorAll(".pb-group").forEach(function (g) {
      var any = g.querySelector(".pb-row:not(.is-hidden)");
      var titleHit = term && g.textContent.toLowerCase().indexOf(term) !== -1 && g.querySelector(".pb-gname").textContent.toLowerCase().indexOf(term) !== -1;
      g.classList.toggle("is-empty", !any && !titleHit && (term || hideDone));
    });
    root.querySelectorAll(".pb-col").forEach(function (c) {
      var n = c.querySelectorAll(".pb-row:not(.is-hidden), .pb-pcard:not(.is-hidden)").length;
      var badge = c.querySelector(".pb-colhead span");
      if (badge) badge.textContent = n;
      c.classList.toggle("is-zero", n === 0);
    });
    none.hidden = visible > 0;
  }
  q.addEventListener("input", filter);
  hd.addEventListener("change", function () { store("hidedone", hd.checked ? "1" : "0"); filter(); });

  var v = store("view");
  show(v === "kanban" || v === "pipeline" ? v : "table");
}());
