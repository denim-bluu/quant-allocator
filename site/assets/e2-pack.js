// site/assets/e2-pack.js
// Value->pixel only: positions IntervalStat bands within each data-domain group
// so the rail reflects the certified ci_lo/point/ci_hi. Reads verbatim numbers
// from data-* attributes; computes pixel positions, never a displayed number.
// (Same shape as s2-tearsheet.js positionBands.)
(function () {
  "use strict";

  function positionBands() {
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".pack-section .interval-stat")
    );
    var groups = {};
    stats.forEach(function (s) {
      var key = s.dataset.domain || "_";
      (groups[key] = groups[key] || []).push(s);
    });
    Object.keys(groups).forEach(function (key) {
      var members = groups[key];
      var los = members.map(function (s) { return parseFloat(s.dataset.lo); });
      var his = members.map(function (s) { return parseFloat(s.dataset.hi); });
      var min = Math.min.apply(null, los);
      var max = Math.max.apply(null, his);
      var span = max - min;
      if (span <= 0) {
        return;
      }
      members.forEach(function (s) {
        var lo = parseFloat(s.dataset.lo);
        var hi = parseFloat(s.dataset.hi);
        var point = parseFloat(s.dataset.point);
        var band = s.querySelector(".interval-stat__band");
        var mark = s.querySelector(".interval-stat__point");
        band.style.left = ((lo - min) / span) * 100 + "%";
        band.style.width = ((hi - lo) / span) * 100 + "%";
        mark.style.left = ((point - min) / span) * 100 + "%";
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", positionBands);
  } else {
    positionBands();
  }
})();
