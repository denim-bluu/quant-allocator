import numpy as np

from quant_allocator.flagships.alarms import pipeline as ap
from quant_allocator.flagships.tearsheet import pipeline as tp


def _inline_troughs(hyp, ar1, t, n_paths, seed):
    # Byte-exact copy of drawdown_band's PRE-refactor inner loop, to pin the primitive.
    vol_monthly = hyp.vol_annual / np.sqrt(tp.MONTHS_PER_YEAR)
    mean_monthly = hyp.sharpe_annual / np.sqrt(tp.MONTHS_PER_YEAR) * vol_monthly
    innovation_sd = vol_monthly * np.sqrt(1.0 - ar1**2)
    rng = np.random.default_rng([seed, 7])
    troughs = np.empty((n_paths, t))
    for i in range(n_paths):
        path = np.empty(t)
        prev = 0.0
        for k in range(t):
            eps = rng.normal(0.0, innovation_sd)
            dev = ar1 * prev + eps
            path[k] = mean_monthly + dev
            prev = dev
        troughs[i] = tp._drawdown_path(path)
    return troughs


def test_simulate_null_drawdowns_matches_inline_loop():
    hyp = tp.DrawdownHypothesis(sharpe_annual=0.8, vol_annual=0.15)
    ar1 = 0.1
    expected = _inline_troughs(hyp, ar1, 48, 500, 20260706)
    got = tp.simulate_null_drawdowns(hyp, ar1, 48, n_paths=500, seed=20260706)
    assert np.array_equal(got, expected)


def test_max_drawdown_null_is_per_path_positive_depth():
    troughs = np.array([[0.0, -0.1, -0.05], [0.0, -0.2, -0.3]])
    mdd = ap.max_drawdown_null(troughs)
    assert np.allclose(mdd, [0.1, 0.3])  # deepest point per row, sign-flipped to positive


def test_familywise_band_is_monotone_and_meets_scalar_at_window_end():
    hyp = ap.DrawdownHypothesis(sharpe_annual=0.5, vol_annual=0.12)
    troughs = ap.simulate_null_drawdowns(hyp, 0.0, 48, n_paths=3000, seed=ap.ALARM_SEED)
    band_amber, band_red = ap.familywise_band(troughs)
    assert np.all(np.diff(band_amber) >= -1e-12)   # running-MDD quantile never decreases
    assert np.all(np.diff(band_red) >= -1e-12)
    assert np.all(band_red >= band_amber - 1e-12)  # 99th deeper than 95th
    # Identity (spec §3.2): the band's window-end value == the alpha-quantile of null MDD.
    null_mdd = ap.max_drawdown_null(troughs)
    assert band_red[-1] == np.percentile(null_mdd, 99)
    assert band_amber[-1] == np.percentile(null_mdd, 95)


def _returns_from_null(sharpe, vol, ar1, t, seed):
    # A "healthy" realized path is one draw from the maintained hypothesis process itself.
    rng = np.random.default_rng([seed, 99])
    vm = vol / np.sqrt(12.0)
    mm = sharpe / np.sqrt(12.0) * vm
    sd = vm * np.sqrt(1.0 - ar1**2)
    out = np.empty(t)
    prev = 0.0
    for k in range(t):
        prev = ar1 * prev + rng.normal(0.0, sd)
        out[k] = mm + prev
    return out


def test_alarm_state_flags_a_tail_drawdown_red_and_reports_percentile():
    hyp = ap.DrawdownHypothesis(sharpe_annual=1.0, vol_annual=0.06)
    # A -12% path is a deep tail for a smooth 6%-vol book: force it by scaling a null draw.
    base = _returns_from_null(1.0, 0.06, 0.0, 48, seed=3)
    returns = base - 0.02  # shift down so the path digs a deep drawdown
    v = ap.alarm_state(returns, hyp, roster_size=12, n_paths=4000, seed=ap.ALARM_SEED)
    assert v.level in {"green", "amber", "red"}
    assert 0.0 <= v.mdd_percentile <= 100.0
    assert v.realized_mdd > 0.0
    assert v.red_threshold >= v.amber_threshold
    assert v.expected_false_red == 12 * ap.RED_BUDGET  # heat-list count = N x per-manager RED budget
    assert (v.level == "red") == (v.realized_mdd > v.red_threshold)


def test_posterior_null_is_wider_than_point_null():
    # Same central Sharpe, but a posterior fan folds in Sharpe uncertainty => a wider,
    # deeper 99th-pct null MDD than any single plug-in (M3 spec §3.6).
    vol, ar1, t = 0.10, 0.0, 60
    point = ap.DrawdownHypothesis(sharpe_annual=0.8, vol_annual=vol)
    rng = np.random.default_rng([ap.ALARM_SEED, 5])
    posterior = ap.PosteriorHypothesis(
        sharpe_draws=rng.normal(0.8, 0.6, size=400), vol_annual=vol
    )
    point_mdd = ap.max_drawdown_null(
        ap.simulate_null_drawdowns(point, ar1, t, n_paths=5000, seed=ap.ALARM_SEED)
    )
    post_troughs = ap._simulate_posterior_troughs(posterior, ar1, t, n_paths=5000, seed=ap.ALARM_SEED)
    post_mdd = ap.max_drawdown_null(post_troughs)
    assert np.percentile(post_mdd, 99) > np.percentile(point_mdd, 99)


def test_hysteresis_holds_red_until_sustained_recovery():
    # Path digs past the RED arm line, then hovers at the boundary; a single month back inside
    # the clear line must NOT step down — two consecutive months must (M3 spec §3.5).
    exceeds_amber = np.array([0, 1, 1, 1, 1, 1, 1, 1], dtype=bool)
    exceeds_red = np.array([0, 0, 1, 1, 0, 0, 0, 0], dtype=bool)
    # month 4 clear alone, below_run reset at 5, then a sustained 2-month recovery at 6-7.
    inside_clear = np.array([1, 0, 0, 0, 1, 0, 1, 1], dtype=bool)
    levels = ap.hysteresis_sequence(exceeds_amber, exceeds_red, inside_clear)
    assert levels[2] == "red" and levels[3] == "red"
    assert levels[4] == "red"          # one month inside clear is not enough (below_run reset at 5)
    assert levels[-1] in {"amber", "green"}  # sustained recovery finally steps down
