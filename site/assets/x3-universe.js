(() => {
  const payload = document.getElementById("card-data");
  const cutoff = document.getElementById("x3-cutoff");
  const source = document.getElementById("x3-source");
  const scope = document.getElementById("x3-scope");
  if (!payload || !cutoff || !source || !scope) return;

  const data = JSON.parse(payload.textContent);
  const defaults = data.meta.default_state.split("|");
  const controls = [cutoff, source, scope];
  const cutoffLabels = {
    early: "early evidence",
    middle: "intermediate evidence",
    latest: "latest available evidence"
  };
  const sourceLabels = {
    "public-only": "public records only",
    "public-plus-prehire": "public records plus pre-hire submissions",
    "full-synthetic-funnel": "the full synthetic sourcing funnel"
  };
  const scopeLabels = {
    "cross-asset": "cross-asset research map",
    "liquid-public-markets": "liquid public-markets map",
    "credit-private-markets": "credit and private-markets map"
  };
  const sourceNames = {
    "dataset:x3-holdings-filer": "Holdings filer records",
    "dataset:x3-public-adviser": "Public adviser records",
    "dataset:x3-registered-fund": "Registered fund records",
    "dataset:x3-rfi-ddq": "RFI and DDQ responses",
    "dataset:x3-strategy-export": "Strategy export",
    "dataset:x3-target-grid": "Allocator target grid"
  };
  const cohortLabels = {
    "x3-discovered-to-screen": "Discovered to screened",
    "x3-diligence-to-approved": "Diligence to approved"
  };

  const setText = (name, value) => {
    const slot = document.querySelector(`[data-x3="${name}"]`);
    if (slot) slot.textContent = String(value);
  };

  const listItem = (text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  };

  const replaceList = (target, items) => {
    target.replaceChildren(...items);
  };

  const render = (state, stateKey) => {
    setText("source-rows", state.source_counts.source_rows);
    setText("canonical-members", state.source_counts.canonical_members);
    setText("ambiguous-rows", state.source_counts.ambiguous_rows);
    setText("eligible-cells", state.target_grid.eligible_cells);
    setText("excluded-cells", state.target_grid.excluded_cells);
    document.getElementById("x3-visual").dataset.stateKey = stateKey;

    const selectedSources = Object.keys(state.slice_receipts)
      .filter((key) => key !== "dataset:x3-target-grid")
      .map((key) => listItem(sourceNames[key] || "Named source record"));
    replaceList(document.getElementById("x3-source-list"), selectedSources);

    const stages = state.funnel.stage_counts.length
      ? state.funnel.stage_counts.map((row) => listItem(
        `${cohortLabels[row.cohort_label] || "Defined cohort"}: ${row.entry_count} entered; ${row.outcome_count} reached the outcome.`
      ))
      : [listItem("No funnel stage counts are available for this source set.")];
    replaceList(document.getElementById("x3-funnel-counts"), stages);

    document.getElementById("x3-live").textContent =
      `Showing ${cutoffLabels[cutoff.value]}, ${sourceLabels[source.value]}, across the ${scopeLabels[scope.value]}.`;
  };

  const selectState = (announce, preserveFocus) => {
    const stateKey = `${cutoff.value}|${source.value}|${scope.value}`;
    const state = data.states[stateKey];
    const unsupported = document.getElementById("x3-unsupported");
    if (!state) {
      controls.forEach((control, index) => { control.value = defaults[index]; });
      unsupported.textContent = "That combination is unavailable, so the opening state has been restored.";
      unsupported.hidden = false;
      render(data.states[data.meta.default_state], data.meta.default_state);
      return;
    }
    unsupported.hidden = true;
    render(state, stateKey);
    const params = new URLSearchParams(location.search);
    params.set("cutoff", cutoff.value);
    params.set("source", source.value);
    params.set("scope", scope.value);
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
