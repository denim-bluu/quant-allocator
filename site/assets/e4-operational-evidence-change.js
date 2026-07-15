(function () {
  "use strict";

  var dataNode = document.getElementById("card-data");
  if (!dataNode) return;
  var data = JSON.parse(dataNode.textContent);
  var controls = {
    cutoff: document.querySelectorAll("[data-e4-cutoff-control]"),
    source: document.querySelectorAll("[data-e4-source-control]"),
    domain: document.querySelector("[data-e4-domain-control]"),
    state: document.querySelector("[data-e4-state-control]")
  };
  var selected = {
    cutoff: "latest",
    source: "all-entitled",
    domain: "all",
    state: "all"
  };

  var cutoffLabels = {
    early: "First evidence cutoff",
    middle: "Interim evidence cutoff",
    latest: "Latest evidence cutoff"
  };
  var sourceLabels = {
    "public-only": "Public sources only",
    "all-entitled": "All permitted sources"
  };
  var domainLabels = {
    organisation: "investment-team",
    process: "process",
    control: "control",
    provider: "fund-administrator",
    incident: "incident"
  };
  var actionLabels = {
    "immediate-clarification": "Clarify now",
    "scheduled-reunderwrite": "Schedule review",
    "evidence-refresh": "Refresh evidence",
    "no-action-from-e4": "No new action"
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
  }

  function stateKey() { return selected.cutoff + "|" + selected.source; }

  function displayKey() {
    return selected.domain + "|" + selected.state + "|timeline";
  }

  function writeUrl(replace) {
    var query = new URLSearchParams();
    query.set("cutoff", selected.cutoff);
    query.set("source", selected.source);
    query.set("domain", selected.domain);
    query.set("state", selected.state);
    var method = replace ? "replaceState" : "pushState";
    window.history[method](null, "", window.location.pathname + "?" + query.toString());
  }

  function membershipSet(values) {
    var result = Object.create(null);
    values.forEach(function (value) { result[value] = true; });
    return result;
  }

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

  function queueQuestion(row) {
    if (row.action_bucket === "immediate-clarification") {
      if (row.domain === "incident") return "Clarify the NAV-publication incident and its materiality.";
      if (row.domain === "provider") return "Clarify conflicting evidence about the fund administrator.";
      return "Clarify conflicting evidence about the investment team.";
    }
    if (row.action_bucket === "scheduled-reunderwrite") {
      return "Re-underwrite the dated " + domainLabels[row.domain] + " change.";
    }
    if (row.action_bucket === "evidence-refresh") {
      return "Request current " + domainLabels[row.domain] + " evidence.";
    }
    return "No new action follows from this evidence.";
  }

  function renderQueue(key, visibleIds) {
    var visible = membershipSet(visibleIds);
    var rows = data.reunderwriting_queue[key].filter(function (row) {
      return visible[row.queue_id];
    }).map(function (row) {
      var article = document.createElement("article");
      article.dataset.e4QueueId = row.queue_id;
      article.dataset.domain = row.domain;
      var chip = document.createElement("span");
      chip.className = "e4-state";
      chip.dataset.state = row.action_bucket;
      chip.textContent = actionLabels[row.action_bucket];
      var question = document.createElement("p");
      question.textContent = queueQuestion(row);
      article.appendChild(chip);
      article.appendChild(question);
      return article;
    });
    replaceChildren(document.querySelector("[data-e4-queue]"), rows);
    document.querySelector("[data-e4-action-count]").textContent = rows.length;
  }

  function render() {
    var key = stateKey();
    var interaction = data.interaction_states[key];
    var display = interaction.visible_id_sets[displayKey()];
    var facts = membershipSet(display.fact_ids);
    var changes = membershipSet(display.change_ids);
    var factStates = stateByFact(key);

    document.documentElement.dataset.e4Enhanced = "true";
    document.querySelector("[data-e4-cutoff]").textContent = cutoffLabels[selected.cutoff];
    document.querySelector("[data-e4-source-view]").textContent = sourceLabels[selected.source];
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
      chip.textContent = evidenceState === "asserted" ? "Single-source assertion" :
        (evidenceState === "conflicted" ? "Conflicting evidence" :
          (evidenceState === "stale" ? "Needs refresh" :
            (evidenceState === "corroborated" ? "Corroborated" : "Policy evidence")));
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-e4-change-id]"), function (row) {
      row.hidden = !changes[row.dataset.e4ChangeId];
    });
    renderQueue(key, display.queue_ids);
    document.querySelector("[data-e4-empty]").hidden = !display.empty;
    syncPressed(controls.cutoff, "data-e4-cutoff-control", selected.cutoff);
    syncPressed(controls.source, "data-e4-source-control", selected.source);
    controls.domain.value = selected.domain;
    controls.state.value = selected.state;
    document.querySelector("[data-e4-announcer]").textContent =
      "Showing the " + cutoffLabels[selected.cutoff].toLowerCase() + " using " +
      sourceLabels[selected.source].toLowerCase() + ".";
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
  controls.domain.addEventListener("change", function () {
    selected.domain = this.value;
    writeUrl(false);
    render();
  });
  controls.state.addEventListener("change", function () {
    selected.state = this.value;
    writeUrl(false);
    render();
  });
  document.querySelector("[data-e4-reset]").addEventListener("click", function () {
    selected = {cutoff: "latest", source: "all-entitled", domain: "all", state: "all"};
    writeUrl(false);
    render();
  });
  window.addEventListener("popstate", function () { readUrl(); render(); });
  readUrl();
  writeUrl(true);
  render();
})();
