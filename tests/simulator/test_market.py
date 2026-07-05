import numpy as np
import pandas as pd

from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_shapes_and_return_identity():
    cfg = MarketConfig(n_assets=50, n_months=24, seed=1)
    mkt = simulate_market(cfg)
    assert mkt.factor_returns.shape == (24, 4)
    assert mkt.betas.shape == (50, 4)
    assert mkt.idio_returns.shape == (24, 50)
    assert isinstance(mkt.factor_returns.index, pd.PeriodIndex)
    expected = (
        mkt.factor_returns.to_numpy() @ mkt.betas.to_numpy().T + mkt.idio_returns.to_numpy()
    )
    np.testing.assert_allclose(mkt.asset_returns.to_numpy(), expected)


def test_seed_reproducibility():
    a = simulate_market(MarketConfig(n_assets=30, n_months=12, seed=7))
    b = simulate_market(MarketConfig(n_assets=30, n_months=12, seed=7))
    pd.testing.assert_frame_equal(a.asset_returns, b.asset_returns)


def test_factor_vol_calibration():
    cfg = MarketConfig(n_assets=10, n_months=6000, seed=3)
    mkt = simulate_market(cfg)
    realized_annual_vol = mkt.factor_returns.std() * np.sqrt(12)
    expected = pd.Series(cfg.factor_annual_vols, index=list(cfg.factor_names))
    assert (realized_annual_vol - expected).abs().max() < 0.02
