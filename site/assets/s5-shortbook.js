(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function line(svg, arr, cls, W, H, lo, hi) {
    var span = (hi - lo) || 1;
    var n = arr.length;
    var pts = arr.map(function (v, i) {
      var x = (i / (n - 1)) * W;
      var y = H - ((v - lo) / span) * H;   // higher value -> higher on the chart
      return x + "," + y;
    });
    var pl = document.createElementNS(SVGNS, "polyline");
    pl.setAttribute("class", cls);
    pl.setAttribute("points", pts.join(" "));
    svg.appendChild(pl);
  }

  function drawSplit(panel) {
    var svg = panel.querySelector(".s5-split-chart");
    if (!svg) { return; }
    var hedge = JSON.parse(panel.dataset.cumHedge);
    var alpha = JSON.parse(panel.dataset.cumAlpha);
    var all = hedge.concat(alpha);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    line(svg, hedge, "s5-split-chart__hedge", 100, 44, lo, hi);
    line(svg, alpha, "s5-split-chart__alpha", 100, 44, lo, hi);
  }

  function fmtPct(x) { return (x >= 0 ? "+" : "") + (x * 100).toFixed(2) + "%"; }

  function wireDial(panel) {
    var dial = panel.querySelector(".s5-dial");
    if (!dial) { return; }
    var grid = JSON.parse(panel.dataset.borrowDial);
    var range = dial.querySelector(".s5-dial__range");
    var readout = dial.querySelector("[data-dial-readout]");
    function render() {
      var e = grid[parseInt(range.value, 10)];
      readout.textContent =
        "at " + (e.fee * 100).toFixed(1) + "%/yr borrow: net " + fmtPct(e.net) +
        " (" + fmtPct(e.net_ci_lo) + " … " + fmtPct(e.net_ci_hi) + ") — " +
        (e.calibrated ? "still calibrated" : "no detectable alpha");
    }
    range.addEventListener("input", render);
    render();
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll(".s5-manager")).forEach(function (panel) {
      drawSplit(panel);
      wireDial(panel);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
