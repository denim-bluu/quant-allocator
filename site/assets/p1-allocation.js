(function () {
  "use strict";

  // Position the median anchor tick and the naive-optimizer marker along each band rail.
  // The rail spans [floor, ceil]; anchor and naive are mapped to a percentage across it.
  function placeMarkers(row) {
    var floor = parseFloat(row.dataset.floor);
    var ceil = parseFloat(row.dataset.ceil);
    var span = ceil - floor;
    var rail = row.querySelector(".p1-band__rail");
    if (!rail || !(span > 0)) { return; }
    var point = rail.querySelector(".interval-stat__point");
    var naive = rail.querySelector(".p1-naive");
    if (point) {
      point.style.left = clampPct((parseFloat(row.dataset.anchor) - floor) / span);
    }
    if (naive) {
      naive.style.left = clampPct((parseFloat(row.dataset.naive) - floor) / span);
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
        var ceil = parseFloat(btn.dataset.ceil);
        readout.textContent =
          "×" + parseFloat(btn.dataset.scale).toFixed(1) + " τ: band " +
          (floor * 100).toFixed(1) + "–" + (ceil * 100).toFixed(1) + "%";
      });
    });
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll(".p1-row")).forEach(function (row) {
      placeMarkers(row);
      wireDial(row);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
