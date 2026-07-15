(function (global) {
  "use strict";

  var FACETS = [
    "stage",
    "asset",
    "vehicle",
    "access",
    "modality",
    "readiness",
    "attestation",
    "family",
  ];

  function emptyFacets() {
    var facets = {};
    FACETS.forEach(function (key) {
      facets[key] = [];
    });
    return facets;
  }

  function defaultState() {
    return { view: "journey", q: "", preset: "", facets: emptyFacets(), minimumAllowed: [] };
  }

  function uniqueSorted(values) {
    return Array.from(new Set(values.filter(Boolean))).sort();
  }

  function parseQuery(search) {
    var state = defaultState();
    var params = new URLSearchParams(search || "");
    state.view = params.get("view") === "catalog" ? "catalog" : "journey";
    state.q = (params.get("q") || "").trim();
    state.preset = params.get("preset") || "";
    FACETS.forEach(function (key) {
      state.facets[key] = uniqueSorted(params.getAll(key));
    });
    if (state.preset === "returns-only") state.minimumAllowed = ["returns"];
    return state;
  }

  function serializeState(state) {
    var params = new URLSearchParams();
    if (state.view === "catalog") params.set("view", "catalog");
    if (state.q) params.set("q", state.q.trim());
    if (state.preset) params.set("preset", state.preset);
    FACETS.forEach(function (key) {
      uniqueSorted((state.facets && state.facets[key]) || []).forEach(function (value) {
        params.append(key, value);
      });
    });
    var encoded = params.toString();
    return encoded ? "?" + encoded : "";
  }

  function presetState(name) {
    var state = defaultState();
    state.view = "catalog";
    state.preset = name;
    if (name === "returns-only") {
      state.minimumAllowed = ["returns"];
    } else if (name === "holdings") {
      state.facets.modality = ["holdings"];
    } else if (name === "screen-managers") {
      state.facets.stage = ["discover", "underwrite"];
    } else if (name === "ic-preparation") {
      state.facets.stage = ["construct", "govern"];
    } else if (name === "credit-private") {
      state.facets.asset = [
        "fixed-income-credit",
        "private-credit",
        "private-equity",
        "real-assets",
        "structured-credit",
      ];
    }
    return state;
  }

  function intersects(left, right) {
    return left.some(function (value) {
      return right.indexOf(value) !== -1;
    });
  }

  function matchesCard(card, state) {
    var query = (state.q || "").trim().toLowerCase();
    if (query && (card.search || "").toLowerCase().indexOf(query) === -1) return false;
    var facets = state.facets || emptyFacets();
    for (var index = 0; index < FACETS.length; index += 1) {
      var key = FACETS[index];
      var selected = facets[key] || [];
      if (selected.length && !intersects(card[key] || [], selected)) return false;
    }
    if (state.minimumAllowed && state.minimumAllowed.length) {
      var minimum = card.minimumModality || [];
      if (!minimum.every(function (value) { return state.minimumAllowed.indexOf(value) !== -1; })) {
        return false;
      }
    }
    return true;
  }

  function hasActiveFilter(state) {
    return Boolean(
      state.q ||
      state.preset ||
      FACETS.some(function (key) { return (state.facets[key] || []).length; })
    );
  }

  function tokens(value) {
    return (value || "").split(/\s+/).filter(Boolean);
  }

  function cardFromElement(element) {
    return {
      element: element,
      search: element.dataset.search || "",
      stage: tokens(element.dataset.stage),
      asset: tokens(element.dataset.asset),
      vehicle: tokens(element.dataset.vehicle),
      access: tokens(element.dataset.access),
      modality: tokens(element.dataset.modality),
      minimumModality: tokens(element.dataset.minimumModality),
      readiness: tokens(element.dataset.readiness),
      attestation: tokens(element.dataset.attestation),
      family: tokens(element.dataset.family),
    };
  }

  function initialize() {
    var root = document.querySelector("[data-gallery]");
    if (!root) return;
    var search = root.querySelector("[data-gallery-search]");
    var filters = Array.from(root.querySelectorAll("[data-gallery-filter]"));
    var viewButtons = Array.from(root.querySelectorAll("[data-gallery-view]"));
    var presetButtons = Array.from(root.querySelectorAll("[data-gallery-preset]"));
    var cards = Array.from(root.querySelectorAll("[data-gallery-card]")).map(cardFromElement);
    var sections = Array.from(root.querySelectorAll("[data-stage-section]"));
    var count = root.querySelector("[data-gallery-count]");
    var empty = root.querySelector("[data-gallery-empty]");
    var state = parseQuery(global.location.search);

    function writeUrl(mode) {
      var target = global.location.pathname + serializeState(state) + global.location.hash;
      global.history[mode + "State"](null, "", target);
    }

    function syncControls() {
      root.dataset.view = state.view;
      search.value = state.q;
      viewButtons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.dataset.galleryView === state.view));
      });
      presetButtons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.dataset.galleryPreset === state.preset));
      });
      filters.forEach(function (input) {
        input.checked = (state.facets[input.name] || []).indexOf(input.value) !== -1;
      });
    }

    function render() {
      var visible = 0;
      var filtering = hasActiveFilter(state);
      cards.forEach(function (card) {
        var matches = matchesCard(card, state);
        card.element.hidden = !matches;
        if (matches) visible += 1;
      });
      sections.forEach(function (section) {
        section.hidden = filtering && !section.querySelector("[data-gallery-card]:not([hidden])");
      });
      count.textContent = visible === cards.length
        ? "Showing all " + visible + " ideas"
        : "Showing " + visible + " of " + cards.length + " ideas";
      empty.hidden = visible !== 0;
      syncControls();
    }

    function controlsState() {
      var next = defaultState();
      next.view = state.view;
      next.q = search.value.trim();
      filters.forEach(function (input) {
        if (input.checked) next.facets[input.name].push(input.value);
      });
      return next;
    }

    viewButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        state.view = button.dataset.galleryView;
        writeUrl("push");
        render();
      });
    });
    presetButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        state = presetState(button.dataset.galleryPreset);
        writeUrl("push");
        render();
      });
    });
    filters.forEach(function (input) {
      input.addEventListener("change", function () {
        state = controlsState();
        writeUrl("push");
        render();
      });
    });
    search.addEventListener("input", function () {
      var next = controlsState();
      next.preset = state.preset;
      next.minimumAllowed = state.minimumAllowed;
      state = next;
      writeUrl("replace");
      render();
    });
    root.querySelectorAll("[data-gallery-clear]").forEach(function (button) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        state = defaultState();
        writeUrl("push");
        render();
        search.focus();
      });
    });
    global.addEventListener("popstate", function () {
      state = parseQuery(global.location.search);
      render();
    });
    render();
  }

  var api = {
    parseQuery: parseQuery,
    serializeState: serializeState,
    matchesCard: matchesCard,
    presetState: presetState,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document !== "undefined") initialize();
})(typeof window !== "undefined" ? window : globalThis);
