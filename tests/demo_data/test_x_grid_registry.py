from quant_allocator.demo_data import x_grid


def test_verdict_bands():
    assert x_grid.verdict_for(0.90) == "robust"
    assert x_grid.verdict_for(0.80) == "robust"
    assert x_grid.verdict_for(0.65) == "shrink"
    assert x_grid.verdict_for(0.50) == "shrink"
    assert x_grid.verdict_for(0.10) == "noise"


def _tiny_grid():
    cells = {}
    for cfg in x_grid.base_configs():
        for cell in x_grid.run_config(cfg, n_reps=40, base_seed=x_grid.GRID_BASE_SEED, use_cache=True):
            cells[(cell.ic, cell.half_life, cell.sizing, cell.T, cell.tier)] = cell
    return cells


def test_thresholds_and_gate_states_are_consistent():
    cells = _tiny_grid()
    payloads, thresholds, meta = x_grid.build_grid(cells=cells)
    # Every payload cell has all its analytics rendered with a gate state.
    for key, payload in payloads.items():
        for name, a in payload.analytics.items():
            assert a["verdict"] in {"robust", "shrink", "noise"}
            assert a["gate_state"] in {"open", "closed"}
            # Gate closed exactly when gate quantity is below threshold (X1 §4).
            below = a["gate_quantity"] < a["threshold"]
            assert (a["gate_state"] == "closed") == below
    assert meta["n_reps"] == 40
    assert ("hit_rate", "P") in thresholds
