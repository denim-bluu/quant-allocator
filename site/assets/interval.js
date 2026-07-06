(function () {
  "use strict";
  var STORAGE_KEY = "qa-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* localStorage unavailable (private mode / file://) — theme still applies */
    }
  }

  function init() {
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) {
      return;
    }
    toggle.addEventListener("click", function () {
      applyTheme(currentTheme() === "dark" ? "light" : "dark");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
