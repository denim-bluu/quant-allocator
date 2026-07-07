(function () {
  "use strict";

  var DIALS = ["ic", "half_life", "sizing", "T", "tier"];

  // D-22 positional indices.
  var POINT = 0, LO = 1, HI = 2, VERDICT = 3, GATE = 4, THRESHOLD = 5, UNITS = 6, WILSON = 7;

  // Per-analytic display formatters. No math beyond unit scaling for display.
  function pct1(x) {
    var v = (x * 100).toFixed(1);
    return (x >= 0 ? "+" : "") + v + "%";
  }
  function ratio2(x) { return x.toFixed(2); }
  function slope4(x) { return x.toFixed(4); }

  var FORMAT = {
    alpha: { fmt: pct1, band: "95% band " },
    sharpe: { fmt: ratio2, band: "95% band " },
    hit_rate: { fmt: function (x) { return (x * 100).toFixed(1) + "%"; }, band: "95% band " },
    sizing_slope: { fmt: slope4, band: "95% band " }
  };

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

  function readState(controls) {
    var state = {};
    DIALS.forEach(function (d) {
      state[d] = controls.getAttribute("data-default-" + d);
    });
    return state;
  }

  function cellKey(state) {
    return DIALS.map(function (d) { return state[d]; }).join("|");
  }

  function gateReason(arr) {
    if (arr[GATE] === "open") {
      return "gate open — cleared " + arr[THRESHOLD] + " " + arr[UNITS];
    }
    if (arr[THRESHOLD] === null) {
      return "no threshold reached in the measured range";
    }
    return "gate closed — opens at " + arr[THRESHOLD] + " " + arr[UNITS];
  }

  function paintSlot(slot, arr) {
    var name = slot.getAttribute("data-analytic");
    var f = FORMAT[name];
    var stat = slot.querySelector(".interval-stat");
    var value = slot.querySelector(".interval-stat__value");
    var range = slot.querySelector(".interval-stat__range");
    var band = slot.querySelector(".interval-stat__band");
    var mark = slot.querySelector(".interval-stat__point");
    var chip = slot.querySelector(".verdict-chip");
    var wilson = slot.querySelector(".x2-wilson__value");
    var reason = slot.querySelector(".power-gate__reason");

    value.textContent = f.fmt(arr[POINT]);
    range.textContent = f.band + f.fmt(arr[LO]) + " … " + f.fmt(arr[HI]);
    stat.setAttribute("data-verdict", arr[VERDICT]);
    chip.setAttribute("data-verdict", arr[VERDICT]);
    chip.textContent = arr[VERDICT];
    wilson.textContent = arr[WILSON].toFixed(3);
    reason.textContent = gateReason(arr);

    // Position: band spans lo..hi, point placed within it. Pixel layout only.
    var span = arr[HI] - arr[LO];
    band.style.left = "0%";
    band.style.width = "100%";
    mark.style.left = (span > 0 ? ((arr[POINT] - arr[LO]) / span) * 100 : 50) + "%";
  }

  function render(data, state) {
    var cell = data.cells[cellKey(state)];
    var slots = Array.prototype.slice.call(
      document.querySelectorAll(".x2-analytic")
    );
    slots.forEach(function (slot) {
      var name = slot.getAttribute("data-analytic");
      var arr = cell ? cell[name] : null;
      if (arr) {
        slot.hidden = false;
        paintSlot(slot, arr);
      } else {
        slot.hidden = true;
      }
    });
    var banner = document.querySelector("[data-falsealarm]");
    if (banner) {
      banner.hidden = state.ic !== "0";
    }
  }

  function bindDials(controls, onChange) {
    controls.addEventListener("click", function (evt) {
      var btn = evt.target.closest(".x2-dial__btn");
      if (!btn) {
        return;
      }
      var group = btn.closest(".x2-dial");
      var dial = group.getAttribute("data-dial");
      Array.prototype.slice.call(group.querySelectorAll(".x2-dial__btn")).forEach(
        function (b) {
          var on = b === btn;
          b.classList.toggle("x2-dial__btn--active", on);
          b.setAttribute("aria-pressed", on ? "true" : "false");
        }
      );
      onChange(dial, btn.getAttribute("data-value"));
    });
  }

  function init() {
    var data = readCardData();
    var controls = document.querySelector("[data-dials]");
    if (!data || !controls) {
      return;
    }
    var state = readState(controls);
    render(data, state);
    bindDials(controls, function (dial, value) {
      state[dial] = value;
      render(data, state);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
