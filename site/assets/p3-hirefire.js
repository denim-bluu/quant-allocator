/* site/assets/p3-hirefire.js — value->pixel only. Positions the posterior
   IntervalStat band on a domain that includes zero (so "straddles zero" is
   visible) and draws the fired-vs-replacement forward-path SVG. */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function readCardData() {
    var el = document.getElementById("card-data");
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  function positionPosterior() {
    var s = document.querySelector('.interval-stat[data-domain="valueadd"]');
    if (!s) { return; }
    var lo = parseFloat(s.dataset.lo);
    var hi = parseFloat(s.dataset.hi);
    var point = parseFloat(s.dataset.point);
    var zero = parseFloat(s.dataset.zero || "0");
    var min = Math.min(lo, zero);
    var max = Math.max(hi, zero);
    var span = max - min;
    if (span <= 0) { return; }
    function pct(v) { return ((v - min) / span) * 100 + "%"; }
    s.querySelector(".interval-stat__band").style.left = pct(lo);
    s.querySelector(".interval-stat__band").style.width = ((hi - lo) / span) * 100 + "%";
    s.querySelector(".interval-stat__point").style.left = pct(point);
    var z = s.querySelector(".interval-stat__zero");
    if (z) { z.style.left = pct(zero); }
  }

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) { el.setAttribute("class", cls); }
    return el;
  }

  function drawCohort(paths) {
    var svg = document.querySelector(".p3-cohort");
    if (!svg || !paths) { return; }
    var W = 100, H = 40;
    var all = paths.fired.concat(paths.replacement);
    var min = Math.min.apply(null, all);
    var max = Math.max.apply(null, all);
    var span = (max - min) || 1;
    var n = paths.fired.length;
    function x(i) { return (i / (n - 1)) * W; }
    function y(v) { return H - ((v - min) / span) * H; }

    var zeroY = y(0);
    var zline = makeEl("line", "p3-cohort__zero");
    zline.setAttribute("x1", "0"); zline.setAttribute("x2", String(W));
    zline.setAttribute("y1", String(zeroY)); zline.setAttribute("y2", String(zeroY));
    svg.appendChild(zline);

    function poly(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }
    poly(paths.fired, "p3-cohort__p-fired");
    poly(paths.replacement, "p3-cohort__p-replacement");
  }

  function init() {
    positionPosterior();
    var data = readCardData();
    if (data) { drawCohort(data.cohort_paths); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
