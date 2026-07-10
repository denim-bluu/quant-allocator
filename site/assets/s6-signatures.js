(function () {
  "use strict";

  // Value -> pixel only (mirrors m3-alarms.js): the AUC rail spans the domain
  // 0.0 -> 1.0. Read precomputed data attributes and place the band, the point,
  // and the two threshold marks (familywise significance floor + usability bar).
  // No computation, no fetch: the committed JSON is already the answer.
  var LO = 0.0, HI = 1.0;

  function pct(auc) {
    var f = (auc - LO) / (HI - LO);
    return Math.max(0, Math.min(1, f)) * 100;
  }

  function place(stat) {
    var point = parseFloat(stat.dataset.point);
    var lo = parseFloat(stat.dataset.lo);
    var hi = parseFloat(stat.dataset.hi);
    var floor = parseFloat(stat.dataset.floor);
    var bar = parseFloat(stat.dataset.bar);

    var band = stat.querySelector(".interval-stat__band");
    var dot = stat.querySelector(".interval-stat__point");
    var floorMark = stat.querySelector(".s6-rail__floor");
    var barMark = stat.querySelector(".s6-rail__bar");
    var nullMark = stat.querySelector(".s6-rail__null");

    if (band) {
      var left = pct(lo);
      band.style.left = left + "%";
      band.style.width = Math.max(0, pct(hi) - left) + "%";
    }
    if (dot) { dot.style.left = pct(point) + "%"; }
    if (floorMark) { floorMark.style.left = pct(floor) + "%"; }
    if (barMark) { barMark.style.left = pct(bar) + "%"; }
    if (nullMark) { nullMark.style.left = pct(0.5) + "%"; }
  }

  function init() {
    Array.prototype.slice
      .call(document.querySelectorAll('.interval-stat[data-domain="auc"]'))
      .forEach(place);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
