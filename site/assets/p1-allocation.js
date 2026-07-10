(function () {
  "use strict";

  function pct(value) {
    return (value * 100).toFixed(1) + "%";
  }

  // Use one domain per manager across every committed skepticism state and the naive marker.
  // State changes therefore alter geometry without silently rescaling the axis.
  function positionState(row) {
    var floor = parseFloat(row.dataset.floor);
    var anchor = parseFloat(row.dataset.anchor);
    var ceil = parseFloat(row.dataset.ceil);
    var domainMin = parseFloat(row.dataset.domainMin);
    var domainMax = parseFloat(row.dataset.domainMax);
    var span = domainMax - domainMin;
    var rail = row.querySelector(".p1-band__rail");
    if (!rail || !(span > 0)) { return; }
    var band = rail.querySelector(".interval-stat__band");
    var point = rail.querySelector(".interval-stat__point");
    var naive = rail.querySelector(".p1-naive");
    if (band) {
      band.style.left = clampPct((floor - domainMin) / span);
      band.style.width = clampPct((ceil - floor) / span);
    }
    if (point) {
      point.style.left = clampPct((anchor - domainMin) / span);
      point.title = "median anchor " + pct(anchor);
    }
    if (naive) {
      naive.style.left = clampPct((parseFloat(row.dataset.naive) - domainMin) / span);
    }
  }

  function clampPct(frac) {
    return (Math.max(0, Math.min(1, frac)) * 100).toFixed(2) + "%";
  }

  // Skepticism dial: snap the readout to a PRECOMPUTED τ-scale state (x2/M3 idiom). No computation.
  function wireDial(row) {
    var dial = row.querySelector(".p1-dial");
    if (!dial) { return; }
    var readout = dial.querySelector("[data-dial-readout]");
    var btns = Array.prototype.slice.call(dial.querySelectorAll(".p1-dial__btn"));
    btns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        btns.forEach(function (b) {
          b.classList.remove("p1-dial__btn--active");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("p1-dial__btn--active");
        btn.setAttribute("aria-pressed", "true");
        var floor = parseFloat(btn.dataset.floor);
        var anchor = parseFloat(btn.dataset.anchor);
        var ceil = parseFloat(btn.dataset.ceil);
        row.dataset.floor = btn.dataset.floor;
        row.dataset.anchor = btn.dataset.anchor;
        row.dataset.ceil = btn.dataset.ceil;
        var stat = row.querySelector(".interval-stat");
        stat.dataset.lo = btn.dataset.floor;
        stat.dataset.point = btn.dataset.anchor;
        stat.dataset.hi = btn.dataset.ceil;
        stat.querySelector(".interval-stat__value").textContent = pct(floor) + "–" + pct(ceil);
        stat.querySelector(".interval-stat__range").textContent =
          "10th–90th percentile of posterior-draw weights · anchor " + pct(anchor) +
          " · point optimizer " + pct(parseFloat(row.dataset.naive));
        stat.setAttribute(
          "aria-label",
          "Advisory band " + pct(floor) + " to " + pct(ceil) + ", anchor " + pct(anchor)
        );
        readout.textContent =
          "×" + parseFloat(btn.dataset.scale).toFixed(1) + " τ: band " + pct(floor) + "–" + pct(ceil);
        positionState(row);
      });
    });
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll(".p1-row")).forEach(function (row) {
      positionState(row);
      wireDial(row);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
