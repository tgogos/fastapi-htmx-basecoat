/**
 * Small vanilla island for the HTMX UI.
 * - Dialog confirm before destructive HTMX deletes
 * - Basecoat toasts (HX-Trigger: showToast)
 * - Dismiss flash messages
 * - Send CSRF header on HTMX requests when meta csrf-token is present
 */
(function () {
  "use strict";

  var pendingConfirmEl = null;

  function confirmDialog() {
    return document.getElementById("confirm-dialog");
  }

  function confirmMessageEl() {
    return document.getElementById("confirm-dialog-message");
  }

  function openConfirm(el) {
    var dialog = confirmDialog();
    var messageEl = confirmMessageEl();
    if (!dialog || !messageEl || typeof dialog.showModal !== "function") {
      return false;
    }
    pendingConfirmEl = el;
    messageEl.textContent = el.getAttribute("data-confirm") || "Are you sure?";
    dialog.showModal();
    return true;
  }

  function closeConfirm() {
    var dialog = confirmDialog();
    pendingConfirmEl = null;
    if (dialog && dialog.open) {
      dialog.close();
    }
  }

  function showToast(message, level) {
    var region = document.getElementById("toaster");
    if (!region || !message || typeof region.toast !== "function") {
      return;
    }
    region.toast({
      category: level === "error" ? "error" : "success",
      description: message,
    });
  }

  function initBasecoat(force) {
    if (window.basecoat && typeof window.basecoat.initAll === "function") {
      window.basecoat.initAll(force ? { force: true } : undefined);
    }
  }

  document.body.addEventListener("click", function (event) {
    var dismiss = event.target.closest(".flash-dismiss");
    if (dismiss) {
      var flash = dismiss.closest(".flash, .alert");
      if (flash) {
        flash.remove();
      }
      return;
    }

    var deleteBtn = event.target.closest(".js-confirm-delete");
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();
      if (!openConfirm(deleteBtn)) {
        var message = deleteBtn.getAttribute("data-confirm") || "Are you sure?";
        if (window.confirm(message)) {
          htmx.trigger(deleteBtn, "confirmed-delete");
        }
      }
    }
  }, true);

  document.body.addEventListener("click", function (event) {
    if (event.target.closest("[data-confirm-cancel]")) {
      closeConfirm();
      return;
    }
    if (event.target.closest("[data-confirm-ok]")) {
      var el = pendingConfirmEl;
      closeConfirm();
      if (el && window.htmx) {
        htmx.trigger(el, "confirmed-delete");
      }
    }
  });

  document.body.addEventListener("showToast", function (event) {
    var detail = event.detail || {};
    showToast(detail.message, detail.level);
  });

  document.body.addEventListener("htmx:config:request", function (event) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    var ctx = event.detail && event.detail.ctx;
    var headers = ctx && ctx.request && ctx.request.headers;
    if (!meta || !headers) {
      return;
    }
    var token = meta.getAttribute("content");
    if (token && !headers["X-CSRF-Token"]) {
      headers["X-CSRF-Token"] = token;
    }
  });

  function syncListFiltersFromUrl() {
    var params = new URLSearchParams(window.location.search);
    document.querySelectorAll("form[data-list-filters] input[type='hidden']").forEach(function (input) {
      var name = input.getAttribute("name");
      if (!name || name === "page" || name === "csrf_token" || !params.has(name)) {
        return;
      }
      input.value = params.get(name);
    });
  }

  document.body.addEventListener("change", function (event) {
    var el = event.target;
    if (!el || !el.matches || !el.matches("[data-list-page-size]")) {
      return;
    }
    var opt = el.selectedOptions && el.selectedOptions[0];
    var url = opt && opt.getAttribute("data-url");
    if (!url || !window.htmx) {
      return;
    }
    document.querySelectorAll("form[data-list-filters] input[type='hidden'][name='size']").forEach(function (input) {
      input.value = el.value;
    });
    htmx.ajax("GET", url, {
      source: el,
      target: el.getAttribute("data-panel-target"),
      swap: "innerHTML",
      push: url,
    });
  });

  document.body.addEventListener("htmx:after:history:push", syncListFiltersFromUrl);
  document.body.addEventListener("htmx:after:settle", function () {
    initBasecoat(false);
  });
  document.body.addEventListener("htmx:after:history:update", function () {
    initBasecoat(true);
  });
  syncListFiltersFromUrl();

  document.addEventListener("basecoat:themechange", function () {
    document.documentElement.dispatchEvent(new CustomEvent("themechange"));
  });

  var colorThemes = ["default", "blue", "teal", "grey"];

  function syncColorMenu() {
    var current = document.documentElement.getAttribute("data-color") || "default";
    document.querySelectorAll("[data-color-value]").forEach(function (item) {
      item.setAttribute("aria-checked", item.getAttribute("data-color-value") === current ? "true" : "false");
    });
  }

  document.addEventListener("click", function (event) {
    var item = event.target.closest("[data-color-value]");
    if (!item) {
      return;
    }
    var next = item.getAttribute("data-color-value");
    if (colorThemes.indexOf(next) === -1) {
      return;
    }
    if (next === "default") {
      document.documentElement.removeAttribute("data-color");
    } else {
      document.documentElement.setAttribute("data-color", next);
    }
    try {
      localStorage.setItem("colorTheme", next);
    } catch (_) {}
    syncColorMenu();
    document.documentElement.dispatchEvent(new CustomEvent("themechange"));
  });
  syncColorMenu();

  var pendingToast = document.getElementById("pending-toast");
  if (pendingToast) {
    showToast(pendingToast.getAttribute("data-message"), pendingToast.getAttribute("data-level"));
    pendingToast.remove();
  }
})();
