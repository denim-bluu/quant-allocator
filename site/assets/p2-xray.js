(function () {
  "use strict";

  function signed(value) {
    var number = Number(value);
    return (number >= 0 ? "+" : "") + number.toFixed(3);
  }

  function init() {
    var dataNode = document.getElementById("card-data");
    var readout = document.querySelector("[data-p2-dial-readout]");
    if (!dataNode || !readout) { return; }
    var payload = JSON.parse(dataNode.textContent);
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
        readout.textContent = "R sd " + target.toFixed(2) + ": book " +
          signed(state.book.point) + ", 90% " + signed(state.book.ci_lo) +
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
