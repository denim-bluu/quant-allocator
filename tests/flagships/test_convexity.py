import numpy as np

from quant_allocator.flagships.convexity.bootstrap import block_bootstrap_ci


def test_block_bootstrap_ci_brackets_the_mean_and_contains_point():
    rng = np.random.default_rng([20260707, 99])
    x = rng.normal(0.4, 1.0, size=48)
    point = float(x.mean())
    lo, hi = block_bootstrap_ci(
        lambda a: float(a.mean()), (x,),
        level=0.90, n_boot=500, seed=20260707, stream_tag=1,
    )
    assert lo <= point <= hi            # point always inside its own interval
    assert lo < point < hi              # a non-degenerate spread
    assert lo < 0.4 < hi                # brackets the population mean


def test_block_bootstrap_ci_is_deterministic():
    x = np.arange(48, dtype=float)
    first = block_bootstrap_ci(
        lambda a: float(a.mean()), (x,), level=0.9, n_boot=200, seed=7, stream_tag=3
    )
    second = block_bootstrap_ci(
        lambda a: float(a.mean()), (x,), level=0.9, n_boot=200, seed=7, stream_tag=3
    )
    assert first == second


def test_block_bootstrap_ci_resamples_arrays_jointly():
    # Estimator = correlation; joint resampling must preserve pairing so a
    # strong correlation survives the bootstrap (a per-array shuffle would kill it).
    rng = np.random.default_rng([1, 2])
    a = rng.normal(size=60)
    b = 2.0 * a + rng.normal(scale=0.01, size=60)
    lo, hi = block_bootstrap_ci(
        lambda x, y: float(np.corrcoef(x, y)[0, 1]), (a, b),
        level=0.90, n_boot=300, seed=5, stream_tag=4,
    )
    assert lo > 0.9
