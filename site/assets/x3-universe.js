(() => {
  const payload = document.getElementById("card-data");
  const cutoff = document.getElementById("x3-cutoff");
  const source = document.getElementById("x3-source");
  const scope = document.getElementById("x3-scope");
  if (!payload || !cutoff || !source || !scope) return;
  const data = JSON.parse(payload.textContent);
  const defaults = data.meta.default_state.split("|");
  const controls = [cutoff, source, scope];

  const setText = (name, value) => {
    const slot = document.querySelector(`[data-x3="${name}"]`);
    if (slot) slot.textContent = String(value);
  };
  const rows = (target, values, render) => {
    const body = document.getElementById(target);
    if (!body) return;
    body.replaceChildren(...values.map(render));
  };
  const tableRow = (values) => {
    const tr = document.createElement("tr");
    values.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = String(value ?? "");
      tr.appendChild(td);
    });
    return tr;
  };
  const listItem = (text) => {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
  };

  const render = (state, stateKey, announce) => {
    setText("source-rows", state.source_counts.source_rows);
    setText("canonical-members", state.source_counts.canonical_members);
    setText("eligible-cells", state.target_grid.eligible_cells);
    setText("excluded-cells", state.target_grid.excluded_cells);
    setText("denominator", state.denominator_label);
    document.getElementById("x3-visual").dataset.stateKey = stateKey;
    rows("x3-receipts", Object.entries(state.slice_receipts), ([datasetId, receiptId]) => tableRow([datasetId, receiptId]));
    rows("x3-exclusions", state.target_grid.excluded_ledger, (row) => tableRow([row.cell_id, row.state, row.reason]));
    rows("x3-refusals", state.refusals, (row) => listItem(`${row.pointer} · ${row.code} — ${row.detail}`));
    rows("x3-funnel-counts", state.funnel.stage_counts, (row) => listItem(`${row.cohort_label}: ${row.entry_count} entry / ${row.outcome_count} outcome`));
    document.getElementById("x3-live").textContent = `Showing ${stateKey}.`;
  };

  const selectState = (announce, preserveFocus) => {
    const stateKey = `${cutoff.value}|${source.value}|${scope.value}`;
    const state = data.states[stateKey];
    const unsupported = document.getElementById("x3-unsupported");
    if (!state) {
      controls.forEach((control, index) => { control.value = defaults[index]; });
      unsupported.textContent = "unsupported-state-key: restored the complete server default.";
      unsupported.hidden = false;
      render(data.states[data.meta.default_state], data.meta.default_state, announce);
      return;
    }
    unsupported.hidden = true;
    render(state, stateKey, announce);
    const params = new URLSearchParams(location.search);
    params.set("cutoff", cutoff.value); params.set("source", source.value); params.set("scope", scope.value);
    const nextUrl = `${location.pathname}?${params.toString()}`;
    if (announce) history.pushState({}, "", nextUrl);
    else history.replaceState({}, "", nextUrl);
    if (preserveFocus) preserveFocus.focus();
  };

  const restore = () => {
    const params = new URLSearchParams(location.search);
    cutoff.value = params.get("cutoff") || defaults[0];
    source.value = params.get("source") || defaults[1];
    scope.value = params.get("scope") || defaults[2];
    selectState(false, null);
  };
  controls.forEach((control) => control.addEventListener("change", () => selectState(true, control)));
  window.addEventListener("popstate", restore);
  restore();
})();
