from quant_allocator.demo_data import x_grid


def test_verdict_bands():
    assert x_grid.verdict_for(0.90) == "robust"
    assert x_grid.verdict_for(0.80) == "robust"
    assert x_grid.verdict_for(0.65) == "shrink"
    assert x_grid.verdict_for(0.50) == "shrink"
    assert x_grid.verdict_for(0.10) == "noise"


def _tiny_grid():
    cells = {}
    estimates = {}
    for cfg in x_grid.base_configs():
        result = x_grid.run_config(cfg, n_reps=40, base_seed=x_grid.GRID_BASE_SEED, use_cache=True)
        for cell in result.cells:
            cells[(cell.ic, cell.half_life, cell.sizing, cell.T, cell.tier)] = cell
        estimates[(cfg.ic, cfg.half_life, cfg.sizing)] = result.estimates
    return cells, estimates


def test_thresholds_and_gate_states_are_consistent():
    cells, estimates = _tiny_grid()
    payloads, thresholds, meta = x_grid.build_grid(cells=cells, estimates=estimates)
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


def test_posterior_pooled_across_ic_lands_only_on_r_and_e():
    # FIX 2: build_grid injects the pooled posterior into R and E cells only, and
    # the R (OLS) and E (pinned) inputs give distinct posterior bands.
    cells, estimates = _tiny_grid()
    payloads, _, _ = x_grid.build_grid(cells=cells, estimates=estimates)
    ref = (x_grid.PINNED_EFFECT_IC, x_grid.REF_HALF_LIFE, x_grid.REF_SIZING, x_grid.T_MAX)
    r_post = payloads[(*ref, "R")].analytics["alpha_posterior"]
    e_post = payloads[(*ref, "E")].analytics["alpha_posterior"]
    assert "alpha_posterior" not in payloads[(*ref, "P")].analytics
    assert (r_post["point"], r_post["lo"], r_post["hi"]) != (e_post["point"], e_post["lo"], e_post["hi"])
