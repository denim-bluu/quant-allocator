(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function readCardData() {
    var el = document.getElementById("card-data");
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  function make(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) { el.setAttribute("class", cls); }
    return el;
  }

  // Shared IntervalStat band positioning (same idiom as s2-tearsheet.js), scoped to
  // this page and grouped by data-domain. Reads verbatim numbers; computes only pixels.
  function positionBands() {
    var stats = Array.prototype.slice.call(document.querySelectorAll(".m1-panel .interval-stat"));
    var groups = {};
    stats.forEach(function (s) {
      var key = s.dataset.domain || "_";
      (groups[key] = groups[key] || []).push(s);
    });
    Object.keys(groups).forEach(function (key) {
      var members = groups[key];
      var min = Math.min.apply(null, members.map(function (s) { return parseFloat(s.dataset.lo); }));
      var max = Math.max.apply(null, members.map(function (s) { return parseFloat(s.dataset.hi); }));
      var span = max - min;
      if (span <= 0) { return; }
      members.forEach(function (s) {
        var lo = parseFloat(s.dataset.lo), hi = parseFloat(s.dataset.hi), pt = parseFloat(s.dataset.point);
        s.querySelector(".interval-stat__band").style.left = ((lo - min) / span) * 100 + "%";
        s.querySelector(".interval-stat__band").style.width = ((hi - lo) / span) * 100 + "%";
        s.querySelector(".interval-stat__point").style.left = ((pt - min) / span) * 100 + "%";
      });
    });
  }

  // Main chart: measured net-beta path + band edges + honest-wander envelope + a marker
  // at the CUSUM alarm month. Drawdown-style value->pixel; no number is produced here.
  function drawDriftChart(data) {
    var svg = document.querySelector(".m1-drift-chart");
    if (!svg || !data) { return; }
    var v = data.visual, band = data.band;
    var W = 100, H = 44;
    var series = v.beta_path;
    var n = series.length;
    var all = series.concat(v.wander_p05, v.wander_p95, [band.lower, band.upper]);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var span = (hi - lo) || 1;
    function x(i) { return (i / (n - 1)) * W; }
    function y(val) { return H - ((val - lo) / span) * H; }

    // Honest-wander envelope (p05..p95) as a filled band.
    var pts = [];
    v.wander_p95.forEach(function (val, i) { pts.push(x(i) + "," + y(val)); });
    for (var i = v.wander_p05.length - 1; i >= 0; i--) { pts.push(x(i) + "," + y(v.wander_p05[i])); }
    var env = make("polygon", "m1-drift-chart__wander");
    env.setAttribute("points", pts.join(" "));
    svg.appendChild(env);

    // Band edges (upper/lower) as horizontal rules.
    [band.upper, band.lower].forEach(function (edge) {
      var ln = make("line", "m1-drift-chart__band");
      ln.setAttribute("x1", "0"); ln.setAttribute("x2", String(W));
      ln.setAttribute("y1", String(y(edge))); ln.setAttribute("y2", String(y(edge)));
      svg.appendChild(ln);
    });

    // Measured path.
    var line = make("polyline", "m1-drift-chart__path");
    line.setAttribute("points", series.map(function (val, i) { return x(i) + "," + y(val); }).join(" "));
    svg.appendChild(line);

    // Alarm onset marker.
    if (v.alarm_month !== null && v.alarm_month !== undefined) {
      var mark = make("line", "m1-drift-chart__alarm");
      mark.setAttribute("x1", String(x(v.alarm_month))); mark.setAttribute("x2", String(x(v.alarm_month)));
      mark.setAttribute("y1", "0"); mark.setAttribute("y2", String(H));
      svg.appendChild(mark);
    }
  }

  // R-tier rolling-beta path, greyed (descriptive-only). Nulls (pre-window) are skipped.
  function drawRbsa(data) {
    var svg = document.querySelector(".m1-rbsa-chart");
    if (!svg || !data) { return; }
    var series = data.visual.rolling_beta;
    var defined = series.map(function (val, i) { return [i, val]; }).filter(function (p) { return p[1] !== null; });
    if (defined.length < 2) { return; }
    var W = 100, H = 30, n = series.length;
    var vals = defined.map(function (p) { return p[1]; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var span = (hi - lo) || 1;
    var pts = defined.map(function (p) {
      return ((p[0] / (n - 1)) * W) + "," + (H - ((p[1] - lo) / span) * H);
    }).join(" ");
    var line = make("polyline", "m1-rbsa-chart__path");
    line.setAttribute("points", pts);
    svg.appendChild(line);
  }

  function init() {
    positionBands();
    var data = readCardData();
    drawDriftChart(data);
    drawRbsa(data);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
