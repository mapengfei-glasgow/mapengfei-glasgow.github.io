/* ------------------------------------------------------------------
   Files page: browse the R2 bucket as a folder tree, upload, copy links.

   Auth: the page reuses the site's AppWrite sign-in (window.SiteAuth from
   appwrite.js). Every Worker request carries an AppWrite JWT, which the Worker
   verifies before listing/uploading/deleting — there is no shared token.

   Listing is paginated (the Worker returns up to 1000 keys plus a cursor).
 ------------------------------------------------------------------ */

(function () {
  var root = document.getElementById("portal");
  if (!root) return;

  var API = (root.dataset.api || "").trim();
  if (API === "none") API = "";
  API = API.replace(/\/+$/, "");

  var EXPANDED_KEY = "ds-portal-open";
  var allFiles = [];
  var openPaths = loadExpanded();

  var el = {
    status: document.getElementById("portal-status"),
    signin: document.getElementById("portal-signin"),
    signout: document.getElementById("portal-signout"),
    uploadCard: document.getElementById("portal-upload-card"),
    filesCard: document.getElementById("portal-files-card"),
    drop: document.getElementById("portal-drop"),
    file: document.getElementById("portal-file"),
    prefix: document.getElementById("portal-prefix"),
    progress: document.getElementById("portal-progress"),
    filter: document.getElementById("portal-filter"),
    expand: document.getElementById("portal-expand"),
    collapse: document.getElementById("portal-collapse"),
    refresh: document.getElementById("portal-refresh"),
    tree: document.getElementById("portal-tree"),
    empty: document.getElementById("portal-empty"),
    count: document.getElementById("portal-count"),
  };

  /* ---------- small helpers ---------- */

  function loadExpanded() {
    try { return JSON.parse(localStorage.getItem(EXPANDED_KEY) || "{}") || {}; } catch (e) { return {}; }
  }

  function saveExpanded() {
    try { localStorage.setItem(EXPANDED_KEY, JSON.stringify(openPaths)); } catch (e) {}
  }

  function human(bytes) {
    if (!bytes && bytes !== 0) return "";
    var u = ["B", "KB", "MB", "GB"], i = 0, n = bytes;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + " " + u[i];
  }

  function when(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toISOString().slice(0, 10);
  }

  function show(node, visible) {
    if (!node) return;
    node.classList.toggle("hidden", !visible);
  }

  function setStatus(text, kind) {
    el.status.textContent = text;
    el.status.className = "portal-note" + (kind ? " " + kind : "");
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-1000px";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy") ? resolve() : reject(new Error("copy failed")); }
      catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  function flash(btn, text) {
    var old = btn.textContent;
    btn.textContent = text;
    btn.disabled = true;
    setTimeout(function () { btn.textContent = old; btn.disabled = false; }, 1200);
  }

  /* ---------- talking to the worker (JWT-authenticated) ---------- */

  function authHeaders(extra) {
    if (!window.SiteAuth) return Promise.reject(new Error("sign-in support not loaded"));
    return window.SiteAuth.jwt().then(function (jwt) {
      var h = { Authorization: "Bearer " + jwt };
      if (extra) for (var k in extra) h[k] = extra[k];
      return h;
    });
  }

  function api(method, path, body) {
    var isForm = body instanceof FormData;
    return authHeaders(isForm ? {} : { "content-type": "application/json" }).then(function (headers) {
      return fetch(API + path, {
        method: method,
        headers: headers,
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
      });
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
        return data;
      });
    });
  }

  function fetchAllFiles() {
    function page(cursor, acc) {
      return api("GET", "/api/list?limit=1000" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""))
        .then(function (data) {
          acc = acc.concat(data.files || []);
          if (data.truncated && data.cursor) return page(data.cursor, acc);
          return acc;
        });
    }
    return page(null, []);
  }

  /* ---------- folder tree ---------- */

  function buildTree(files) {
    var rootNode = { name: "", path: "", folders: {}, files: [] };
    files.forEach(function (f) {
      var parts = String(f.key).split("/");
      var name = parts.pop();
      var node = rootNode;
      var path = "";
      parts.forEach(function (part) {
        path = path ? path + "/" + part : part;
        if (!node.folders[part]) node.folders[part] = { name: part, path: path, folders: {}, files: [] };
        node = node.folders[part];
      });
      node.files.push({ name: name, key: f.key, size: f.size, uploaded: f.uploaded, url: f.url });
    });
    return rootNode;
  }

  function totalSize(node) {
    var sum = node.files.reduce(function (a, f) { return a + (f.size || 0); }, 0);
    Object.keys(node.folders).forEach(function (k) { sum += totalSize(node.folders[k]); });
    return sum;
  }

  function countFiles(node) {
    var n = node.files.length;
    Object.keys(node.folders).forEach(function (k) { n += countFiles(node.folders[k]); });
    return n;
  }

  function fileMatches(f, q) { return !q || (f.name + " " + f.key).toLowerCase().indexOf(q) !== -1; }

  function folderMatches(node, q) {
    if (!q) return true;
    if (node.files.some(function (f) { return fileMatches(f, q); })) return true;
    return Object.keys(node.folders).some(function (k) { return folderMatches(node.folders[k], q); });
  }

  function renderFileRow(f) {
    var li = document.createElement("li");
    li.className = "portal-file";

    var row = document.createElement("div");
    row.className = "portal-filerow";

    var a = document.createElement("a");
    a.className = "portal-filename";
    a.href = f.url;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = f.name;
    a.title = f.key;
    row.appendChild(a);

    var meta = document.createElement("span");
    meta.className = "portal-filemeta";
    meta.textContent = [human(f.size), when(f.uploaded)].filter(Boolean).join(" · ");
    row.appendChild(meta);

    var acts = document.createElement("span");
    acts.className = "portal-fileacts";

    var copy = document.createElement("button");
    copy.type = "button";
    copy.className = "portal-btn small";
    copy.textContent = "Copy link";
    copy.addEventListener("click", function () {
      copyText(f.url).then(function () { flash(copy, "Copied ✓"); },
                           function () { flash(copy, "Copy failed"); });
    });
    acts.appendChild(copy);

    var del = document.createElement("button");
    del.type = "button";
    del.className = "portal-btn small danger";
    del.textContent = "Delete";
    del.addEventListener("click", function () {
      if (!confirm("Delete " + f.key + " from the bucket?")) return;
      del.disabled = true;
      api("POST", "/api/delete", { key: f.key }).then(function () {
        allFiles = allFiles.filter(function (x) { return x.key !== f.key; });
        render();
      }).catch(function (e) {
        alert("Delete failed: " + e.message);
        del.disabled = false;
      });
    });
    acts.appendChild(del);

    row.appendChild(acts);
    li.appendChild(row);
    return li;
  }

  function toggleFolder(path, toggle, body) {
    var nowOpen = body.hidden;
    body.hidden = !nowOpen;
    toggle.classList.toggle("open", nowOpen);
    var caret = toggle.querySelector(".caret");
    if (caret) caret.textContent = nowOpen ? "▾" : "▸";
    toggle.setAttribute("aria-expanded", nowOpen ? "true" : "false");
    if (nowOpen) openPaths[path] = 1; else delete openPaths[path];
    saveExpanded();
  }

  function renderFolder(node, container, q) {
    Object.keys(node.folders).sort().forEach(function (key) {
      var child = node.folders[key];
      if (!folderMatches(child, q)) return;

      var li = document.createElement("li");
      li.className = "portal-folder";

      var row = document.createElement("div");
      row.className = "portal-folderrow";

      var open = Boolean(openPaths[child.path]) || Boolean(q);
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "portal-toggle" + (open ? " open" : "");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", (open ? "Collapse " : "Expand ") + child.name);
      toggle.innerHTML = '<span class="caret" aria-hidden="true">' + (open ? "▾" : "▸") + "</span>";
      row.appendChild(toggle);

      var name = document.createElement("button");
      name.type = "button";
      name.className = "portal-foldername";
      name.textContent = child.name + "/";
      row.appendChild(name);

      var n = countFiles(child);
      var meta = document.createElement("span");
      meta.className = "portal-filemeta";
      meta.textContent = n + " file" + (n === 1 ? "" : "s") +
                         (totalSize(child) ? " · " + human(totalSize(child)) : "");
      row.appendChild(meta);

      li.appendChild(row);

      var body = document.createElement("ul");
      body.className = "portal-children";
      body.hidden = !open;
      renderFolder(child, body, q);
      child.files
        .filter(function (f) { return fileMatches(f, q); })
        .sort(function (a, b) { return a.name.localeCompare(b.name); })
        .forEach(function (f) { body.appendChild(renderFileRow(f)); });
      li.appendChild(body);
      container.appendChild(li);

      toggle.addEventListener("click", function () { toggleFolder(child.path, toggle, body); });
      name.addEventListener("click", function () { toggleFolder(child.path, toggle, body); });
    });
  }

  function render() {
    var q = (el.filter.value || "").trim().toLowerCase();
    var tree = buildTree(allFiles);
    el.tree.innerHTML = "";

    renderFolder(tree, el.tree, q);

    // keys without a folder live at the root of the tree
    tree.files
      .filter(function (f) { return fileMatches(f, q); })
      .sort(function (a, b) { return a.name.localeCompare(b.name); })
      .forEach(function (f) { el.tree.appendChild(renderFileRow(f)); });

    var shown = countFiles(tree);
    var total = allFiles.length;
    el.count.textContent = "(" + (q ? shown + " of " + total : total) + ")";
    show(el.empty, total === 0 || Boolean(q && shown === 0));
    el.empty.textContent = total === 0 ? "The bucket is empty." : "No files match that filter.";
  }

  /* ---------- uploads ---------- */

  function upload(fileList) {
    var list = Array.prototype.slice.call(fileList || []);
    if (!list.length) return;

    authHeaders().then(function (headers) {
      list.forEach(function (f) {
        var li = document.createElement("li");
        li.textContent = f.name + " — waiting…";
        el.progress.appendChild(li);

        var form = new FormData();
        form.append("file", f);
        form.append("prefix", el.prefix.value || "uploads");

        var xhr = new XMLHttpRequest();
        xhr.open("POST", API + "/api/upload");
        xhr.setRequestHeader("Authorization", headers.Authorization);
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) li.textContent = f.name + " — " + Math.round((e.loaded / e.total) * 100) + "%";
        };
        xhr.onload = function () {
          var data = {};
          try { data = JSON.parse(xhr.responseText || "{}"); } catch (e) {}
          if (xhr.status >= 200 && xhr.status < 300 && data.files && data.files.length) {
            li.textContent = f.name + " — uploaded ✓";
            li.className = "ok";
          } else {
            li.textContent = f.name + " — failed: " + (data.error || ("HTTP " + xhr.status));
            li.className = "bad";
          }
          refresh();
        };
        xhr.onerror = function () { li.textContent = f.name + " — network error"; li.className = "bad"; };
        xhr.send(form);
      });
    }).catch(function (e) {
      alert("Upload needs a signed-in session: " + e.message);
    });
  }

  /* ---------- session state ---------- */

  function signedOut(message) {
    show(el.uploadCard, false);
    show(el.filesCard, false);
    show(el.signin, true);
    show(el.signout, false);
    allFiles = [];
    setStatus(message || "Sign in to see and manage the files in this bucket.", "warn");
  }

  /* " (id: abc123, aa@example.com)" — handy when locking ALLOWED_USERS down */
  function accountSuffix() {
    var u = (window.SiteAuth && window.SiteAuth.user && window.SiteAuth.user()) || {};
    var bits = [];
    if (u.name) bits.push(String(u.name));
    if (u.$id) bits.push("id: " + u.$id);
    if (u.email) bits.push(String(u.email));
    return bits.length ? " as " + bits.join(" · ") : "";
  }

  function signedIn(name) {
    show(el.signin, false);
    show(el.signout, true);
    show(el.uploadCard, true);
    show(el.filesCard, true);
    setStatus("Signed in as " + name + " — loading the bucket…", "ok");
    refresh();
  }

  function refresh() {
    if (!API) {
      setStatus("No portal backend configured (params.portalApi is empty).", "warn");
      show(el.filesCard, false);
      show(el.uploadCard, false);
      return Promise.resolve();
    }
    return fetchAllFiles().then(function (files) {
      allFiles = files;
      render();
      setStatus("Signed in" + accountSuffix() + " — " + files.length + " file" +
                (files.length === 1 ? "" : "s") + " in the bucket.", "ok");
    }).catch(function (e) {
      setStatus("Could not load the file list: " + e.message, "warn");
    });
  }

  function wireSession() {
    if (!window.SiteAuth) {
      signedOut("Sign-in support failed to load — reload the page.");
      return;
    }
    el.signin.addEventListener("click", function () { window.SiteAuth.openSignIn(); });
    el.signout.addEventListener("click", function () {
      window.SiteAuth.signOut().then(function () { signedOut("Signed out."); });
    });
    window.SiteAuth.onChange(function (user) {
      if (user) signedIn(user.name || user.email || "your account");
      else signedOut();
    });
    window.SiteAuth.ready().then(function (isSignedIn) {
      var user = window.SiteAuth.user();
      if (isSignedIn && user) signedIn(user.name || user.email || "your account");
      else signedOut();
    });
  }

  /* ---------- wiring ---------- */

  el.refresh.addEventListener("click", refresh);
  el.filter.addEventListener("input", render);
  el.expand.addEventListener("click", function () {
    (function walk(node) {
      Object.keys(node.folders).forEach(function (k) {
        openPaths[node.folders[k].path] = 1;
        walk(node.folders[k]);
      });
    })(buildTree(allFiles));
    saveExpanded();
    render();
  });
  el.collapse.addEventListener("click", function () {
    openPaths = {};
    saveExpanded();
    render();
  });

  el.drop.addEventListener("click", function () { el.file.click(); });
  el.drop.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.file.click(); }
  });
  el.file.addEventListener("change", function () { upload(el.file.files); el.file.value = ""; });
  ["dragenter", "dragover"].forEach(function (ev) {
    el.drop.addEventListener(ev, function (e) { e.preventDefault(); el.drop.classList.add("over"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    el.drop.addEventListener(ev, function (e) { e.preventDefault(); el.drop.classList.remove("over"); });
  });
  el.drop.addEventListener("drop", function (e) {
    if (e.dataTransfer && e.dataTransfer.files) upload(e.dataTransfer.files);
  });

  /* appwrite.js defines window.SiteAuth and loads after this file (defer order),
     so give it a moment before deciding that sign-in support is missing. */
  (function startWhenAuthReady() {
    if (window.SiteAuth) { wireSession(); return; }
    var waited = 0;
    var timer = setInterval(function () {
      if (window.SiteAuth) {
        clearInterval(timer);
        wireSession();
      } else if ((waited += 100) >= 4000) {
        clearInterval(timer);
        signedOut("Sign-in support did not load — reload the page.");
      }
    }, 100);
  })();
})();
