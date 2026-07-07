(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function readCardData() {
    var el = document.getElementById("card-data");
    if (!el) {
      return null;
    }
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  // Position IntervalStat bands on a shared pixel domain per data-domain group so
  // stats in the same group are visually comparable. Reads verbatim numbers from
  // data-* attributes; computes only pixel positions, never a displayed number.
  function positionBands() {
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".tearsheet-panel .interval-stat")
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

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) {
      el.setAttribute("class", cls);
    }
    return el;
  }

  // Drawdown chart: drawdowns are <= 0, so 0 sits at the top and the deepest
  // envelope point sits at the bottom. Areas for p99/p95, lines for p50/realized.
  function drawDrawdown(band) {
    var svg = document.querySelector(".s2-drawdown");
    if (!svg || !band) {
      return;
    }
    var W = 100;
    var H = 40;
    var all = band.p99.concat(band.p95, band.p50, band.realized);
    var minVal = Math.min.apply(null, all);
    if (minVal >= 0) {
      return;
    }
    var n = band.realized.length;
    function x(i) { return (i / (n - 1)) * W; }
    function y(v) { return (v / minVal) * H; } // v,minVal <= 0 -> [0, H]

    function area(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); });
      pts.push(x(n - 1) + ",0", x(0) + ",0");
      var poly = makeEl("polygon", cls);
      poly.setAttribute("points", pts.join(" "));
      svg.appendChild(poly);
    }
    function line(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }

    area(band.p99, "s2-drawdown__p99");
    area(band.p95, "s2-drawdown__p95");
    line(band.p50, "s2-drawdown__p50");
    line(band.realized, "s2-drawdown__realized");
  }

  // Monthly return strip: bars from a midline, positive up / negative down.
  function drawStrip(returns) {
    var svg = document.querySelector(".s2-strip");
    if (!svg || !returns || !returns.length) {
      return;
    }
    var W = 100;
    var H = 30;
    var mid = H / 2;
    var maxAbs = returns.reduce(function (m, v) {
      return Math.max(m, Math.abs(v));
    }, 0) || 1;
    var bw = W / returns.length;
    returns.forEach(function (v, i) {
      var h = (Math.abs(v) / maxAbs) * (H / 2);
      var rect = makeEl("rect", v >= 0 ? "s2-strip__pos" : "s2-strip__neg");
      rect.setAttribute("x", String(i * bw));
      rect.setAttribute("y", String(v >= 0 ? mid - h : mid));
      rect.setAttribute("width", String(bw * 0.8));
      rect.setAttribute("height", String(h || 0.1));
      svg.appendChild(rect);
    });
  }

  function init() {
    positionBands();
    var data = readCardData();
    if (data) {
      drawDrawdown(data.drawdown_band);
      drawStrip(data.monthly_returns);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
