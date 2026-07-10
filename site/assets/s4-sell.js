/* site/assets/s4-sell.js — value->pixel only. Positions each gap IntervalStat on a
   domain that includes zero, draws the forgone-alpha curve+band SVG, and snaps the gap
   rails + curves to the precomputed horizon the slider selects. No client computation. */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function domainFor(stat) {
    var horizons = JSON.parse(stat.dataset.horizons);
    var values = [0];
    horizons.forEach(function (state) { values.push(state.ci_lo, state.gap, state.ci_hi); });
    return { min: Math.min.apply(null, values), max: Math.max.apply(null, values) };
  }

  function positionGap(stat, lo, point, hi) {
    var zero = parseFloat(stat.dataset.zero || "0");
    var domain = domainFor(stat);
    var min = domain.min, max = domain.max, span = (max - min) || 1;
    function pct(v) { return ((v - min) / span) * 100 + "%"; }
    stat.querySelector(".interval-stat__band").style.left = pct(lo);
    stat.querySelector(".interval-stat__band").style.width = ((hi - lo) / span) * 100 + "%";
    stat.querySelector(".interval-stat__point").style.left = pct(point);
    var z = stat.querySelector(".interval-stat__zero");
    if (z) { z.style.left = pct(zero); }
  }

  function initGapRails() {
    var stats = document.querySelectorAll('.interval-stat[data-domain="gap"]');
    Array.prototype.forEach.call(stats, function (s) {
      positionGap(s, parseFloat(s.dataset.lo), parseFloat(s.dataset.point),
        parseFloat(s.dataset.hi));
    });
  }

  function el(name) { return document.createElementNS(SVGNS, name); }

  function fmtBp(value) {
    var bp = (value * 10000).toFixed(0);
    return (value >= 0 ? "+" : "") + bp + " bp";
  }

  function drawCurve(fig, horizon) {
    // Sourced from the full data-horizons series (6 points), not the shorter
    // data-curve prefix, so the curve can be drawn out to every horizon the
    // slider offers instead of flattening out past the prefix length.
    var curve = JSON.parse(fig.dataset.horizons).slice(0, horizon).map(function (pt) {
      return { horizon: pt.horizon, point: pt.gap, lo: pt.ci_lo, hi: pt.ci_hi };
    });
    var svg = fig.querySelector(".s4-curve__svg");
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    var W = 100, H = 40, n = curve.length;
    var vals = [];
    curve.forEach(function (p) { vals.push(p.lo, p.hi, p.point, 0); });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    var span = (max - min) || 1;
    function x(i) { return n > 1 ? (i / (n - 1)) * W : W / 2; }
    function y(v) { return H - ((v - min) / span) * H; }

    var top = curve.map(function (p, i) { return x(i) + "," + y(p.hi); });
    var bot = curve.map(function (p, i) { return x(i) + "," + y(p.lo); }).reverse();
    var band = el("polygon");
    band.setAttribute("class", "s4-curve__band");
    band.setAttribute("points", top.concat(bot).join(" "));
    svg.appendChild(band);

    var zeroY = y(0), zl = el("line");
    zl.setAttribute("class", "s4-curve__zero");
    zl.setAttribute("x1", "0"); zl.setAttribute("x2", String(W));
    zl.setAttribute("y1", String(zeroY)); zl.setAttribute("y2", String(zeroY));
    svg.appendChild(zl);

    var line = el("polyline");
    line.setAttribute("class", "s4-curve__line");
    line.setAttribute("points", curve.map(function (p, i) {
      return x(i) + "," + y(p.point); }).join(" "));
    svg.appendChild(line);
  }

  function snapHorizon(h) {
    var rails = document.querySelectorAll('.interval-stat[data-domain="gap"]');
    Array.prototype.forEach.call(rails, function (s) {
      if (!s.dataset.horizons) { return; }
      var hz = JSON.parse(s.dataset.horizons);
      var chosen = hz[Math.min(h, hz.length) - 1];
      s.dataset.lo = String(chosen.ci_lo);
      s.dataset.point = String(chosen.gap);
      s.dataset.hi = String(chosen.ci_hi);
      s.dataset.nExits = String(chosen.n_exits);
      var value = s.querySelector('[data-horizon-value="point"]');
      var range = s.querySelector('[data-horizon-value="range"]');
      var exits = s.querySelector('[data-horizon-value="exits"]');
      if (value) { value.textContent = fmtBp(chosen.gap); }
      if (range) { range.textContent = "90% interval " +
        fmtBp(chosen.ci_lo).replace(" bp", "") + " … " + fmtBp(chosen.ci_hi); }
      if (exits) { exits.textContent = chosen.n_exits + " exits"; }
      positionGap(s, chosen.ci_lo, chosen.gap, chosen.ci_hi);
    });
    var figs = document.querySelectorAll(".s4-curve");
    Array.prototype.forEach.call(figs, function (fig) {
      var hz = JSON.parse(fig.dataset.horizons);
      var chosen = hz[Math.min(h, hz.length) - 1];
      drawCurve(fig, chosen.horizon);
    });
  }

  function initSlider() {
    var slider = document.getElementById("s4-horizon");
    if (!slider) { return; }
    var out = document.querySelector('.s4-slider__out');
    function update() {
      var h = parseInt(slider.value, 10);
      if (out) { out.textContent = String(h); }
      snapHorizon(h);
    }
    slider.addEventListener("input", update);
    update();
  }

  function init() {
    initGapRails();
    initSlider();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
