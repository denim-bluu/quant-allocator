(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";
  function el(name, cls) { var e = document.createElementNS(SVGNS, name);
    if (cls) { e.setAttribute("class", cls); } return e; }

  // Sizing scatter: |size| on x, active contribution on y (centered), plus a fit line.
  function drawScatter(panel) {
    var svg = panel.querySelector(".s3-scatter");
    if (!svg) { return; }
    var pts = JSON.parse(panel.dataset.scatter);
    if (!pts.length) { return; }
    var W = 100, H = 60;
    var xs = pts.map(function (p) { return p.size; });
    var ys = pts.map(function (p) { return p.contribution; });
    var xmax = Math.max.apply(null, xs) || 1;
    var ymax = Math.max.apply(null, ys.map(Math.abs)) || 1;
    function x(v) { return (v / xmax) * W; }
    function y(v) { return H / 2 - (v / ymax) * (H / 2); }
    pts.forEach(function (p) {
      var c = el("circle", "s3-scatter__pt");
      c.setAttribute("cx", x(p.size)); c.setAttribute("cy", y(p.contribution));
      c.setAttribute("r", 0.6); svg.appendChild(c);
    });
  }

  // Decay curve: D(m) by holding age; nulls (thin ages) break the line.
  function drawDecay() {
    var svg = document.querySelector(".s3-decay-svg");
    if (!svg) { return; }
    var curve = JSON.parse(svg.dataset.curve);
    var finite = curve.filter(function (v) { return v !== null; });
    var vmax = Math.max.apply(null, finite) || 1;
    var n = curve.length, W = 100, H = 50;
    var d = "", pen = false;
    curve.forEach(function (v, i) {
      if (v === null) { pen = false; return; }
      var px = (i / (n - 1)) * W, py = H - (v / vmax) * H;
      d += (pen ? " L" : " M") + px + "," + py; pen = true;
    });
    var path = el("path", "s3-decay-svg__pt");
    path.setAttribute("d", d.trim()); svg.appendChild(path);
  }

  // Holding decomposition: stacked bar, one segment per bucket in canonical fresh->stale
  // order (the JSON object is key-sorted, so the order comes from data-order).
  function drawHolding() {
    var bar = document.querySelector(".s3-holding-bar");
    if (!bar) { return; }
    var shares = JSON.parse(bar.dataset.shares);
    var order = JSON.parse(bar.dataset.order);
    order.forEach(function (label) {
      var share = shares[label] || 0;
      var seg = document.createElement("span");
      seg.style.width = Math.max(0, share * 100) + "%";
      seg.title = label + ": " + (share * 100).toFixed(0) + "%";
      bar.appendChild(seg);
    });
  }

  function init() {
    Array.prototype.slice.call(document.querySelectorAll(".s3-manager")).forEach(drawScatter);
    drawDecay();
    drawHolding();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
