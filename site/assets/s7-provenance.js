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

  function keyFor(selection) {
    return `${selection.scenario}|${selection.cutoff}|${selection.view}`;
  }

  function exactState(selection) {
    return data.states[keyFor(selection)] || null;
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
      restoreDefault(`unsupported-state-key: restored ${data.meta.default_state}`);
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

  function textCell(value) {
    var cell = document.createElement("td");
    cell.textContent = value === null || value === undefined || value === "" ? "not available" : String(value);
    return cell;
  }

  function codeCell(value) {
    var cell = document.createElement("td");
    var code = document.createElement("code");
    code.textContent = value === null || value === undefined || value === "" ? "none" : String(value);
    cell.appendChild(code);
    return cell;
  }

  function chipCell(value) {
    var cell = document.createElement("td");
    var chip = document.createElement("span");
    chip.className = "s7-chip";
    chip.dataset.state = value;
    chip.textContent = value;
    cell.appendChild(chip);
    return cell;
  }

  function emptyRow(body, span, message) {
    var row = document.createElement("tr");
    var cell = document.createElement("td");
    cell.colSpan = span;
    cell.textContent = message;
    row.appendChild(cell);
    body.appendChild(row);
  }

  function renderLineage(state) {
    var body = document.querySelector("[data-s7-lineage-body]");
    clear(body);
    if (!state.lineage_segments.length) {
      emptyRow(body, 5, "No lineage segment is admitted in this state.");
    }
    state.lineage_segments.forEach(function (item) {
      var row = document.createElement("tr");
      row.dataset.s7LineageRow = item.segment_id;
      row.appendChild(codeCell(item.canonical_entity_id));
      row.appendChild(textCell(item.entity_grain));
      row.appendChild(textCell(`${item.effective_from} to ${item.effective_to}`));
      row.appendChild(textCell(item.observation_ids.length));
      row.appendChild(textCell(
        `${item.mapping_ids.length} mappings; ${item.membership_ids.length} memberships; ${item.relationship_ids.length} relationships`
      ));
      body.appendChild(row);
    });

    var portability = document.querySelector("[data-s7-portability-body]");
    clear(portability);
    if (!state.portability_findings.length) {
      emptyRow(portability, 6, "Not assessed: no authenticated scenario portability bundle.");
    }
    state.portability_findings.forEach(function (item) {
      var row = document.createElement("tr");
      row.dataset.s7PortabilityRow = item.finding_id;
      row.appendChild(chipCell(item.state));
      row.appendChild(textCell(`${item.predecessor_entity_id || "not established"} to ${item.current_entity_id || "not established"}`));
      row.appendChild(textCell(item.claimed_scope || "not established"));
      row.appendChild(textCell(`${item.missing_evidence}; ${item.reason_codes}`));
      row.appendChild(textCell(`Current ${item.current_attestation}; live ceiling ${item.live_attestation_ceiling}`));
      row.appendChild(codeCell(item.receipt_id));
      portability.appendChild(row);
    });
  }

  function renderBasis(state) {
    var breaks = document.querySelector("[data-s7-break-body]");
    clear(breaks);
    if (!state.basis_breaks.length) {
      emptyRow(breaks, 5, "No derived basis break is present in this state.");
    }
    state.basis_breaks.forEach(function (item) {
      var row = document.createElement("tr");
      row.dataset.s7BreakRow = item.receipt_id;
      row.appendChild(chipCell(item.disposition));
      row.appendChild(textCell(item.binding_reason));
      row.appendChild(textCell(item.reason_codes));
      row.appendChild(textCell(item.row_ids.length));
      row.appendChild(codeCell(item.receipt_id));
      breaks.appendChild(row);
    });

    var panel = state.panel;
    var summary = document.querySelector("[data-s7-panel-summary]");
    clear(summary);
    var status = document.createElement("span");
    status.className = "s7-chip";
    status.dataset.state = panel.status;
    status.textContent = panel.status;
    summary.appendChild(status);
    var description = panel.status === "admitted"
      ? ` ${panel.panel_kind}; ${panel.native_frequency}; ${panel.canonical_entity_id}.`
      : ` ${panel.reason_code}.`;
    summary.appendChild(document.createTextNode(description));

    var signatureBody = document.querySelector("[data-s7-basis-signature-body]");
    clear(signatureBody);
    if (panel.status !== "admitted") {
      emptyRow(signatureBody, 2, "Unavailable because the panel is refused; see the controlled reasons above.");
    } else {
      [
        "base_currency",
        "benchmark_id",
        "benchmark_return_kind",
        "benchmark_version",
        "calendar_id",
        "cashflow_convention_id",
        "composite_definition_id",
        "composite_membership_version",
        "entity_grain",
        "fee_schedule_version",
        "frequency",
        "fx_rule_id",
        "fx_series_id",
        "fx_series_version",
        "fx_treatment",
        "gross_net_fee_basis",
        "return_kind",
        "valuation_policy_id"
      ].forEach(function (field) {
        var row = document.createElement("tr");
        row.appendChild(codeCell(field));
        row.appendChild(textCell(panel.basis_signature[field] === null ? "not applicable" : panel.basis_signature[field]));
        signatureBody.appendChild(row);
      });
    }

    var panelBody = document.querySelector("[data-s7-panel-body]");
    clear(panelBody);
    if (panel.status !== "admitted") {
      emptyRow(panelBody, 5, `Panel refused: ${panel.reason_codes}. No empty chart is shown.`);
    } else {
      panel.rows.forEach(function (item) {
        var row = document.createElement("tr");
        row.dataset.s7PanelRow = item.observation_id;
        row.appendChild(textCell(item.observed_at));
        row.appendChild(codeCell(item.observation_id));
        row.appendChild(textCell(`${item.source_value} source observation`));
        row.appendChild(textCell(`${item.admitted_value} deterministic admitted value, not an estimate`));
        row.appendChild(codeCell(item.fx_observation_id));
        panelBody.appendChild(row);
      });
    }
    document.querySelector("[data-s7-panel-receipt]").textContent = panel.receipt_id;
  }

  function renderAudit(state) {
    document.querySelector("[data-s7-analytic-mode]").textContent = state.revision_modes.analytic;
    document.querySelector("[data-s7-audit-mode]").textContent = state.revision_modes.audit;
    var vintages = document.querySelector("[data-s7-vintage-body]");
    clear(vintages);
    if (!state.vintage_findings.length) {
      emptyRow(vintages, 6, "No vintage finding is emitted at this cutoff.");
    }
    state.vintage_findings.forEach(function (item) {
      var row = document.createElement("tr");
      row.dataset.s7VintageRow = item.finding_id;
      row.appendChild(chipCell(item.finding_type));
      row.appendChild(codeCell(item.dataset_id));
      row.appendChild(textCell(item.effective_at || "dataset-level"));
      row.appendChild(textCell(item.first_known_at));
      row.appendChild(textCell(item.prior_value === undefined ? "not applicable" : `${item.prior_value || "none"} to ${item.later_value || "none"}`));
      row.appendChild(codeCell(item.receipt_id));
      vintages.appendChild(row);
    });

    var exclusions = document.querySelector("[data-s7-exclusion-body]");
    clear(exclusions);
    if (!state.exclusions.length) {
      emptyRow(exclusions, 4, "No typed exclusion is present.");
    }
    state.exclusions.forEach(function (item) {
      var row = document.createElement("tr");
      row.dataset.s7ExclusionRow = item.observation_id;
      row.appendChild(codeCell(item.observation_id));
      row.appendChild(codeCell(item.dataset_id));
      row.appendChild(textCell(item.reason_code));
      row.appendChild(textCell(item.source));
      exclusions.appendChild(row);
    });
  }

  function renderRefusals(state) {
    var container = document.querySelector("[data-s7-refusal-list]");
    clear(container);
    state.refusals.forEach(function (item) {
      var article = document.createElement("article");
      article.dataset.s7Refusal = "";
      var chip = document.createElement("span");
      chip.className = "s7-chip";
      chip.dataset.state = "refused";
      chip.textContent = item.reason_code;
      var pointer = document.createElement("code");
      pointer.textContent = item.pointer;
      var receipt = document.createElement("code");
      receipt.textContent = item.receipt_id;
      article.appendChild(chip);
      article.appendChild(pointer);
      article.appendChild(receipt);
      if (item.detail) {
        var detail = document.createElement("p");
        detail.textContent = item.detail;
        article.appendChild(detail);
      }
      container.appendChild(article);
    });
  }

  function renderReceipts(state) {
    document.querySelector("[data-s7-analytic-bundle]").textContent = state.analytic_bundle_digest;
    document.querySelector("[data-s7-analytic-join]").textContent = state.join_receipt_ids.analytic;
    document.querySelector("[data-s7-audit-bundle]").textContent = state.audit_bundle_digest;
    document.querySelector("[data-s7-audit-join]").textContent = state.join_receipt_ids.audit;
    var list = document.querySelector("[data-s7-receipt-list]");
    clear(list);
    state.receipt_ids.forEach(function (receiptId) {
      var item = document.createElement("li");
      var code = document.createElement("code");
      code.textContent = receiptId;
      item.appendChild(code);
      list.appendChild(item);
    });
  }

  function renderClaims(key) {
    Object.keys(data.claims).forEach(function (claimId) {
      var claim = data.claims[claimId];
      document.querySelector(`[data-s7-claim-applicable="${claimId}"]`).textContent =
        claim.applicable_by_state[key] ? "yes" : "no";
      var receiptIds = claim.receipt_ids_by_state[key];
      document.querySelector(`[data-s7-claim-receipts="${claimId}"]`).textContent =
        receiptIds.length ? String(receiptIds) : "none";
    });
  }

  function render() {
    var active = document.activeElement;
    var key = keyFor(selected);
    var state = data.states[key];
    var scenario = data.scenarios[state.scenario];

    document.documentElement.dataset.s7Enhanced = "true";
    document.querySelector("[data-s7-state-key]").textContent = key;
    document.querySelector("[data-s7-decision-at]").textContent = state.decision_at;
    document.querySelector("[data-s7-conclusion]").textContent = state.conclusion;
    document.querySelector("[data-s7-limitation]").textContent = state.limitation;
    document.querySelector("[data-s7-what-changed]").textContent = state.what_changed;
    document.querySelector("[data-s7-scenario-label]").textContent = scenario.label;
    document.querySelector("[data-s7-source-shape]").textContent = scenario.source_shape;
    document.querySelector("[data-s7-minimum-data]").textContent = String(scenario.minimum_data);
    document.querySelector("[data-s7-portability-scope]").textContent = scenario.portability_scope;
    document.querySelector("[data-s7-access-contexts]").textContent = String(state.access_contexts);

    renderLineage(state);
    renderBasis(state);
    renderAudit(state);
    renderRefusals(state);
    renderReceipts(state);
    renderClaims(key);

    Array.prototype.forEach.call(document.querySelectorAll("[data-s7-view-panel]"), function (panel) {
      panel.hidden = panel.dataset.s7ViewPanel !== selected.view;
    });
    syncPressed(scenarioControls, "data-s7-scenario-control", selected.scenario);
    syncPressed(cutoffControls, "data-s7-cutoff-control", selected.cutoff);
    syncPressed(viewControls, "data-s7-view-control", selected.view);
    document.querySelector("[data-s7-announcer]").textContent =
      `Showing ${key}. ${state.conclusion}`;
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
