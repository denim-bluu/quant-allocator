(function () {
  "use strict";

  var dataNode = document.getElementById("card-data");
  if (!dataNode) return;
  var data = JSON.parse(dataNode.textContent);
  var controls = {
    cutoff: document.querySelectorAll("[data-e4-cutoff-control]"),
    source: document.querySelectorAll("[data-e4-source-control]"),
    panel: document.querySelectorAll("[data-e4-panel-control]"),
    domain: document.querySelector("[data-e4-domain-control]"),
    state: document.querySelector("[data-e4-state-control]")
  };
  var selected = {
    cutoff: "latest",
    source: "all-entitled",
    domain: "all",
    state: "all",
    panel: "timeline"
  };

  function allowed(value, values, fallback) {
    return values.indexOf(value) >= 0 ? value : fallback;
  }

  function readUrl() {
    var query = new URLSearchParams(window.location.search);
    selected.cutoff = allowed(query.get("cutoff"), ["early", "middle", "latest"], "latest");
    selected.source = allowed(query.get("source"), ["public-only", "all-entitled"], "all-entitled");
    selected.domain = allowed(query.get("domain"), ["all", "organisation", "process", "control", "provider", "incident"], "all");
    selected.state = allowed(query.get("state"), ["all", "corroborated", "asserted", "conflicted", "stale"], "all");
    selected.panel = allowed(query.get("view"), ["timeline", "graph", "table"], "timeline");
  }

  function stateKey() { return selected.cutoff + "|" + selected.source; }

  function displayKey() {
    return selected.domain + "|" + selected.state + "|" + selected.panel;
  }

  function writeUrl(replace) {
    var query = new URLSearchParams();
    query.set("cutoff", selected.cutoff);
    query.set("source", selected.source);
    query.set("domain", selected.domain);
    query.set("state", selected.state);
    query.set("view", selected.panel);
    var method = replace ? "replaceState" : "pushState";
    window.history[method](null, "", window.location.pathname + "?" + query.toString());
  }

  function membershipSet(values) {
    var result = Object.create(null);
    values.forEach(function (value) { result[value] = true; });
    return result;
  }

  function catalogById(rows, field) {
    var result = Object.create(null);
    rows.forEach(function (row) { result[row[field]] = row; });
    return result;
  }

  var factsById = catalogById(data.facts, "fact_id");
  var changesById = catalogById(data.changes, "change_id");
  var relationshipsById = catalogById(data.relationships, "relationship_id");
  var refusalsById = catalogById(data.refusals.data_boundary, "refusal_id");

  function stateByFact(key) {
    var result = Object.create(null);
    data.state_summary[key].forEach(function (row) {
      row.supporting_fact_ids.concat(row.conflicting_fact_ids).forEach(function (id) {
        result[id] = row.state;
      });
    });
    return result;
  }

  function syncPressed(nodes, attribute, value) {
    Array.prototype.forEach.call(nodes, function (node) {
      node.setAttribute("aria-pressed", String(node.getAttribute(attribute) === value));
    });
  }

  function replaceChildren(container, children) {
    while (container.firstChild) container.removeChild(container.firstChild);
    children.forEach(function (child) { container.appendChild(child); });
  }

  function receipt(row, key) {
    return row.receipt_ids_by_state[key] || "";
  }

  function renderStateReceipts(key) {
    var rows = data.state_summary[key].map(function (row) {
      var article = document.createElement("article");
      article.dataset.e4StateId = row.state_id;
      var chip = document.createElement("span");
      chip.className = "e4-state";
      chip.dataset.state = row.state;
      chip.textContent = row.state;
      var label = document.createElement("span");
      label.textContent = row.fact_key[1] + " · " + row.fact_key[2];
      var code = document.createElement("code");
      code.textContent = row.receipt_id;
      article.appendChild(chip);
      article.appendChild(label);
      article.appendChild(code);
      return article;
    });
    replaceChildren(document.querySelector("[data-e4-state-receipts]"), rows);
  }

  function renderQueue(key, visibleIds) {
    var visible = membershipSet(visibleIds);
    var rows = data.reunderwriting_queue[key].filter(function (row) {
      return visible[row.queue_id];
    }).map(function (row) {
      var details = document.createElement("details");
      details.dataset.e4QueueId = row.queue_id;
      details.dataset.domain = row.domain;
      var summary = document.createElement("summary");
      var chip = document.createElement("span");
      chip.className = "e4-state";
      chip.dataset.state = row.action_bucket;
      chip.textContent = row.action_bucket;
      summary.appendChild(chip);
      summary.appendChild(document.createTextNode(" " + row.question));
      details.appendChild(summary);
      var reason = document.createElement("p");
      reason.textContent = row.reason_codes.join(", ");
      details.appendChild(reason);
      var code = document.createElement("code");
      code.textContent = receipt(row, key);
      details.appendChild(code);
      return details;
    });
    replaceChildren(document.querySelector("[data-e4-queue]"), rows);
  }

  function renderRefusals(key, refusalIds) {
    var rows = refusalIds.map(function (id) {
      var row = refusalsById[id];
      var article = document.createElement("article");
      article.dataset.e4RefusalId = id;
      var reason = document.createElement("strong");
      reason.textContent = row.reason_code;
      var pointer = document.createElement("span");
      pointer.textContent = row.output_pointer;
      var code = document.createElement("code");
      code.textContent = receipt(row, key);
      article.appendChild(reason);
      article.appendChild(pointer);
      article.appendChild(code);
      return article;
    });
    replaceChildren(document.querySelector("[data-e4-refusal-list]"), rows);
    document.querySelector("[data-e4-method-receipt]").textContent =
      receipt(data.refusals.method_boundary, key);
  }

  function render() {
    var key = stateKey();
    var interaction = data.interaction_states[key];
    var display = interaction.visible_id_sets[displayKey()];
    var facts = membershipSet(display.fact_ids);
    var changes = membershipSet(display.change_ids);
    var relationships = membershipSet(display.relationship_ids);
    var factStates = stateByFact(key);

    document.documentElement.dataset.e4Enhanced = "true";
    document.querySelector("[data-e4-cutoff]").textContent = selected.cutoff;
    document.querySelector("[data-e4-source-view]").textContent = selected.source;
    ["corroborated", "asserted", "conflicted", "stale"].forEach(function (name) {
      document.querySelector('[data-e4-count="' + name + '"]').textContent = interaction.state_counts[name] || 0;
    });
    document.querySelector('[data-e4-count="refused"]').textContent = interaction.refusal_count;
    document.querySelector("[data-e4-refusal-count]").textContent = interaction.data_boundary_refusal_ids.length;

    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-fact-id]"), function (row) {
      var id = row.dataset.e4FactId;
      var evidenceState = factStates[id] || "";
      row.hidden = !facts[id];
      row.dataset.evidenceState = evidenceState;
      var chip = row.querySelector(".e4-state");
      chip.dataset.state = evidenceState;
      chip.textContent = evidenceState || "policy evidence";
      row.querySelector("code").textContent = receipt(factsById[id], key);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-change-id]"), function (row) {
      var id = row.dataset.e4ChangeId;
      row.hidden = !changes[id];
      row.querySelector("code").textContent = receipt(changesById[id], key);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-relationship-id]"), function (row) {
      var id = row.dataset.e4RelationshipId;
      row.hidden = !relationships[id];
      row.querySelector("code").textContent = receipt(relationshipsById[id], key);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-relationship-row-id]"), function (row) {
      var id = row.dataset.e4RelationshipRowId;
      row.hidden = !relationships[id];
      row.querySelector("code").textContent = receipt(relationshipsById[id], key);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-panel]"), function (panel) {
      if (panel.dataset.e4Panel) panel.hidden = panel.dataset.e4Panel !== selected.panel;
    });
    renderStateReceipts(key);
    renderQueue(key, display.queue_ids);
    renderRefusals(key, interaction.data_boundary_refusal_ids);
    document.querySelector("[data-e4-empty]").hidden = !display.empty;
    syncPressed(controls.cutoff, "data-e4-cutoff-control", selected.cutoff);
    syncPressed(controls.source, "data-e4-source-control", selected.source);
    syncPressed(controls.panel, "data-e4-panel-control", selected.panel);
    controls.domain.value = selected.domain;
    controls.state.value = selected.state;
    document.querySelector("[data-e4-announcer]").textContent =
      "Showing " + key + ", domain " + selected.domain + ", state " + selected.state + ", " + selected.panel + " view.";
  }

  function bindButtons(nodes, attribute, field) {
    Array.prototype.forEach.call(nodes, function (node) {
      node.addEventListener("click", function () {
        selected[field] = node.getAttribute(attribute);
        writeUrl(false);
        render();
      });
    });
  }

  bindButtons(controls.cutoff, "data-e4-cutoff-control", "cutoff");
  bindButtons(controls.source, "data-e4-source-control", "source");
  bindButtons(controls.panel, "data-e4-panel-control", "panel");
  controls.domain.addEventListener("change", function () { selected.domain = this.value; writeUrl(false); render(); });
  controls.state.addEventListener("change", function () { selected.state = this.value; writeUrl(false); render(); });
  document.querySelector("[data-e4-reset]").addEventListener("click", function () {
    selected = {cutoff: "latest", source: "all-entitled", domain: "all", state: "all", panel: "timeline"};
    writeUrl(false);
    render();
  });
  window.addEventListener("popstate", function () { readUrl(); render(); });
  readUrl();
  writeUrl(true);
  render();
})();
