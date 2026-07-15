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
      members.forEach(function (s) {
        if (s.dataset.decisionLow) { los.push(parseFloat(s.dataset.decisionLow)); }
        if (s.dataset.decisionHigh) { his.push(parseFloat(s.dataset.decisionHigh)); }
      });
      var min = Math.min.apply(null, los);
      var max = Math.max.apply(null, his);
      var span = max - min;
      if (!(span > 0)) { return; }
      members.forEach(function (s) {
        var lo = parseFloat(s.dataset.lo), hi = parseFloat(s.dataset.hi), point = parseFloat(s.dataset.point);
        s.querySelector(".interval-stat__band").style.left = ((lo - min) / span) * 100 + "%";
        s.querySelector(".interval-stat__band").style.width = ((hi - lo) / span) * 100 + "%";
        s.querySelector(".interval-stat__point").style.left = ((point - min) / span) * 100 + "%";
        if (s.dataset.decisionLow && s.dataset.decisionHigh) {
          var decisionLow = parseFloat(s.dataset.decisionLow);
          var decisionHigh = parseFloat(s.dataset.decisionHigh);
          var decisionBand = s.querySelector(".m2-decision-band");
          var lowBoundary = s.querySelector(".m2-decision-boundary--low");
          var highBoundary = s.querySelector(".m2-decision-boundary--high");
          decisionBand.style.left = ((decisionLow - min) / span) * 100 + "%";
          decisionBand.style.width = ((decisionHigh - decisionLow) / span) * 100 + "%";
          lowBoundary.style.left = ((decisionLow - min) / span) * 100 + "%";
          highBoundary.style.left = ((decisionHigh - min) / span) * 100 + "%";
        }
      });
    });
  }

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) { el.setAttribute("class", cls); }
    return el;
  }

  function symmetricExtent(series) {
    return series.reduce(function (largest, value) {
      return Math.max(largest, Math.abs(value));
    }, 0) || 1;
  }

  function addLine(svg, cls, x1, y1, x2, y2) {
    var line = makeEl("line", cls);
    line.setAttribute("x1", String(x1));
    line.setAttribute("y1", String(y1));
    line.setAttribute("x2", String(x2));
    line.setAttribute("y2", String(y2));
    svg.appendChild(line);
  }

  function addText(svg, cls, x, y, value, anchor) {
    var label = makeEl("text", cls);
    label.setAttribute("x", String(x));
    label.setAttribute("y", String(y));
    label.setAttribute("text-anchor", anchor || "middle");
    label.textContent = value;
    svg.appendChild(label);
  }

  function drawPayoffChart(svg, market, manager, domain) {
    var width = 320, height = 220;
    var left = 46, right = 12, top = 12, bottom = 32;
    var plotWidth = width - left - right;
    var plotHeight = height - top - bottom;
    var xExtent = domain.x;
    var yExtent = domain.y;

    function x(value) {
      return left + ((value + xExtent) / (2 * xExtent)) * plotWidth;
    }
    function y(value) {
      return top + plotHeight - ((value + yExtent) / (2 * yExtent)) * plotHeight;
    }

    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    addLine(svg, "m2-payoff-grid", left, y(0), width - right, y(0));
    addLine(svg, "m2-payoff-grid", x(0), top, x(0), height - bottom);

    [-xExtent, 0, xExtent].forEach(function (value) {
      addText(svg, "m2-payoff-tick", x(value), height - 10, (value * 100).toFixed(0) + "%");
    });
    [-yExtent, 0, yExtent].forEach(function (value) {
      addText(svg, "m2-payoff-tick", left - 7, y(value) + 3, (value * 100).toFixed(0) + "%", "end");
    });

    market.forEach(function (marketReturn, index) {
      var point = makeEl("circle", "m2-payoff-point");
      point.setAttribute("cx", String(x(marketReturn)));
      point.setAttribute("cy", String(y(manager[index])));
      point.setAttribute("r", "2.5");
      svg.appendChild(point);
    });
  }

  // Both charts receive one shared x/y domain. This maps committed paired
  // observations to pixels; it does not estimate a payoff curve.
  function drawPayoffCharts(data) {
    var charts = Array.prototype.slice.call(document.querySelectorAll(".m2-payoff-chart"));
    var market = data.market_returns;
    if (!charts.length || !market || !market.length) { return; }

    var honest = data.managers.honest.monthly_returns;
    var overlaid = data.managers.overlaid.monthly_returns;
    if (market.length !== honest.length || market.length !== overlaid.length) { return; }

    var domain = {
      x: symmetricExtent(market),
      y: symmetricExtent(honest.concat(overlaid))
    };
    charts.forEach(function (svg) {
      var series = data.managers[svg.dataset.series].monthly_returns;
      drawPayoffChart(svg, market, series, domain);
    });
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
      drawPayoffCharts(data);
      drawStressStrip(data.managers.honest.monthly_returns, data.managers.overlaid.monthly_returns);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
