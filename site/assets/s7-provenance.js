(function () {
  "use strict";

  var dataNode = document.getElementById("card-data");
  if (!dataNode) return;

  var data = JSON.parse(dataNode.textContent);
  var defaultTokens = data.meta.default_state.split("|");
  var defaults = {
    scenario: defaultTokens[0],
    cutoff: defaultTokens[1],
    view: defaultTokens[2]
  };
  var selected = {scenario: defaults.scenario, cutoff: defaults.cutoff, view: defaults.view};
  var scenarioControls = document.querySelectorAll("[data-s7-scenario-control]");
  var cutoffControls = document.querySelectorAll("[data-s7-cutoff-control]");
  var viewControls = document.querySelectorAll("[data-s7-view-control]");
  var notice = document.querySelector("[data-s7-notice]");

  var viewLabels = {
    lineage: "Lineage",
    basis: "Comparability",
    audit: "Revision history"
  };
  var reasonLabels = {
    "fee-basis-incomparable": "reported fee bases are not comparable",
    "frequency-calendar-incomparable": "frequencies and calendars are not comparable",
    "entity-mapping-ambiguous": "the observation cannot be attached to one entity",
    "entity-mapping-unresolved": "the entity owner has not been resolved",
    "lineage-overlap": "two lineage intervals overlap",
    unmatched: "no supported lineage match is available"
  };

  function keyFor(selection) {
    return `${selection.scenario}|${selection.cutoff}|${selection.view}`;
  }

  function exactState(selection) {
    var key = keyFor(selection);
    return data.states[key] || null;
  }

  function restoreDefault(reason) {
    selected = {scenario: defaults.scenario, cutoff: defaults.cutoff, view: defaults.view};
    notice.hidden = !reason;
    notice.textContent = reason || "";
  }

  function readUrl() {
    var query = new URLSearchParams(window.location.search);
    var candidate = {
      scenario: query.get("scenario") || defaults.scenario,
      cutoff: query.get("cutoff") || defaults.cutoff,
      view: query.get("view") || defaults.view
    };
    if (!exactState(candidate)) {
      restoreDefault("That combination is unavailable, so the opening example has been restored.");
      return false;
    }
    selected = candidate;
    notice.hidden = true;
    notice.textContent = "";
    return true;
  }

  function writeUrl(replace) {
    var query = new URLSearchParams();
    query.set("scenario", selected.scenario);
    query.set("cutoff", selected.cutoff);
    query.set("view", selected.view);
    var method = replace ? "replaceState" : "pushState";
    window.history[method](null, "", `${window.location.pathname}?${query.toString()}`);
  }

  function syncPressed(nodes, attribute, value) {
    Array.prototype.forEach.call(nodes, function (node) {
      node.setAttribute("aria-pressed", String(node.getAttribute(attribute) === value));
    });
  }

  function clear(node) {
    node.replaceChildren();
  }

  function metric(label, value) {
    var article = document.createElement("article");
    var name = document.createElement("span");
    var amount = document.createElement("strong");
    name.textContent = label;
    amount.textContent = String(value);
    article.appendChild(name);
    article.appendChild(amount);
    return article;
  }

  function paragraph(text) {
    var node = document.createElement("p");
    node.textContent = text;
    return node;
  }

  function readableReason(code) {
    return reasonLabels[code] || "the required evidence is incomplete";
  }

  function renderLineage(state, body) {
    var attached = state.lineage_segments.length
      ? state.lineage_segments[0].observation_ids.length
      : 0;
    body.appendChild(metric("Exact lineage segments", state.lineage_segments.length));
    body.appendChild(metric("Records attached to the lineage", attached));
    body.appendChild(metric("Records kept outside", state.exclusions.length));
    body.appendChild(paragraph(state.what_changed));
  }

  function renderBasis(state, body) {
    var panel = state.panel;
    var status = panel.status === "admitted" ? "Admitted" : "Refused";
    body.appendChild(metric("Panel decision", status));
    body.appendChild(metric("Comparable source observations", panel.rows.length));
    body.appendChild(metric("Basis breaks", state.basis_breaks.length));
    if (state.basis_breaks.length) {
      body.appendChild(paragraph(`Primary reason: ${readableReason(state.basis_breaks[0].binding_reason)}.`));
    } else {
      body.appendChild(paragraph("No controlled basis break is present in this state."));
    }
  }

  function renderAudit(state, body) {
    body.appendChild(metric("Version changes found", state.vintage_findings.length));
    if (!state.vintage_findings.length) {
      body.appendChild(paragraph("No later version is visible at this decision date."));
      return;
    }
    state.vintage_findings.forEach(function (item) {
      var effective = item.effective_at ? item.effective_at.slice(0, 10) : "dataset-level change";
      var known = item.first_known_at.slice(0, 10);
      body.appendChild(paragraph(`Effective ${effective}; first known ${known}.`));
    });
  }

  function render() {
    var active = document.activeElement;
    var key = keyFor(selected);
    var state = data.states[key];
    var scenario = data.scenarios[state.scenario];
    var cutoff = selected.cutoff === "early" ? "earlier decision date" : "later decision date";
    var view = viewLabels[selected.view];
    var body = document.querySelector("[data-s7-explorer-body]");

    document.querySelector("[data-s7-scenario-label]").textContent = scenario.label;
    document.querySelector("[data-s7-view-label]").textContent = view;
    document.querySelector("[data-s7-explorer-summary]").textContent = state.conclusion;
    clear(body);
    if (selected.view === "lineage") renderLineage(state, body);
    if (selected.view === "basis") renderBasis(state, body);
    if (selected.view === "audit") renderAudit(state, body);

    syncPressed(scenarioControls, "data-s7-scenario-control", selected.scenario);
    syncPressed(cutoffControls, "data-s7-cutoff-control", selected.cutoff);
    syncPressed(viewControls, "data-s7-view-control", selected.view);
    document.querySelector("[data-s7-announcer]").textContent =
      `Showing the ${scenario.label.toLowerCase()} at the ${cutoff}, with the ${view.toLowerCase()} view.`;
    if (active && active.matches("[data-s7-scenario-control], [data-s7-cutoff-control], [data-s7-view-control]")) {
      active.focus();
    }
  }

  function bind(nodes, attribute, field) {
    Array.prototype.forEach.call(nodes, function (node) {
      node.addEventListener("click", function () {
        selected[field] = node.getAttribute(attribute);
        notice.hidden = true;
        notice.textContent = "";
        writeUrl(false);
        render();
      });
    });
  }

  bind(scenarioControls, "data-s7-scenario-control", "scenario");
  bind(cutoffControls, "data-s7-cutoff-control", "cutoff");
  bind(viewControls, "data-s7-view-control", "view");
  window.addEventListener("popstate", function () {
    var valid = readUrl();
    writeUrl(true);
    render();
    if (!valid) notice.hidden = false;
  });

  var validInitial = readUrl();
  writeUrl(true);
  render();
  if (!validInitial) notice.hidden = false;
})();
