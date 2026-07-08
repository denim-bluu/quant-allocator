import numpy as np

from quant_allocator.flagships.sizing_lab import pipeline as sp


def test_build_panel_reconstructs_ages_and_side():
    # name 0: held months 0..3 then dropped; name 1: entered month 2; name 2: gap+re-entry.
    w = np.array([
        [0.05, 0.00, -0.04],
        [0.05, 0.00,  0.00],
        [0.05, 0.03, -0.04],
        [0.05, 0.03, -0.04],
        [0.00, 0.03, -0.04],
    ])
    idio = np.zeros_like(w)
    panel = sp.build_panel(w, idio)
    assert panel.ages[:, 0].tolist() == [0, 1, 2, 3, -1]     # continuous run then unheld
    assert panel.ages[:, 1].tolist() == [-1, -1, 0, 1, 2]    # late entry
    assert panel.ages[:, 2].tolist() == [0, -1, 0, 1, 2]     # gap resets age
    assert panel.side[0, 0] == 1.0 and panel.side[0, 2] == -1.0
    assert panel.side[1, 2] == 0.0                            # unheld -> side 0


def test_sizing_slope_estimate_matches_x1_kernel_on_the_built_matrices():
    from quant_allocator.demo_data.x_metrics import sizing_slope as kernel
    rng = np.random.default_rng([20260707, 1])
    w = rng.normal(0, 0.04, (60, 20))
    idio = rng.normal(0, 0.02, (60, 20))
    panel = sp.build_panel(w, idio)
    got = sp.sizing_slope_estimate(panel)
    hedged = idio - idio.mean(axis=1, keepdims=True)
    expected = kernel(np.abs(w), w * hedged)
    assert got.point == expected.point and got.se == expected.se
    assert got.tstat == expected.tstat


def test_sizing_slope_separates_conviction_from_equal_weight():
    # Same picks + same returns; only sizing differs. A book that sizes by |signal| where
    # signal predicts the return earns a POSITIVE slope; its equal-weight shadow earns ~0.
    rng = np.random.default_rng([20260707, 2])
    T, N = 120, 30
    idio = rng.normal(0, 0.02, (T, N))
    held = np.zeros((T, N))
    held[:, :10] = 1.0                                     # first ten names held every month
    signal = idio + rng.normal(0, 0.01, (T, N))            # skilled: signal tracks the return
    conviction = np.abs(signal) * held
    sizer = np.sign(signal) * conviction / conviction.sum(axis=1, keepdims=True) * held
    picker = held / held.sum(axis=1, keepdims=True)         # equal weight, same names
    slope_sizer = sp.sizing_slope_estimate(sp.build_panel(sizer, idio)).point
    slope_picker = sp.sizing_slope_estimate(sp.build_panel(picker, idio)).point
    assert slope_sizer > slope_picker
    assert abs(slope_picker) < abs(slope_sizer)


def test_independent_trades_matches_x1_formula():
    # X1 §3.4: (n_long + n_short) + (round(reb·n_long) + round(reb·n_short)) · T.
    assert sp.independent_trades(40, 25, 0.25, 48) == 833
    assert sp.independent_trades(40, 25, 0.25, 120) == 1985
    assert sp.independent_trades(20, 10, 0.10, 48) == 174


def test_cluster_bootstrap_brackets_the_point_and_is_seed_reproducible():
    rng = np.random.default_rng([20260707, 3])
    w = rng.normal(0, 0.04, (80, 20))
    idio = rng.normal(0, 0.02, (80, 20))
    panel = sp.build_panel(w, idio)

    def stat(p):
        return sp.sizing_slope_estimate(p).point

    a = sp.cluster_bootstrap(stat, panel, n=300, rng=np.random.default_rng([sp.S3_BOOTSTRAP_STREAM, 5]))
    b = sp.cluster_bootstrap(stat, panel, n=300, rng=np.random.default_rng([sp.S3_BOOTSTRAP_STREAM, 5]))
    assert a == b                                            # deterministic given the rng
    assert a.lo <= a.point <= a.hi


def _decaying_panel(half_life, T=120, N=60, seed=7):
    # A held book whose held-name idio decays with a known half-life: age-m idio = 2^{-m/H}·base.
    rng = np.random.default_rng([20260707, seed])
    idio = rng.normal(0, 0.02, (T, N))
    weights = np.zeros((T, N))
    # Ten names entered on a stagger, each held 24 months, re-entered on a cycle.
    for j in range(N):
        start = (j * 2) % T
        for k in range(min(24, T - start)):
            t = start + k
            weights[t, j] = 0.03
            idio[t, j] = 0.02 * 0.5 ** (k / half_life)  # deterministic decaying edge
    return sp.build_panel(weights, idio)


def test_decay_curve_pools_by_age_and_counts_thin_out():
    panels = [_decaying_panel(6.0, seed=s) for s in range(8)]
    curve = sp.decay_curve(panels, idio_vol=0.02, max_age=12)
    assert curve.values[0] > curve.values[6] > curve.values[12]  # monotone decay
    assert curve.counts[0] >= curve.counts[12]                    # older ages are thinner


def test_fit_half_life_recovers_the_dial_from_age_one():
    panels = [_decaying_panel(6.0, seed=s) for s in range(20)]
    curve = sp.decay_curve(panels, idio_vol=0.02, max_age=12)
    hl = sp.fit_half_life(curve, np.arange(1, 13))
    assert abs(hl - 6.0) < 0.6                                    # recovers the 6.0 truth


def test_fit_half_life_is_invariant_to_idio_vol_scale():
    panels = [_decaying_panel(6.0, seed=s) for s in range(10)]
    a = sp.fit_half_life(sp.decay_curve(panels, idio_vol=0.02), np.arange(1, 13))
    b = sp.fit_half_life(sp.decay_curve(panels, idio_vol=0.99), np.arange(1, 13))
    assert abs(a - b) < 1e-9                                       # y-scale cancels in the log-slope


def test_holding_decomposition_shares_sum_to_one_and_front_load():
    panel = _decaying_panel(6.0, seed=3)
    shares = sp.holding_decomposition(panel)
    assert abs(sum(shares.values()) - 1.0) < 1e-9
    assert shares["0-2m"] > shares["12m+"]                         # fresh positions earn more
    assert set(shares) == {"0-2m", "3-5m", "6-11m", "12m+"}
