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

  // Draw one exposure path (value -> pixel) and shade the delta dead-band around
  // the starting exposure. Pure layout; no displayed number is produced here.
  function drawSpark(container, series, delta) {
    var svg = container.querySelector(".saydo-spark");
    if (!svg || !series || series.length < 2) {
      return;
    }
    var start = parseFloat(container.dataset.start);
    var values = series.map(function (p) { return p.value; });
    var lo = Math.min.apply(null, values.concat([start - delta]));
    var hi = Math.max.apply(null, values.concat([start + delta]));
    var span = hi - lo || 1;
    var W = 100;
    var H = 40;

    function x(i) { return (i / (series.length - 1)) * W; }
    function y(v) { return H - ((v - lo) / span) * H; }

    var bandTop = y(start + delta);
    var bandBottom = y(start - delta);
    var band = document.createElementNS(SVGNS, "rect");
    band.setAttribute("x", "0");
    band.setAttribute("y", String(bandTop));
    band.setAttribute("width", String(W));
    band.setAttribute("height", String(bandBottom - bandTop));
    band.setAttribute("class", "saydo-spark__band");
    svg.appendChild(band);

    var points = series
      .map(function (p, i) { return x(i) + "," + y(p.value); })
      .join(" ");
    var line = document.createElementNS(SVGNS, "polyline");
    line.setAttribute("points", points);
    line.setAttribute("class", "saydo-spark__line");
    svg.appendChild(line);
  }

  function initSparks(data) {
    var containers = Array.prototype.slice.call(
      document.querySelectorAll(".saydo-exposure")
    );
    containers.forEach(function (c) {
      var series = data.exposure_paths[c.dataset.instrument];
      drawSpark(c, series, parseFloat(c.dataset.delta));
    });
  }

  function initFocus() {
    var btn = document.querySelector("[data-saydo-focus]");
    var root = document.querySelector("[data-saydo]");
    if (!btn || !root) {
      return;
    }
    btn.addEventListener("click", function () {
      root.classList.toggle("saydo--focus");
    });
  }

  function init() {
    var data = readCardData();
    if (data) {
      initSparks(data);
    }
    initFocus();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
