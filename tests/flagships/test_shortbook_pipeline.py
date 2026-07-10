import numpy as np
import pytest

from quant_allocator.flagships.shortbook import pipeline as sb
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market


def _book(short_ic=None, n_months=120, seed=41):
    market = simulate_market(MarketConfig(n_assets=120, n_months=n_months, seed=20260710))
    history = simulate_manager(
        market,
        ManagerConfig(
            n_long=40, n_short=25, target_gross=1.6, target_net=0.2,
            information_coefficient=0.06, short_information_coefficient=short_ic,
            alpha_half_life_months=6.0, seed=seed,
        ),
    )
    return market, history


def test_decomposition_is_an_exact_identity():
    market, history = _book()
    w = history.weights.to_numpy()
    decomp = sb.decompose_short_sleeve(
        w, market.betas.to_numpy(), market.factor_returns.to_numpy(),
        market.idio_returns.to_numpy(),
    )
    short_w = np.minimum(w, 0.0)
    sleeve_from_assets = (short_w * market.asset_returns.to_numpy()).sum(axis=1)
    # §3.3: hedge + alpha reproduces the sleeve P&L to machine precision.
    assert np.max(np.abs(decomp.sleeve_pnl - sleeve_from_assets)) < 1e-12
    assert np.allclose(decomp.hedge_pnl + decomp.alpha_pnl, decomp.sleeve_pnl)
    # Short gross is the (positive) short exposure per month; ~0.70 for 1.6/0.2.
    assert np.allclose(decomp.short_gross, 0.70, atol=1e-9)


def test_hedge_share_is_a_bounded_descriptive_ratio():
    market, history = _book()
    decomp = sb.decompose_short_sleeve(
        history.weights.to_numpy(), market.betas.to_numpy(),
        market.factor_returns.to_numpy(), market.idio_returns.to_numpy(),
    )
    hs = sb.hedge_share(decomp)
    # §3.1: a 0.7-gross equity short sleeve is mostly factor offset.
    assert 0.70 <= hs <= 0.90


def test_borrow_adjusted_alpha_uses_the_s2_interval_and_shifts_by_the_drag():
    market, history = _book()
    decomp = sb.decompose_short_sleeve(
        history.weights.to_numpy(), market.betas.to_numpy(),
        market.factor_returns.to_numpy(), market.idio_returns.to_numpy(),
    )
    sa = sb.borrow_adjusted_alpha(decomp.alpha_pnl, sb.BORROW_COST_ANNUAL, decomp.short_gross)
    # Gross alpha is 12 x mean of the alpha component.
    assert np.isclose(sa.gross_annual, 12.0 * decomp.alpha_pnl.mean())
    # Drag is fee x average short gross (0.02 x 0.70 = 0.014); net shifts the interval down by it.
    assert np.isclose(sa.borrow_drag_annual, sb.BORROW_COST_ANNUAL * decomp.short_gross.mean())
    assert np.isclose(sa.net_annual, sa.gross_annual - sa.borrow_drag_annual)
    assert np.isclose(sa.net_ci[0], sa.gross_ci[0] - sa.borrow_drag_annual)
    assert np.isclose(sa.net_ci[1], sa.gross_ci[1] - sa.borrow_drag_annual)
    assert sa.calibrated == (sa.net_ci[0] > 0.0)


def test_trade_count_and_gate_render_rule():
    # §3.5: 25 + 6 x months. Both observed windows stay below the approved 780 line.
    assert sb.short_trade_count(25, 0.25, 60) == 385
    assert sb.short_trade_count(25, 0.25, 120) == 745
    market, history = _book()
    w, ar = history.weights.to_numpy(), market.asset_returns.to_numpy()
    gate_full = sb.hit_rate_gate(w, ar, n_short=25, turnover=0.25, months=120)
    gate_half = sb.hit_rate_gate(w[:60], ar[:60], n_short=25, turnover=0.25, months=60)
    assert gate_full.trades == 745 and gate_full.gate == 780 and gate_full.renders is False
    assert gate_half.trades == 385 and gate_half.renders is False
    assert 0.0 <= gate_full.hit_rate <= 1.0


def test_trade_gate_boundary_is_exactly_780(monkeypatch):
    monkeypatch.setattr(
        sb, "short_hit_rate", lambda *_: sb.Estimate(0.55, 0.025, 2.0, True, 0.55)
    )
    monkeypatch.setattr(sb, "short_trade_count", lambda *_: 779)
    below = sb.hit_rate_gate([], [], n_short=1, turnover=0.0, months=1)
    monkeypatch.setattr(sb, "short_trade_count", lambda *_: 780)
    at = sb.hit_rate_gate([], [], n_short=1, turnover=0.0, months=1)
    assert below.renders is False
    assert at.renders is True


def test_verdict_chip_text_is_pinned():
    assert sb.verdict_chip(sb.ShortAlpha(0.05, (0.01, 0.09), 0.014, 0.036, (0.004, 0.076), True)) == (
        "Short alpha, calibrated"
    )
    assert sb.verdict_chip(sb.ShortAlpha(0.0, (-0.03, 0.03), 0.014, -0.014, (-0.044, 0.016), False)) == (
        "No detectable short alpha net of borrow"
    )


def test_regression_fallback_reports_alpha_and_r2():
    market, history = _book()
    decomp = sb.decompose_short_sleeve(
        history.weights.to_numpy(), market.betas.to_numpy(),
        market.factor_returns.to_numpy(), market.idio_returns.to_numpy(),
    )
    rf = sb.regression_fallback(
        decomp.sleeve_pnl, market.factor_returns.to_numpy(), market.config.factor_names,
    )
    # §3.4: R^2 stands in for the hedge share; the two are close on the same sleeve.
    assert 0.60 <= rf.r2 <= 0.95
    assert rf.crosses_zero == (rf.ci[0] <= 0.0 <= rf.ci[1])


@pytest.mark.slow
def test_hedge_share_robust_across_seeds():
    # §8 ruling 3: the "~80% in both books" claim must hold across >=20 seeds — both books'
    # hedge shares inside ~[0.70, 0.90]. If this fails, the spec copy is corrected at the gate.
    for seed in range(20):
        for short_ic in (0.06, 0.0):
            market, history = _book(short_ic=short_ic, seed=100 + seed)
            decomp = sb.decompose_short_sleeve(
                history.weights.to_numpy(), market.betas.to_numpy(),
                market.factor_returns.to_numpy(), market.idio_returns.to_numpy(),
            )
            hs = sb.hedge_share(decomp)
            assert 0.65 <= hs <= 0.92, f"seed {seed} short_ic {short_ic}: HS {hs:.3f}"


@pytest.mark.slow
def test_specificity_gate_noise_short_rarely_calibrates():
    # §6.3 gate 1 (the load-bearing gate): at short IC = 0 the borrow-adjusted 90% interval
    # excludes zero from ABOVE in <= the nominal one-sided rate (5%) within MC error. This is
    # the whole card's justification — a noise sleeve must not certify short alpha.
    n_seeds = 60
    calibrated = 0
    for seed in range(n_seeds):
        market, history = _book(short_ic=0.0, seed=200 + seed)
        decomp = sb.decompose_short_sleeve(
            history.weights.to_numpy(), market.betas.to_numpy(),
            market.factor_returns.to_numpy(), market.idio_returns.to_numpy(),
        )
        sa = sb.borrow_adjusted_alpha(
            decomp.alpha_pnl, sb.BORROW_COST_ANNUAL, decomp.short_gross, n_boot=500,
        )
        calibrated += sa.calibrated
    rate = calibrated / n_seeds
    # Borrow drag makes the net test conservative (shifts the interval down), so the rate
    # sits at or below nominal. Allow MC slack at n=60.
    assert rate <= 0.12, f"noise sleeve calibrated {rate:.2%} of the time (gate: <= nominal)"
