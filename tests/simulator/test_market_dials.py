import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_ar1_zero_is_byte_identical():
    base = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    off = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3, idio_ar1=0.0))
    pd.testing.assert_frame_equal(base.idio_returns, off.idio_returns)
    pd.testing.assert_frame_equal(base.factor_returns, off.factor_returns)
    pd.testing.assert_frame_equal(base.betas, off.betas)


def test_ar1_injects_persistence_and_preserves_variance():
    rho = 0.4
    base = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3))
    dialed = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3, idio_ar1=rho))
    idio = dialed.idio_returns.to_numpy()
    ac1 = np.mean([
        (lambda c: c[1:] @ c[:-1] / (c @ c))(idio[:, j] - idio[:, j].mean())
        for j in range(idio.shape[1])
    ])
    assert abs(ac1 - rho) < 0.05
    # Stationary marginal variance preserved vs the rho=0 innovations.
    assert np.isclose(idio.std(), base.idio_returns.to_numpy().std(), rtol=0.05)


def test_ar1_out_of_band_raises():
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=1.0))
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=-1.5))
