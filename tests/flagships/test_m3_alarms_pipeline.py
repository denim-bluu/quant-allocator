import numpy as np

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
