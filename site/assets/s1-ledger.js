(function () {
  "use strict";

  // Map each IntervalStat's lo/point/hi onto a shared pixel domain so bands
  // are visually comparable. Reads verbatim numbers already rendered as data-*
  // attributes; computes only pixel positions, never a displayed number.
  function positionBands() {
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".ledger .interval-stat")
    );
    if (!stats.length) {
      return;
    }
    var los = stats.map(function (s) { return parseFloat(s.dataset.lo); });
    var his = stats.map(function (s) { return parseFloat(s.dataset.hi); });
    var min = Math.min.apply(null, los);
    var max = Math.max.apply(null, his);
    var span = max - min;
    if (span <= 0) {
      return;
    }
    stats.forEach(function (s) {
      var lo = parseFloat(s.dataset.lo);
      var hi = parseFloat(s.dataset.hi);
      var point = parseFloat(s.dataset.point);
      var band = s.querySelector(".interval-stat__band");
      var mark = s.querySelector(".interval-stat__point");
      band.style.left = ((lo - min) / span) * 100 + "%";
      band.style.width = ((hi - lo) / span) * 100 + "%";
      mark.style.left = ((point - min) / span) * 100 + "%";
    });
  }

  // Reorder ledger rows between OLS-rank and posterior-rank order (the reshuffle).
  function initSort() {
    var toggle = document.querySelector("[data-sort-toggle]");
    var ledger = document.querySelector("[data-ledger]");
    if (!toggle || !ledger) {
      return;
    }
    toggle.addEventListener("click", function () {
      var order = toggle.dataset.order === "ols" ? "posterior" : "ols";
      toggle.dataset.order = order;
      toggle.textContent =
        "Order by: " + (order === "ols" ? "OLS rank" : "posterior rank");
      var attr = order === "ols" ? "olsRank" : "posteriorRank";
      var rows = Array.prototype.slice.call(ledger.querySelectorAll(".ledger-row"));
      rows.sort(function (a, b) {
        return parseInt(a.dataset[attr], 10) - parseInt(b.dataset[attr], 10);
      });
      rows.forEach(function (row) { ledger.appendChild(row); });
    });
  }

  function init() {
    positionBands();
    initSort();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
