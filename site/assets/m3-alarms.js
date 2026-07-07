(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) { el.setAttribute("class", cls); }
    return el;
  }

  // Running max-drawdown chart: MDD depth >= 0, so 0 sits at the top and the deepest
  // band value at the bottom. Areas for the red/amber familywise bands, line for realized.
  function drawBand(panel) {
    var svg = panel.querySelector(".m3-band");
    if (!svg) { return; }
    var red = JSON.parse(panel.dataset.bandRed);
    var amber = JSON.parse(panel.dataset.bandAmber);
    var realized = JSON.parse(panel.dataset.running);
    var W = 100, H = 40;
    var maxVal = Math.max.apply(null, red.concat(realized)) || 1;
    var n = realized.length;
    function x(i) { return (i / (n - 1)) * W; }
    function y(v) { return (v / maxVal) * H; }
    function area(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); });
      pts.push(x(n - 1) + ",0", x(0) + ",0");
      var poly = makeEl("polygon", cls);
      poly.setAttribute("points", pts.join(" "));
      svg.appendChild(poly);
    }
    function line(arr, cls) {
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", arr.map(function (v, i) { return x(i) + "," + y(v); }).join(" "));
      svg.appendChild(pl);
    }
    area(red, "m3-band__band-red");
    area(amber, "m3-band__band-amber");
    line(realized, "m3-band__realized");
  }

  // Dietvorst dial: snap the readout to a PRECOMPUTED fan state (x2 idiom). No computation.
  function wireDial(panel) {
    var dial = panel.querySelector(".m3-dial");
    if (!dial) { return; }
    var readout = dial.querySelector("[data-dial-readout]");
    var btns = Array.prototype.slice.call(dial.querySelectorAll(".m3-dial__btn"));
    btns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        btns.forEach(function (b) {
          b.classList.remove("m3-dial__btn--active");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("m3-dial__btn--active");
        btn.setAttribute("aria-pressed", "true");
        readout.textContent =
          "at Sharpe " + btn.dataset.sharpe + ": " + btn.dataset.level +
          " (" + btn.dataset.pct + "th pct of the null)";
      });
    });
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll(".m3-manager")).forEach(function (panel) {
      drawBand(panel);
      wireDial(panel);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
