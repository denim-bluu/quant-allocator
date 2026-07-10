/* Selects committed M4 pair and stress states; no estimator runs in the browser. */
(function () {
  "use strict";

  function readData() {
    var node = document.getElementById("card-data");
    return node ? JSON.parse(node.textContent) : null;
  }

  function percent(value) { return (value * 100).toFixed(1) + "%"; }

  function railPosition(value, domain) {
    return domain === "cosine" ? (value + 1) * 50 : value * 100;
  }

  function updateStat(statId, value, domain) {
    var stat = document.getElementById(statId + "-stat");
    var valueNode = document.getElementById(statId + "-value");
    if (!stat || !valueNode) { return; }
    stat.dataset.lo = String(value);
    stat.dataset.point = String(value);
    stat.dataset.hi = String(value);
    valueNode.textContent = domain === "cosine" ? value.toFixed(3) : percent(value);
    var position = railPosition(value, domain) + "%";
    stat.querySelector(".interval-stat__band").style.left = position;
    stat.querySelector(".interval-stat__point").style.left = position;
  }

  function updatePair(data, i, j) {
    var names = data.heatmap.managers;
    document.getElementById("m4-selected-pair").textContent = names[i] + " × " + names[j];
    updateStat("m4-raw", data.heatmap.raw[i][j], "overlap");
    updateStat("m4-liquidity", data.heatmap.liquidity[i][j], "overlap");
    updateStat("m4-cosine", data.heatmap.cosine[i][j], "cosine");
  }

  function initHeatmap(data) {
    var cells = document.querySelectorAll(".m4-cell:not([disabled])");
    Array.prototype.forEach.call(cells, function (cell) {
      cell.addEventListener("click", function () {
        updatePair(data, parseInt(cell.dataset.i, 10), parseInt(cell.dataset.j, 10));
      });
    });
  }

  function renderStress(scenario) {
    var container = document.getElementById("m4-unwind-bars");
    var worst = scenario.worst.days_stressed_volume || 1;
    var html = scenario.rows.map(function (row) {
      var width = (row.days_stressed_volume / worst) * 100;
      return '<div class="m4-bar"><div class="m4-bar__label"><span>' + row.asset +
        " · " + row.direction + '</span><strong class="m4-bar__value">' +
        row.days_stressed_volume.toFixed(1) +
        ' days</strong></div><div class="m4-bar__track"><span style="width:' + width +
        '%"></span></div><div class="m4-impact">illustrative impact ' +
        (row.illustrative.impact_rate * 100).toFixed(2) +
        "% — illustrative — not a forecast</div></div>";
    }).join("");
    container.innerHTML = html;
  }

  function initStress(data) {
    var slider = document.getElementById("m4-stress-delta");
    var output = document.getElementById("m4-stress-output");
    if (!slider || !output) { return; }
    function update() {
      var scenario = data.stress_scenarios[parseInt(slider.value, 10)];
      output.textContent = Math.round(scenario.stress_delta * 100) + "%";
      renderStress(scenario);
    }
    slider.addEventListener("input", update);
  }

  function init() {
    var data = readData();
    if (!data) { return; }
    initHeatmap(data);
    initStress(data);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
