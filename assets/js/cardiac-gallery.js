(function () {
  "use strict";
  function init() {
    var root = document.getElementById("cardiac-gallery");
    if (!root || root._cardiacGalleryInitialized) return;
    root._cardiacGalleryInitialized = true;
    var cards = Array.from(root.querySelectorAll(".gallery-card"));
    var buttons = Array.from(root.querySelectorAll("[data-filter]"));
    var viewer = root.querySelector("dialog"), content = viewer.querySelector(".gallery-viewer-content");
    var signedIn = false, current = null;
    function playable() { return cards.filter(function (card) { return !card.hidden && (!card.dataset.locked || signedIn); }); }
    function clearMedia() {
      content.querySelectorAll("video").forEach(function (video) { video.pause(); });
      content.replaceChildren();
    }
    function open(card) {
      if (card.dataset.locked && !signedIn) return;
      clearMedia();
      current = card;
      viewer.querySelector("h2").textContent = card.querySelector("h2").textContent;
      content.appendChild(card.querySelector(".gallery-content-template").content.cloneNode(true));
      var list = playable();
      viewer.querySelector(".gallery-position").textContent = (list.indexOf(card) + 1) + " / " + list.length;
      if (!viewer.open) viewer.showModal();
    }
    function move(direction) {
      var list = playable(), index = list.indexOf(current);
      if (list.length) open(list[(index + direction + list.length) % list.length]);
    }
    root.addEventListener("click", function (event) {
      var trigger = event.target.closest(".gallery-open");
      if (trigger) open(trigger.closest(".gallery-card"));
      if (event.target.closest(".gallery-close")) viewer.close();
      var arrow = event.target.closest("[data-direction]");
      if (arrow) move(Number(arrow.dataset.direction));
    });
    viewer.addEventListener("close", clearMedia);
    viewer.addEventListener("keydown", function (event) {
      // Preserve native video seek keys while the player has keyboard focus.
      if (event.target.tagName === "VIDEO") return;
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault(); move(event.key === "ArrowLeft" ? -1 : 1);
      }
    });
    root.querySelector(".gallery-toolbar").hidden = false;
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var filter = button.dataset.filter, count = 0;
        buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b === button)); });
        cards.forEach(function (card) {
          var show = filter === "all" || card.dataset.group === filter || (filter === "diagnostics" && card.dataset.diagnostic === "true");
          card.hidden = !show;
          if (show) count++;
        });
        document.getElementById("gallery-count").textContent = count + (count === 1 ? " animation" : " animations");
      });
    });
    function bindAuth() {
      if (!window.SiteAuth) return;
      root.querySelectorAll("[data-gallery-signin]").forEach(function (button) {
        button.addEventListener("click", function () { window.SiteAuth.openSignIn(); });
      });
      function refresh(user) {
        if (!root.isConnected) return;
        signedIn = !!user;
        if (!user && current && current.dataset.locked && viewer.open) viewer.close();
        root.querySelectorAll(".gallery-locked").forEach(function (block) {
          var target = block.querySelector(".gallery-private-preview");
          target.replaceChildren(); target.hidden = !user;
          block.querySelector(".gallery-gate").hidden = !!user;
          if (user) target.appendChild(block.querySelector(".gallery-preview-template").content.cloneNode(true));
        });
      }
      window.SiteAuth.onChange(refresh);
      window.SiteAuth.ready().then(function () { refresh(window.SiteAuth.user()); });
    }
    if (document.readyState === "complete") bindAuth();
    else window.addEventListener("load", bindAuth, { once: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
  document.addEventListener("turbo:load", init);
}());
