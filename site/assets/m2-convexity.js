(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function readCardData() {
    var el = document.getElementById("card-data");
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  // Position IntervalStat bands on a shared pixel domain per data-domain group.
  // Reads verbatim numbers from data-* attributes; computes only pixel positions.
  function positionBands() {
    var stats = Array.prototype.slice.call(document.querySelectorAll(".interval-stat"));
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
      if (!(span > 0)) { return; }
      members.forEach(function (s) {
        var lo = parseFloat(s.dataset.lo), hi = parseFloat(s.dataset.hi), point = parseFloat(s.dataset.point);
        s.querySelector(".interval-stat__band").style.left = ((lo - min) / span) * 100 + "%";
        s.querySelector(".interval-stat__band").style.width = ((hi - lo) / span) * 100 + "%";
        s.querySelector(".interval-stat__point").style.left = ((point - min) / span) * 100 + "%";
      });
    });
  }

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) { el.setAttribute("class", cls); }
    return el;
  }

  // Paired monthly-return strip: honest vs overlaid, bars from a midline. Draws
  // both managers' full monthly series so the stress months stand out visually.
  function drawStressStrip(honest, overlaid) {
    var svg = document.querySelector(".m2-stress-strip");
    if (!svg || !honest || !overlaid || !honest.length) { return; }
    var W = 100, H = 30, mid = H / 2;
    var all = honest.concat(overlaid);
    var maxAbs = all.reduce(function (m, v) { return Math.max(m, Math.abs(v)); }, 0) || 1;
    var bw = W / honest.length;
    function bars(series, cls, offset) {
      series.forEach(function (v, i) {
        var h = (Math.abs(v) / maxAbs) * (H / 2);
        var rect = makeEl("rect", cls);
        rect.setAttribute("x", String(i * bw + offset));
        rect.setAttribute("y", String(v >= 0 ? mid - h : mid));
        rect.setAttribute("width", String(bw * 0.4));
        rect.setAttribute("height", String(h || 0.1));
        svg.appendChild(rect);
      });
    }
    bars(honest, "m2-bar-honest", 0);
    bars(overlaid, "m2-bar-overlaid", bw * 0.45);
  }

  function init() {
    positionBands();
    var data = readCardData();
    if (data) {
      drawStressStrip(data.managers.honest.monthly_returns, data.managers.overlaid.monthly_returns);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
