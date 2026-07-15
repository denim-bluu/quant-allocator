(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) {
      el.setAttribute("class", cls);
    }
    return el;
  }

  function nums(attr) {
    return attr.split(",").map(function (v) { return parseFloat(v); });
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
    var text = makeEl("text", cls);
    text.setAttribute("x", String(x));
    text.setAttribute("y", String(y));
    text.setAttribute("text-anchor", anchor || "middle");
    text.textContent = value;
    svg.appendChild(text);
  }

  // Display-only projection of four committed posterior-power cells. The
  // browser maps powers and Wilson endpoints to pixels; it estimates nothing.
  function drawTierComparison(svg) {
    if (!svg) return;
    var months = nums(svg.dataset.months);
    var target = parseFloat(svg.dataset.target);
    var returns = nums(svg.dataset.returns);
    var returnsLo = nums(svg.dataset.returnsLo);
    var returnsHi = nums(svg.dataset.returnsHi);
    var exposure = nums(svg.dataset.exposure);
    var exposureLo = nums(svg.dataset.exposureLo);
    var exposureHi = nums(svg.dataset.exposureHi);
    var width = 420, height = 250;
    var left = 48, right = 18, top = 18, bottom = 42;
    var plotLeft = left + 32;
    var plotRight = width - right - 32;
    var plotWidth = plotRight - plotLeft;
    var plotHeight = height - top - bottom;
    var monthMin = Math.min.apply(null, months);
    var monthMax = Math.max.apply(null, months);
    var monthSpan = monthMax - monthMin || 1;

    function x(month) { return plotLeft + ((month - monthMin) / monthSpan) * plotWidth; }
    function y(power) { return top + (1 - power) * plotHeight; }

    while (svg.firstChild) svg.removeChild(svg.firstChild);
    addLine(svg, "x1-tier-chart__axis", left, top, left, height - bottom);
    addLine(svg, "x1-tier-chart__axis", left, height - bottom, width - right, height - bottom);
    addLine(svg, "x1-tier-chart__threshold", left, y(target), width - right, y(target));

    [0, target, 1].forEach(function (value) {
      addLine(svg, "x1-tier-chart__tick", left - 4, y(value), left, y(value));
    });

    function drawSeries(values, lows, highs, cls, offset, label) {
      months.forEach(function (month, index) {
        var cx = x(month) + offset;
        addLine(svg, "x1-tier-chart__interval " + cls, cx, y(lows[index]), cx, y(highs[index]));
        addLine(svg, "x1-tier-chart__cap " + cls, cx - 5, y(lows[index]), cx + 5, y(lows[index]));
        addLine(svg, "x1-tier-chart__cap " + cls, cx - 5, y(highs[index]), cx + 5, y(highs[index]));
        var point = makeEl("circle", "x1-tier-chart__point " + cls);
        point.setAttribute("cx", String(cx));
        point.setAttribute("cy", String(y(values[index])));
        point.setAttribute("r", "5");
        svg.appendChild(point);
        addText(
          svg,
          "x1-tier-chart__value " + cls,
          cx,
          y(values[index]) - 10,
          label + " " + (values[index] * 100).toFixed(1) + "%"
        );
      });
    }

    drawSeries(returns, returnsLo, returnsHi, "x1-tier-chart--returns", -28, "Returns");
    drawSeries(exposure, exposureLo, exposureHi, "x1-tier-chart--exposure", 28, "Exposures");
    months.forEach(function (month) {
      addText(svg, "x1-tier-chart__month", x(month), height - 14, String(month));
    });
  }

  // Draw one power-curve exhibit: power (0..1) on y, T on x, two lines
  // (OLS t-test, posterior) plus a dashed 80%-power reference line.
  function drawCurve(svg) {
    var T = nums(svg.dataset.t);
    var ols = nums(svg.dataset.ols);
    var olsLo = nums(svg.dataset.olsLo);
    var olsHi = nums(svg.dataset.olsHi);
    var posterior = nums(svg.dataset.posterior);
    var posteriorLo = nums(svg.dataset.posteriorLo);
    var posteriorHi = nums(svg.dataset.posteriorHi);
    if (!T.length) {
      return;
    }
    var W = 100;
    var H = 44;
    var tMin = T[0];
    var tMax = T[T.length - 1];
    var tSpan = tMax - tMin || 1;
    function x(t) { return ((t - tMin) / tSpan) * W; }
    function y(p) { return H - p * H; } // power in [0,1]

    var ref = makeEl("line", "x1-powercurve__ref");
    ref.setAttribute("x1", "0");
    ref.setAttribute("y1", String(y(0.8)));
    ref.setAttribute("x2", String(W));
    ref.setAttribute("y2", String(y(0.8)));
    svg.appendChild(ref);

    function envelope(lo, hi, cls) {
      var upper = hi.map(function (p, i) { return x(T[i]) + "," + y(p); });
      var lower = lo.map(function (p, i) { return x(T[i]) + "," + y(p); }).reverse();
      var polygon = makeEl("polygon", cls);
      polygon.setAttribute("points", upper.concat(lower).join(" "));
      svg.appendChild(polygon);
    }

    function line(arr, cls) {
      var pts = arr.map(function (p, i) { return x(T[i]) + "," + y(p); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }
    envelope(olsLo, olsHi, "x1-powercurve__uncertainty x1-powercurve__uncertainty--ols");
    envelope(posteriorLo, posteriorHi, "x1-powercurve__uncertainty x1-powercurve__uncertainty--posterior");
    line(ols, "x1-powercurve__ols");
    line(posterior, "x1-powercurve__posterior");
  }

  function init() {
    drawTierComparison(document.querySelector(".x1-tier-chart"));
    Array.prototype.slice
      .call(document.querySelectorAll(".x1-powercurve"))
      .forEach(drawCurve);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
