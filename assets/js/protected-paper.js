// Casual-access gate: the article remains in the public HTML source.
(function () {
  "use strict";
  var root = document.getElementById("protected-paper");
  if (!root) return;
  var gate = document.getElementById("paper-gate");
  var content = document.getElementById("paper-content");
  function refresh(user) {
    gate.hidden = !!user;
    content.hidden = !user;
    content.replaceChildren();
    if (user) {
      content.appendChild(document.getElementById("paper-body").content.cloneNode(true));
      if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise([content]).catch(function () {});
      }
    }
    // The article canvases are inserted after the chart script initialises.
    // Rebuild on sign-in and dispose detached charts on sign-out.
    if (window.dshCharts) window.dshCharts.renderAll();
  }
  function start() {
    if (!window.SiteAuth) return;
    document.getElementById("paper-signin").onclick = function () { window.SiteAuth.openSignIn(); };
    window.SiteAuth.onChange(refresh);
    window.SiteAuth.ready().then(function () { refresh(window.SiteAuth.user()); });
  }
  if (document.readyState !== "complete") document.addEventListener("DOMContentLoaded", start);
  else start();
}());
