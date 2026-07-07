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

  // Draw one power-curve exhibit: power (0..1) on y, T on x, two lines
  // (OLS t-test, posterior) plus a dashed 80%-power reference line.
  function drawCurve(svg) {
    var T = nums(svg.dataset.t);
    var ols = nums(svg.dataset.ols);
    var posterior = nums(svg.dataset.posterior);
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

    function line(arr, cls) {
      var pts = arr.map(function (p, i) { return x(T[i]) + "," + y(p); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }
    line(ols, "x1-powercurve__ols");
    line(posterior, "x1-powercurve__posterior");
  }

  function init() {
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
