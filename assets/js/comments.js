/* Comments via giscus — GitHub Discussions as the comment backend.
 *
 * The markup (layouts/partials/comments.html) carries the configuration as data
 * attributes; this file turns it into the giscus <script> that renders the
 * widget. It exists as a script instead of an inline <script> in the partial
 * because on a Turbo navigation the scripts of a freshly swapped <body> never
 * execute (same reason player.js is wired on turbo:load) — here every page
 * appearance re-mounts the widget, and #giscus-host is a new node each time.
 *
 * Moderation is entirely on GitHub: repo → Discussions. Whatever you delete or
 * hide there is gone from the site on the next page load; there is no server of
 * ours in the path (see [params.giscus] in hugo.toml).
 */
(function () {
  "use strict";

  var SRC = "https://giscus.app/client.js";
  var ORIGIN = "https://giscus.app";

  /* giscus cannot read the site's CSS variables: it gets its own theme name.
     PaperMod's toggle stores the choice in <html data-theme> (auto/dark/light),
     so "auto" maps to giscus's matching "follow the OS" option. */
  function giscusTheme() {
    var t = document.documentElement.dataset.theme;
    if (t === "dark") return "dark";
    if (t === "light") return "light";
    return "preferred_color_scheme";
  }

  /* The widget loads its theme once; switching the site theme afterwards needs
     giscus's documented postMessage API. */
  function repaint() {
    var frame = document.querySelector("iframe.giscus-frame");
    if (!frame || !frame.contentWindow) return;
    frame.contentWindow.postMessage(
      { giscus: { setConfig: { theme: giscusTheme() } } },
      ORIGIN
    );
  }

  function mount() {
    var host = document.getElementById("giscus-host");
    if (!host || host.dataset.mounted === "1") return;
    var d = host.dataset;
    if (!d.repo || !d.repoId || !d.categoryId) return;   // not configured

    host.dataset.mounted = "1";
    host.textContent = "";

    var attrs = {
      "data-repo": d.repo,
      "data-repo-id": d.repoId,
      "data-category": d.category || "General",
      "data-category-id": d.categoryId,
      "data-mapping": d.mapping || "pathname",
      // 0: a page without a matching discussion still gets a comment box,
      // and giscus creates the thread on the first comment.
      "data-strict": "0",
      "data-reactions-enabled": d.reactionsEnabled || "1",
      "data-emit-metadata": "0",
      "data-input-position": d.inputPosition || "top",
      "data-theme": giscusTheme(),
      "data-lang": d.lang || "en",
      "data-loading": d.loading || "lazy"
    };

    var s = document.createElement("script");
    s.src = SRC;
    s.async = true;
    s.crossOrigin = "anonymous";
    Object.keys(attrs).forEach(function (k) { s.setAttribute(k, attrs[k]); });
    host.appendChild(s);
  }

  /* PaperMod's inline toggle handler flips <html data-theme> on click; this
     listener is registered later, so it sees the new value. */
  function wireThemeToggle() {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle || toggle.dataset.giscusWired === "1") return;
    toggle.dataset.giscusWired = "1";
    toggle.addEventListener("click", function () { setTimeout(repaint, 0); });
  }

  function init() {
    mount();
    wireThemeToggle();
  }

  document.addEventListener("turbo:load", init);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
