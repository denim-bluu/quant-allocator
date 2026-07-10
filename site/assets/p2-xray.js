(function () {
  "use strict";

  function signed(value) {
    var number = Number(value);
    return (number >= 0 ? "+" : "") + number.toFixed(3);
  }

  function positionIntervals() {
    var groups = {};
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".interval-stat[data-domain]")
    );
    stats.forEach(function (stat) {
      var domain = stat.getAttribute("data-domain");
      var lo = Number(stat.getAttribute("data-lo"));
      var point = Number(stat.getAttribute("data-point"));
      var hi = Number(stat.getAttribute("data-hi"));
      if (![lo, point, hi].every(Number.isFinite)) { return; }
      if (!groups[domain]) { groups[domain] = { min: lo, max: hi }; }
      groups[domain].min = Math.min(groups[domain].min, lo, point);
      groups[domain].max = Math.max(groups[domain].max, hi, point);
    });
    stats.forEach(function (stat) {
      var domain = groups[stat.getAttribute("data-domain")];
      if (!domain) { return; }
      var span = domain.max - domain.min || 1;
      var lo = Number(stat.getAttribute("data-lo"));
      var point = Number(stat.getAttribute("data-point"));
      var hi = Number(stat.getAttribute("data-hi"));
      var band = stat.querySelector(".interval-stat__band");
      var marker = stat.querySelector(".interval-stat__point");
      if (!band || !marker) { return; }
      band.style.left = ((lo - domain.min) / span) * 100 + "%";
      band.style.width = ((hi - lo) / span) * 100 + "%";
      marker.style.left = ((point - domain.min) / span) * 100 + "%";
    });
  }

  function init() {
    var dataNode = document.getElementById("card-data");
    var readout = document.querySelector("[data-p2-dial-readout]");
    if (!dataNode || !readout) { return; }
    var payload = JSON.parse(dataNode.textContent);
    var bookStat = document.querySelector("[data-p2-dial-book]");
    positionIntervals();
    var buttons = Array.prototype.slice.call(document.querySelectorAll(".p2-dial__button"));
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var target = Number(button.getAttribute("data-r-sd"));
        var state = payload.r_noise_dial.find(function (item) {
          return Number(item.r_sd) === target;
        });
        if (!state) { return; }
        buttons.forEach(function (candidate) {
          candidate.classList.remove("is-active");
          candidate.setAttribute("aria-pressed", "false");
        });
        button.classList.add("is-active");
        button.setAttribute("aria-pressed", "true");
        if (bookStat) {
          bookStat.setAttribute("data-lo", state.book.ci_lo);
          bookStat.setAttribute("data-point", state.book.point);
          bookStat.setAttribute("data-hi", state.book.ci_hi);
          bookStat.querySelector(".interval-stat__value").textContent = signed(state.book.point);
          bookStat.querySelector(".interval-stat__range").textContent =
            Math.round(state.book.level * 100) + "% credible interval " +
            signed(state.book.ci_lo) + " … " + signed(state.book.ci_hi);
          positionIntervals();
        }
        readout.textContent = "R sd " + target.toFixed(2) + ": book " +
          signed(state.book.point) + ", " + Math.round(state.book.level * 100) + "% " +
          signed(state.book.ci_lo) +
          " … " + signed(state.book.ci_hi);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
