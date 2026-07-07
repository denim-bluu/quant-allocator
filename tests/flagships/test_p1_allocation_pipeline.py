import numpy as np

from quant_allocator.flagships.allocation import pipeline as ap


def test_config_carries_every_gate_constant():
    cfg = ap.AllocationConfig()
    assert cfg.alloc_cap == 0.20          # P1_ALLOC_CAP (§8.6)
    assert cfg.n_draws == 50_000          # P1_N_DRAWS (§8.6)
    assert cfg.band_pct == (10.0, 90.0)   # P1_BAND_PCT (§8.1)
    assert cfg.clear_pct == (25.0, 75.0)  # P1_HYSTERESIS_BANDS clear band (§8.1)
    assert cfg.sigma_demo == 0.08         # P1_SIGMA_DEMO (§8.2)
    assert cfg.kelly_fraction == 0.5      # P1_KELLY_FRACTION (§8.6)


def test_allocate_is_long_only_fully_invested_edge_over_variance():
    # Positive alphas -> weight proportional to alpha/sigma^2; negatives -> zero; sums to 1.
    alphas = np.array([0.10, 0.05, -0.02])
    sigmas = np.full(3, 0.08)
    w = ap.allocate_one_draw(alphas, sigmas, cap=1.0)
    assert w[2] == 0.0                      # long-only: negative alpha gets nothing
    assert abs(w.sum() - 1.0) < 1e-12       # fully invested
    assert w[0] / w[1] == 2.0               # edge-over-variance with equal sigma -> alpha ratio


def test_allocate_all_nonpositive_returns_zeros():
    alphas = np.array([-0.05, -0.01, 0.0])
    w = ap.allocate_one_draw(alphas, np.full(3, 0.08), cap=0.20)
    assert np.array_equal(w, np.zeros(3))   # nothing to fund; not renormalized to garbage


def test_cap_binds_and_redistributes_pro_rata():
    # One dominant name must be capped; the excess flows to the uncapped names pro-rata.
    alphas = np.array([1.0, 0.10, 0.05])
    w = ap.allocate_one_draw(alphas, np.full(3, 0.08), cap=0.50)
    assert abs(w[0] - 0.50) < 1e-9          # capped
    assert abs(w.sum() - 1.0) < 1e-9        # still fully invested
    assert w[1] / w[2] == 2.0               # redistribution preserves the 0.10:0.05 ratio
