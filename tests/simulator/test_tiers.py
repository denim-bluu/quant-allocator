import numpy as np
import pandas as pd

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers


def _fixture():
    market = simulate_market(MarketConfig(n_assets=100, n_months=12, seed=9))
    history = simulate_manager(market, ManagerConfig(seed=9))
    return market, history


def test_returns_only_tier_matches_portfolio_returns():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    pd.testing.assert_series_equal(tiers.returns_only, history.monthly_returns)


def test_exposures_tier_reports_true_factor_betas_and_gross_net():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    expected_betas = history.weights @ market.betas
    for factor in market.config.factor_names:
        np.testing.assert_allclose(
            tiers.exposures[f"beta_{factor}"], expected_betas[factor]
        )
    np.testing.assert_allclose(tiers.exposures["gross"], 1.6, atol=1e-8)
    np.testing.assert_allclose(tiers.exposures["net"], 0.2, atol=1e-8)
    assert ((tiers.exposures["top10_share"] > 0) & (tiers.exposures["top10_share"] <= 1)).all()


def test_transparency_tier_round_trips_to_weights():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    assert (tiers.transparency["weight"] != 0).all()
    rebuilt = (
        tiers.transparency.pivot(index="month", columns="asset", values="weight")
        .reindex(index=history.weights.index, columns=history.weights.columns)
        .fillna(0.0)
    )
    np.testing.assert_allclose(rebuilt.to_numpy(), history.weights.to_numpy())
