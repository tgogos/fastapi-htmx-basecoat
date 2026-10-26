/**
 * Small vanilla island for the HTMX UI.
 * - Dialog confirm before destructive HTMX deletes
 * - Basecoat toasts (HX-Trigger: showToast)
 * - Dismiss flash messages
 * - Send CSRF header on HTMX requests when meta csrf-token is present
 * - Show password checkbox on a new-password pair
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

  function confirmPhraseEl() {
    return document.getElementById("confirm-dialog-phrase");
  }

  function confirmOkEl() {
    return document.getElementById("confirm-dialog-ok");
  }

  function syncConfirmPhrase() {
    var phrase = confirmPhraseEl();
    var ok = confirmOkEl();
    if (!phrase || !ok) {
      return;
    }
    ok.disabled = phrase.value !== "DELETE";
  }

  function openConfirm(el) {
    var dialog = confirmDialog();
    var messageEl = confirmMessageEl();
    var phrase = confirmPhraseEl();
    if (!dialog || !messageEl || typeof dialog.showModal !== "function") {
      return false;
    }
    pendingConfirmEl = el;
    messageEl.textContent = el.getAttribute("data-confirm") || "Are you sure?";
    if (phrase) {
      phrase.value = "";
    }
    syncConfirmPhrase();
    dialog.showModal();
    if (phrase) {
      phrase.focus();
    }
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
      var ok = confirmOkEl();
      if (ok && ok.disabled) {
        return;
      }
      var el = pendingConfirmEl;
      closeConfirm();
      if (el && window.htmx) {
        htmx.trigger(el, "confirmed-delete");
      }
    }
  });

  var confirmRoot = confirmDialog();
  if (confirmRoot) {
    confirmRoot.addEventListener("click", function (event) {
      if (event.target === confirmRoot) {
        closeConfirm();
      }
    });
  }

  var confirmPhrase = confirmPhraseEl();
  if (confirmPhrase) {
    confirmPhrase.addEventListener("input", syncConfirmPhrase);
    confirmPhrase.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") {
        return;
      }
      var ok = confirmOkEl();
      if (ok && !ok.disabled) {
        ok.click();
      }
    });
  }

  document.addEventListener("change", function (event) {
    var box = event.target;
    if (!box || !box.matches || !box.matches("[data-show-password-toggle]")) {
      return;
    }
    var type = box.checked ? "text" : "password";
    document.querySelectorAll("[data-show-password]").forEach(function (input) {
      if (input.getAttribute("data-show-password") === box.id) {
        input.type = type;
      }
    });
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

  function syncStaffReturn() {
    var link = document.querySelector("[data-staff-return]");
    if (!link) {
      return;
    }
    var back = window.location.pathname + window.location.search;
    link.setAttribute("href", "/ui/admin/users/new?return_to=" + encodeURIComponent(back));
  }

  function syncListFiltersFromUrl() {
    var params = new URLSearchParams(window.location.search);
    document.querySelectorAll("form[data-list-filters] input[type='hidden']").forEach(function (input) {
      var name = input.getAttribute("name");
      if (!name || name === "page" || name === "csrf_token" || input.hasAttribute("data-table-facet") || !params.has(name)) {
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

  function syncTableFacetsFromUrl() {
    var form = document.querySelector("form[data-table-filters]");
    if (!form) {
      return;
    }
    var params = new URLSearchParams(window.location.search);
    form.querySelectorAll("[data-table-facet]").forEach(function (input) {
      input.remove();
    });
    ["category", "available", "role"].forEach(function (name) {
      params.getAll(name).forEach(function (value) {
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        input.setAttribute("data-table-facet", "");
        form.appendChild(input);
      });
    });
  }

  function syncTableSelection() {
    var form = document.getElementById("books-table-select");
    if (!form) {
      return;
    }
    var rows = form.querySelectorAll("[data-select-row]");
    var checked = form.querySelectorAll("[data-select-row]:checked");
    var all = form.querySelector("[data-select-page]");
    var bar = form.querySelector("[data-table-selection]");
    var countEl = form.querySelector("[data-selection-count]");
    var remove = form.querySelector("[data-selection-delete]");
    var count = checked.length;
    if (bar) {
      bar.hidden = count === 0;
    }
    if (countEl) {
      countEl.textContent = String(count);
    }
    if (all) {
      all.checked = rows.length > 0 && count === rows.length;
      all.indeterminate = count > 0 && count < rows.length;
    }
    if (remove) {
      remove.disabled = count === 0;
      var noun = count === 1 ? "book" : "books";
      remove.setAttribute(
        "data-confirm",
        "Delete " + count + " selected " + noun + "? This cannot be undone."
      );
    }
  }

  document.body.addEventListener("change", function (event) {
    var el = event.target;
    if (!el || !el.closest || !el.closest("#books-table-select")) {
      return;
    }
    if (el.matches("[data-select-page]")) {
      var form = document.getElementById("books-table-select");
      form.querySelectorAll("[data-select-row]").forEach(function (box) {
        box.checked = el.checked;
      });
    }
    if (el.matches("[data-select-row], [data-select-page]")) {
      syncTableSelection();
    }
  });

  document.body.addEventListener("click", function (event) {
    var clear = event.target.closest("[data-selection-clear]");
    if (!clear) {
      return;
    }
    var form = document.getElementById("books-table-select");
    if (!form) {
      return;
    }
    form.querySelectorAll("[data-select-row], [data-select-page]").forEach(function (box) {
      box.checked = false;
      box.indeterminate = false;
    });
    syncTableSelection();
  });

  function placeRowMenu(pop) {
    var menu = pop.parentElement;
    var trigger = menu && menu.querySelector(":scope > button");
    if (!trigger) {
      return;
    }
    var rect = trigger.getBoundingClientRect();
    var margin = 4;
    pop.style.position = "fixed";
    pop.style.margin = "0";
    pop.style.translate = "none";
    pop.style.inset = "auto";
    pop.style.minWidth = "max-content";
    pop.style.zIndex = "50";
    var top = rect.bottom + margin;
    var height = pop.offsetHeight;
    if (top + height > window.innerHeight && rect.top - margin - height > 0) {
      top = rect.top - margin - height;
    }
    pop.style.top = Math.round(top) + "px";
    pop.style.left = "auto";
    pop.style.right = Math.max(8, Math.round(window.innerWidth - rect.right)) + "px";
  }

  function clearRowMenu(pop) {
    ["position", "margin", "translate", "inset", "top", "left", "right", "minWidth", "zIndex"].forEach(function (name) {
      pop.style[name] = "";
    });
  }

  function syncRowMenus() {
    document.querySelectorAll(".table-actions [data-popover]").forEach(function (pop) {
      if (pop.getAttribute("aria-hidden") === "false") {
        placeRowMenu(pop);
      } else {
        clearRowMenu(pop);
      }
    });
  }

  function scheduleRowMenus() {
    window.setTimeout(syncRowMenus, 0);
  }

  document.addEventListener("click", scheduleRowMenus);
  document.addEventListener("keydown", scheduleRowMenus);
  document.addEventListener("scroll", syncRowMenus, true);
  window.addEventListener("resize", syncRowMenus);

  document.addEventListener("htmx:after:history:push", function () {
    syncListFiltersFromUrl();
    syncTableFacetsFromUrl();
    syncStaffReturn();
  });
  document.body.addEventListener("htmx:after:settle", function () {
    initBasecoat(false);
    syncTableSelection();
    syncTableFacetsFromUrl();
  });
  document.body.addEventListener("htmx:after:history:update", function () {
    initBasecoat(true);
  });
  syncListFiltersFromUrl();
  syncTableFacetsFromUrl();
  syncStaffReturn();

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

  function showPendingToast() {
    var pendingToast = document.getElementById("pending-toast");
    var region = document.getElementById("toaster");
    if (!pendingToast || !region) {
      return true;
    }
    if (typeof region.toast !== "function") {
      initBasecoat(false);
    }
    if (typeof region.toast !== "function") {
      return false;
    }
    showToast(pendingToast.getAttribute("data-message"), pendingToast.getAttribute("data-level"));
    pendingToast.remove();
    return true;
  }

  function watchPendingToast(attempt) {
    if (showPendingToast() || attempt > 20) {
      return;
    }
    setTimeout(function () {
      watchPendingToast(attempt + 1);
    }, 50);
  }

  // Basecoat attaches toaster.toast on DOMContentLoaded, after this script.
  window.addEventListener("load", function () {
    watchPendingToast(0);
  });
  if (document.readyState === "complete") {
    watchPendingToast(0);
  }
})();
