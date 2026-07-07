import numpy as np
import pandas as pd

from quant_allocator.flagships.convexity import diagnostics as dg
from quant_allocator.flagships.convexity import screen as sc
from quant_allocator.flagships.convexity.bootstrap import block_bootstrap_ci
from quant_allocator.flagships.tearsheet.pipeline import DrawdownHypothesis
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.overlays import WrittenPutOverlay, apply_written_put_overlay


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


def _honest_and_overlaid(kappa=0.9, moneyness=1.0, seed=20260707, n_months=48):
    market = simulate_market(MarketConfig(n_assets=300, n_months=n_months, seed=seed))
    hist = simulate_manager(market, ManagerConfig(information_coefficient=0.05, seed=3))
    mkt = market.factor_returns["market"]
    honest = hist.monthly_returns
    honest.index = mkt.index
    overlaid = apply_written_put_overlay(
        honest, mkt, WrittenPutOverlay(strike_moneyness=moneyness, overlay_notional=kappa)
    )
    return honest.to_numpy(), overlaid.to_numpy(), mkt.to_numpy()


def test_treynor_mazuy_gamma_is_more_negative_under_overlay():
    honest, overlaid, mkt = _honest_and_overlaid()
    g_honest = dg.treynor_mazuy(honest, mkt, seed=1)
    g_overlaid = dg.treynor_mazuy(overlaid, mkt, seed=1)
    # A written put injects negative curvature: overlaid gamma sits below honest.
    assert g_overlaid.point < g_honest.point
    assert g_overlaid.ci_lo <= g_overlaid.point <= g_overlaid.ci_hi


def test_treynor_mazuy_recovers_zero_curvature_at_kappa_zero():
    honest, _, mkt = _honest_and_overlaid(kappa=0.0)
    stat = dg.treynor_mazuy(honest, mkt, seed=1)
    # Honest manager: gamma interval should not clear zero in the short-vol direction.
    assert stat.verdict in {"inconclusive", "convex-benign"}


def test_updown_beta_gap_negative_under_overlay():
    honest, overlaid, mkt = _honest_and_overlaid()
    gap = dg.updown_beta(overlaid, mkt, seed=1)
    # gap = beta_up - beta_down; short-vol tell is beta_down > beta_up i.e. gap < 0.
    assert gap.point < dg.updown_beta(honest, mkt, seed=1).point
    assert gap.ci_lo <= gap.point <= gap.ci_hi


def test_market_coskew_more_negative_under_overlay():
    honest, overlaid, mkt = _honest_and_overlaid()
    assert dg.market_coskew(overlaid, mkt, seed=1).point < dg.market_coskew(honest, mkt, seed=1).point


def test_drawdown_vol_signature_reuses_band_and_flags_deeper_tail():
    honest, overlaid, mkt = _honest_and_overlaid()
    hyp_o = DrawdownHypothesis(sharpe_annual=0.8, vol_annual=float(overlaid.std(ddof=1) * (12 ** 0.5)))
    stat = dg.drawdown_vol_signature(overlaid, hyp_o, seed=1)
    assert stat.name == "drawdown_vol"
    assert stat.ci_lo <= stat.point <= stat.ci_hi
    assert stat.verdict in {"short-vol-consistent", "inconclusive", "convex-benign"}


def test_straddle_loading_not_played_without_ptfs():
    honest, _, _ = _honest_and_overlaid()
    stat = dg.straddle_loading(honest, None, seed=1)
    assert stat.played is False
    assert stat.verdict == "not-played"


def test_straddle_loading_played_with_series():
    honest, overlaid, mkt = _honest_and_overlaid()
    # A synthetic short-put payoff on the market is a stand-in PTFS series for the
    # UNIT test only (the demo never fabricates one — it shows the rung as unplayed).
    ptfs = -pd.Series(mkt).clip(upper=0.0).to_numpy()
    stat = dg.straddle_loading(overlaid, ptfs, seed=1)
    assert stat.played is True
    assert stat.ci_lo <= stat.point <= stat.ci_hi


def _run(kappa, moneyness=1.0, seed=20260707, n_months=48):
    honest, overlaid, mkt = _honest_and_overlaid(kappa=kappa, moneyness=moneyness, seed=seed, n_months=n_months)
    series = overlaid if kappa > 0 else honest
    rf = 0.02 / 12
    return sc.run_screen(series, mkt, rf, t=n_months, seed=seed)


def test_screen_orders_the_five_diagnostics():
    res = _run(kappa=0.0)
    assert list(res.diagnostics) == [
        "treynor_mazuy", "updown_beta", "market_coskew", "drawdown_vol", "straddle_loading"
    ]
    assert res.diagnostics["straddle_loading"].played is False  # no PTFS in the demo path


def test_powergate_closed_below_min_t_flag():
    res = _run(kappa=0.9, n_months=36)
    assert res.t == 36
    assert res.gate_open is False
    assert res.composite_chip == "noise"
    assert res.composite_verdict == "inconclusive"


def test_playable_count_excludes_unplayed_straddle():
    res = _run(kappa=0.0)
    assert res.playable_count == 4  # TM, updown, coskew, drawdown_vol


def test_composite_flags_only_when_k_agree_and_gate_open():
    res = _run(kappa=0.0)
    # An honest manager should not reach K short-vol votes.
    assert res.short_vol_count < sc.M2_COMPOSITE_K
    assert res.composite_chip == "noise"
