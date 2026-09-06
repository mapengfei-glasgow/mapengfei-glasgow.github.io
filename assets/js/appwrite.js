/* 生词本 via AppWrite —— 静态站集成（无构建步骤）。
 *
 * 后端（AppWrite Cloud，fra 区域）已配置完成（2026-09-06）：
 *   1. Authentication → Methods：Email & Password 已开启（注册/登录 E2E 验证通过）。
 *      匿名登录未启用：该部署的 guests 角色缺少 account scope，服务端无配置入口，
 *      故本站只提供邮箱注册/登录。
 *      注意：AppWrite 2.0 自助注册必须由客户端指定 userId（即用户名），
 *      注册表单里让用户输入 1–36 位的用户名作为 userId（服务端实测接受 1 位）。
 *   2. Database `site` / Collection `vocab`，属性：
 *        slug    String  128  (episode slug)
 *        idx     Integer          (句子序号，0 起)
 *        show    String  128  (节目名)
 *        title   String  256  (集标题)
 *        text    String  4096 (句子原文)
 *        explain String  32768 (英文解释，可空)
 *      索引 idx_slug (slug, idx)；documentSecurity=true；集合级权限 create("users")，
 *      文档创建后服务端自动赋 read/update/delete("user:<创建者>")（2.0 无 owner 角色）。
 *   3. Web platform 已建（hostname=mapengfei-glasgow.github.io）；Origin 已验证通过。
 *
 * 注意 AppWrite 2.0 与 1.x 的关键差异（本站 SDK 26.2.0）：
 *   - 自助注册必须指定 userId（用户名，≤36 位 [a-zA-Z0-9._-]，首字符字母/数字）
 *   - 注册不自动登录，需再调 /account/sessions/email
 *   - 文档 API 路径 /databases/{db}/collections/{coll}/documents；create body 数据在 data 内
 *   - listDocuments(db, coll, queries, transactionId, total, ttl)，limit 用 Query.limit()
 *   - 会话 fallback：响应头 x-fallback-cookies（JSON）→ localStorage → X-Fallback-Cookies 头
 */
(function () {
  "use strict";

  var CONFIG = {
    endpoint: "https://fra.cloud.appwrite.io/v1",
    projectId: "6a9d0e7c002b1fabe1e9",
    db: "site",
    collection: "vocab"
  };

  if (!CONFIG.projectId || CONFIG.projectId === "YOUR_PROJECT_ID") return;
  document.documentElement.dataset.vocab = "on";

  var SDK_URL = "https://cdn.jsdelivr.net/npm/appwrite@26.2.0/dist/iife/sdk.js";

  var account = null, dbSvc = null, user = null;
  var sdkPromise = null, sessionPromise = null, docCache = null;
  var modal = null, mode = "login";

  /* ---------- SDK 懒加载（只在需要时才拉 469KB 的 SDK） ---------- */

  function loadSDK() {
    if (window.Appwrite && window.Appwrite.Client) return Promise.resolve(window.Appwrite);
    if (!sdkPromise) {
      sdkPromise = new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = SDK_URL;
        s.async = true;
        s.onload = function () { resolve(window.Appwrite); };
        s.onerror = function () { sdkPromise = null; reject(new Error("AppWrite SDK 加载失败")); };
        document.head.appendChild(s);
      });
    }
    return sdkPromise;
  }

  function initClient() {
    // 注意：2.0 的 Client 构造函数不接受参数（1.x 的 new Client({...}) 会被静默忽略，
    // 请求会打到默认的 cloud.appwrite.io 美国区），必须用 setter 链配置
    var AW = window.Appwrite;
    var client = new AW.Client().setEndpoint(CONFIG.endpoint).setProject(CONFIG.projectId);
    account = new AW.Account(client);
    dbSvc = new AW.Databases(client);
  }

  // 恢复/确认会话（cookie 或 localStorage fallback 里可能有上次登录的 session）
  function ensureSession() {
    if (!sessionPromise) {
      sessionPromise = loadSDK().then(function () {
        initClient();
        return account.get();
      }).then(function (u) {
        user = u; updateChip(); return true;
      }).catch(function () {
        user = null; updateChip(); return false;
      });
    }
    return sessionPromise;
  }

  function loggedIn() { return !!user; }

  /* ---------- 头部按钮 ---------- */

  function chip() { return document.getElementById("auth-chip"); }

  function updateChip() {
    var c = chip();
    if (c) {
      c.hidden = false;
      if (user) {
        c.textContent = "📖 " + (user.name || user.email || "生词本");
        c.title = "我的生词本（" + (user.email || user.name) + "）";
        c.dataset.state = "in";
      } else {
        c.textContent = "登录";
        c.title = "登录 / 注册，收藏的句子可以跨设备同步";
        c.dataset.state = "out";
      }
    }
    fireAuth();
  }

  function fireAuth() {
    document.dispatchEvent(new CustomEvent("ds-auth", { detail: { user: user } }));
  }

  /* ---------- 登录弹窗 ---------- */

  function openModal(m) {
    if (!modal) return;
    setTab(m || "login");
    modal.hidden = false;
    document.body.classList.add("modal-open");
    var f = modal.querySelector(mode === "signup" ? "#auth-uid" : "#auth-email");
    if (f) f.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
  }

  function setTab(m) {
    mode = m;
    modal.querySelectorAll(".auth-tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.mode === m);
    });
    var name = modal.querySelector("#auth-name");
    if (name) name.hidden = (m !== "signup");
    var uid = modal.querySelector("#auth-uid");
    if (uid) uid.hidden = (m !== "signup");
    var pw = modal.querySelector("#auth-password");
    if (pw) pw.autocomplete = (m === "signup" ? "new-password" : "current-password");
    var sub = modal.querySelector(".auth-submit");
    if (sub) sub.textContent = (m === "signup" ? "注册并登录" : "登录");
    var title = modal.querySelector("#auth-title");
    if (title) title.textContent = (m === "signup" ? "注册账号" : "登录");
    var err = modal.querySelector("#auth-err");
    if (err) err.textContent = "";
  }

  function fail(msg) {
    var err = modal && modal.querySelector("#auth-err");
    if (err) err.textContent = msg;
  }

  var UID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$/;

  function errMsg(e) {
    var m = (e && e.message) || String(e);
    var t = (e && e.type) || "";
    if (t === "user_already_exists" || (/userid|user.*id/i.test(m) && /exist|already/i.test(m))) return "这个用户名已经被占用了，换一个试试。";
    if (/duplicate|already (exists|used)|user.exists/i.test(m)) return "这个邮箱已经注册过了，切到「登录」再试。";
    if (t === "user_invalid_credentials" || /password|credentials/i.test(m)) return "邮箱或密码不对。";
    if (/valid.*email|email.*valid/i.test(m)) return "邮箱格式好像不对。";
    return m;
  }

  function finishAuth() {
    return account.get().then(function (u) {
      user = u;
      closeModal();
      updateChip();
    });
  }

  function wireModal() {
    modal = document.getElementById("auth-modal");
    if (!modal || modal.dataset.wired === "1") return;
    modal.dataset.wired = "1";
    modal.querySelector("#auth-close").addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    });
    modal.querySelectorAll(".auth-tab").forEach(function (b) {
      b.addEventListener("click", function () { setTab(b.dataset.mode); });
    });

    modal.querySelector("#auth-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var email = modal.querySelector("#auth-email").value.trim();
      var password = modal.querySelector("#auth-password").value;
      var name = (modal.querySelector("#auth-name").value || "").trim();
      var uidEl = modal.querySelector("#auth-uid");
      var uid = uidEl ? uidEl.value.trim() : "";
      if (mode === "signup" && !UID_RE.test(uid)) {
        fail("用户名：1–36 位，以字母或数字开头，可用字母、数字、下划线、中划线和点。");
        return;
      }
      var btn = modal.querySelector(".auth-submit");
      btn.disabled = true;
      btn.textContent = "请稍候…";
      ensureSession().then(function () {
        if (mode === "login") {
          return account.createEmailPasswordSession(email, password).then(finishAuth);
        }
        // AppWrite 2.0：自助注册必须由客户端指定 userId（用户名）
        return account.create(uid, email, password, name || email.split("@")[0])
          .then(function () {
            // 注册后确保拿到会话（一般注册即登录，这里兜底再登一次）
            return account.get().catch(function () {
              return account.createEmailPasswordSession(email, password);
            });
          }).then(finishAuth);
      }).catch(function (err) {
        // 注意：setTab 会清空 #auth-err，所以「切 tab」必须发生在 fail 之前，
        // 且之后绝不能再调 setTab，否则错误提示会被吞掉（表现为"点了没反应"）
        if (mode === "signup" && /duplicate|already (exists|used)|user.exists|user_already_exists/i.test(((err && err.message) || "") + " " + ((err && err.type) || ""))) {
          setTab("login");
          fail("这个邮箱已经注册过了，直接登录吧。");
        } else {
          fail(errMsg(err));
        }
      }).then(function () {
        btn.disabled = false;
        btn.textContent = (mode === "signup" ? "注册并登录" : "登录");
      });
    });

  }

  /* ---------- 生词本数据 ---------- */

  function loadDocs() {
    if (docCache) return Promise.resolve(docCache);
    docCache = {};
    return loadSDK().then(function () {
      initClient();
      // 2.0 签名：listDocuments(databaseId, collectionId, queries, transactionId, total, ttl)
      return dbSvc.listDocuments(CONFIG.db, CONFIG.collection, [window.Appwrite.Query.limit(250)]);
    }).then(function (res) {
      (res.documents || []).forEach(function (d) {
        docCache[d.slug + ":" + d.idx] = d;
      });
      return docCache;
    }).catch(function (e) {
      console.warn("vocab load failed:", (e && e.message) || e);
      return docCache;
    });
  }

  /* ---------- 集页面：☆ 收藏按钮 ---------- */

  function slug() {
    var art = document.querySelector(".episode");
    return art ? art.dataset.slug : null;
  }

  function makeStar(li) {
    var btn = li.querySelector(".star");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.className = "star";
      btn.textContent = "☆";
      btn.setAttribute("aria-label", "收藏这句");
      li.appendChild(btn);
    }
    return btn;
  }

  function hydrateStars() {
    var art = document.querySelector(".episode");
    if (!art || !art.dataset.slug) return;
    var s = art.dataset.slug;
    loadDocs().then(function () {
      art.querySelectorAll(".sentence").forEach(function (li) {
        var btn = li.querySelector(".star");
        if (btn && docCache[s + ":" + li.dataset.i]) {
          btn.classList.add("on");
          btn.textContent = "★";
        }
      });
    });
  }

  function toggleStar(li, btn) {
    var s = slug();
    if (!s) return;
    if (!loggedIn()) { openModal("login"); return; }
    var key = s + ":" + li.dataset.i;
    var textEl = li.querySelector(".text");
    var exEl = li.querySelector(".explain");
    btn.disabled = true;
    loadSDK().then(function () {
      initClient();
      var d = docCache && docCache[key];
      if (d) return dbSvc.deleteDocument(CONFIG.db, CONFIG.collection, d.$id);
      // 2.0：不传 permissions 时服务端自动给创建者加 read/update/delete("user:<uid>")
      // （集合级 create("users") + documentSecurity=true 保证每人只能动自己的句子）
      return dbSvc.createDocument(CONFIG.db, CONFIG.collection, window.Appwrite.ID.unique(), {
        slug: s,
        idx: parseInt(li.dataset.i, 10),
        show: (li.closest(".episode").dataset.show || ""),
        title: (li.closest(".episode").dataset.title || ""),
        text: textEl ? textEl.textContent.trim() : "",
        explain: exEl ? exEl.textContent.trim() : ""
      });
    }).then(function (res) {
      var nowOn = !(docCache && docCache[key]);
      if (!docCache) docCache = {};
      if (nowOn && res && res.$id) docCache[key] = res;
      else delete docCache[key];
      btn.classList.toggle("on", nowOn);
      btn.textContent = nowOn ? "★" : "☆";
    }).catch(function (err) {
      console.warn("star failed:", (err && err.message) || err);
      btn.title = "⚠ 收藏失败: " + ((err && err.message) || err);
      setTimeout(function () { btn.title = ""; }, 4000);
    }).then(function () {
      btn.disabled = false;
    });
  }

  function wireStars() {
    var art = document.querySelector(".episode");
    if (!art || !art.dataset.slug) return;
    var ol = art.querySelector("ol.sentences");
    if (!ol || ol.dataset.wired === "1") return;
    ol.dataset.wired = "1";
    art.querySelectorAll(".sentence").forEach(makeStar);
    ol.addEventListener("click", function (e) {
      var t = e.target;
      var btn = t && t.closest ? t.closest(".star") : null;
      if (!btn) return;
      e.stopPropagation();
      var li = btn.closest(".sentence");
      toggleStar(li, btn);
    });
    document.addEventListener("ds-auth", function (ev) {
      if (ev.detail && ev.detail.user) hydrateStars();
    });
  }

  /* ---------- /words/ 页 ---------- */

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function wireVocabPage() {
    var box = document.getElementById("vocab-list");
    if (!box || box.dataset.wired === "1") return;
    box.dataset.wired = "1";
    var empty = document.getElementById("vocab-empty");
    var logout = document.getElementById("vocab-logout");

    function render() {
      if (logout) logout.hidden = !user;
      if (!user) {
        box.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      loadDocs().then(function () {
        var docs = Object.keys(docCache).map(function (k) { return docCache[k]; })
          .sort(function (a, b) {
            return String(b.$createdAt || "").localeCompare(String(a.$createdAt || ""));
          });
        if (!docs.length) {
          box.innerHTML = "";
          if (empty) empty.hidden = false;
          return;
        }
        box.innerHTML = docs.map(function (d) {
          return '<li class="vocab-item">' +
            '<div class="vocab-head">' +
              '<a class="vocab-ep" href="/episodes/' + esc(d.slug) + '/">' +
                esc(d.show || "") + " · " + esc(d.title || d.slug) +
              '</a>' +
              '<button class="vocab-del" data-id="' + esc(d.$id) + '" title="删除">✕</button>' +
            '</div>' +
            '<p class="vocab-text">' + esc(d.text) + '</p>' +
            (d.explain ? '<p class="vocab-explain">💡 ' + esc(d.explain) + '</p>' : "") +
            '</li>';
        }).join("");
        box.querySelectorAll(".vocab-del").forEach(function (b) {
          b.addEventListener("click", function () {
            b.disabled = true;
            dbSvc.deleteDocument(CONFIG.db, CONFIG.collection, b.dataset.id)
              .then(function () {
                var k;
                for (k in docCache) if (docCache[k].$id === b.dataset.id) delete docCache[k];
                render();
              })
              .catch(function (err) { console.warn("delete failed:", (err && err.message) || err); })
              .then(function () { b.disabled = false; });
          });
        });
      });
    }

    if (logout) logout.addEventListener("click", function () {
      if (!account) return;
      account.deleteSessions().then(function () {
        user = null;
        docCache = null;
        updateChip();
        render();
      }).catch(function (err) { console.warn("logout failed:", (err && err.message) || err); });
    });

    render();
    document.addEventListener("ds-auth", render);
  }

  /* ---------- 启动 ---------- */

  function init() {
    wireModal();
    wireStars();
    wireVocabPage();

    var c = chip();
    if (c && c.dataset.wired !== "1") {
      c.dataset.wired = "1";
      c.addEventListener("click", function () {
        if (loggedIn()) {
          // 走 Turbo 跳转（SPA 式，底部播放条不中断）；Turbo 不可用时退回硬跳转
          if (window.Turbo && window.Turbo.visit) window.Turbo.visit("/words/");
          else location.href = "/words/";
          return;
        }
        ensureSession().then(function (ok) {
          if (!ok) openModal("login");
        });
      });
    }

    var hint = null;
    try { hint = localStorage.getItem("cookieFallback"); } catch (e) {}
    if (hint) {
      // 可能有上次的登录，静默恢复。ensureSession 的 promise 有缓存，
      // 但 SPA 跳转后 chip 是全新节点，每次页面出现都要重新刷一遍它
      ensureSession().then(function () { updateChip(); });
    } else {
      updateChip();    // 没有会话痕迹 → 直接显示"登录"
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
  // Turbo：每次页面出现（含 SPA 跳转）后 <body> 已换成新节点，重新接线。
  // 本文件带 data-turbo-eval="false" 不会重复执行，监听器挂 document 上长期有效；
  // 各 wire* 函数用 data-wired 标记防止同一页代内重复绑。
  document.addEventListener("turbo:load", init);
})();
