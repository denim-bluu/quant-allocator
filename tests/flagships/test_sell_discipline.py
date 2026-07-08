import numpy as np
import pandas as pd
import pytest

from quant_allocator.flagships.sell_discipline import pipeline as sd
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market


def _weights(rows):
    # rows: list of dicts name->weight; missing name = 0. Deterministic column order.
    names = sorted({n for row in rows for n in row})
    idx = pd.period_range("2000-01", periods=len(rows), freq="M", name="month")
    frame = pd.DataFrame(0.0, index=idx, columns=names)
    for m, row in enumerate(rows):
        for name, w in row.items():
            frame.iloc[m, frame.columns.get_loc(name)] = w
    frame.columns.name = "asset"
    return frame


def test_extract_exits_flags_held_then_gone():
    w = _weights([
        {"A": 0.5, "B": 0.5},          # m0: A,B held
        {"A": 0.5, "C": 0.5},          # m1: B gone (exit e=1), C fresh
        {"A": 0.5, "C": 0.5},          # m2
    ])
    exits = sd.extract_exits(w)
    assert exits == [sd.ExitEvent(exit_month=1, name="B")]


def test_holdings_by_month_reads_nonzero():
    w = _weights([{"A": 0.5, "B": -0.5}, {"A": 0.5}])
    holdings = sd.holdings_by_month(w)
    assert holdings[0] == {"A", "B"}
    assert holdings[1] == {"A"}


def test_pool_excludes_fresh_buys_and_gap_matches_worked_toy():
    # Spec §3.2 worked example, one exit: book {A,B,C,D}, sell D at execution month e.
    # Forward 2-month residuals cumulate to D +3.0%, A +1.0%, B 0.0%, C -1.0%.
    # Pool is B_{e-1} \ {D} = {A,B,C}; ghost mean = 0.0%; gap = +3.0pp.
    # A fresh buy E entering AT month e must NOT enter the pool.
    names = ["A", "B", "C", "D", "E"]
    idx = pd.period_range("2000-01", periods=4, freq="M", name="month")
    w = pd.DataFrame(0.0, index=idx, columns=names)
    w.loc[idx[0], ["A", "B", "C", "D"]] = 0.25            # m0 = B_{e-1}: incumbents
    w.loc[idx[1], ["A", "B", "C", "E"]] = 0.25            # m1 = e: D gone, E fresh-bought
    w.loc[idx[2], ["A", "B", "C", "E"]] = 0.25
    w.loc[idx[3], ["A", "B", "C", "E"]] = 0.25
    w.columns.name = "asset"
    resid = pd.DataFrame(0.0, index=idx, columns=names)
    # forward months e+1=m2, e+2=m3 monthly residuals summing to the toy totals:
    resid.loc[idx[2], ["A", "B", "C", "D"]] = [0.005, 0.0, -0.005, 0.015]
    resid.loc[idx[3], ["A", "B", "C", "D"]] = [0.005, 0.0, -0.005, 0.015]
    resid.loc[[idx[2], idx[3]], "E"] = 0.10               # a hot fresh buy — must be ignored
    exits = sd.extract_exits(w)
    assert exits == [sd.ExitEvent(exit_month=1, name="D")]
    res = sd.counterfactual_gap(resid, sd.holdings_by_month(w), exits, horizon=2)
    assert res.n_exits == 1
    assert res.gap == pytest.approx(0.03, abs=1e-9)       # +3.0pp, E excluded


def _demo_world(idio_ar1, exit_style, *, market_seed=1, mgr_seed=2, n_months=90, n_assets=90):
    market = simulate_market(
        MarketConfig(n_assets=n_assets, n_months=n_months, seed=market_seed, idio_ar1=idio_ar1)
    )
    hist = simulate_manager(
        market,
        ManagerConfig(
            n_long=40, n_short=0, information_coefficient=0.35,
            rebalance_fraction=0.15, seed=mgr_seed, exit_style=exit_style,
        ),
    )
    exits = sd.extract_exits(hist.weights)
    holdings = sd.holdings_by_month(hist.weights)
    res = sd.counterfactual_gap(market.idio_returns, holdings, exits, horizon=4)
    return res


def test_structural_null_no_leak_at_rho_zero():
    # §3.8 / §6.3 gate 1: at idio_ar1=0 NO exit rule can leak — the gap is
    # statistically zero (|gap| well under a detectable effect) for every style.
    for style in ("signal", "disposition", "random"):
        res = _demo_world(0.0, style)
        se = res.per_exit_gaps.std(ddof=1) / np.sqrt(res.n_exits)
        assert abs(res.gap) < sd.S4_MDG_FACTOR * se       # not detectable at ρ=0


def test_detection_and_direction_under_persistence():
    # §6.3 gate 2: at ρ>0 the disposition seller leaks (+), the disciplined seller
    # culls (-); the random seller stays near zero.
    dispo = _demo_world(0.4, "disposition")
    disc = _demo_world(0.4, "signal")
    ghost = _demo_world(0.4, "random")
    assert dispo.gap > 0.0
    assert disc.gap < 0.0
    assert disc.gap < ghost.gap < dispo.gap
    assert abs(ghost.gap) < abs(dispo.gap)


def test_curve_is_cumulative_and_gap_is_its_last_horizon():
    res = _demo_world(0.4, "disposition")
    assert res.curve.shape == (4,)
    assert res.gap == pytest.approx(res.curve[-1])
    # Disposition give-back accrues then plateaus: the curve rises over forward months.
    assert res.curve[0] < res.curve[-1]


def test_signed_icc_can_go_negative_for_a_stratified_rule():
    # Same-month exits ANTI-correlated (a selective rule sells "the worst k" every
    # month, so month means are MORE stable than iid) -> rho_c < 0 -> deff < 1 (§3.6).
    # P3's clamped ICC would floor this at 0; S4's signed version must not.
    values = np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0])   # tight within-cohort spread
    cohorts = np.array([0, 0, 1, 1, 2, 2])
    rho = sd.intra_cohort_correlation_signed(values, cohorts)
    assert rho < 0.0


def test_gap_band_is_deterministic_and_imports_p3():
    res = _demo_world(0.4, "disposition")
    b1 = sd.gap_band(res, reps=400, seed=7)
    b2 = sd.gap_band(res, reps=400, seed=7)
    assert (b1.se, b1.ci_lo, b1.ci_hi) == (b2.se, b2.ci_lo, b2.ci_hi)
    assert b1.ci_lo < res.gap < b1.ci_hi
    assert b1.min_detectable_gap == pytest.approx(sd.S4_MDG_FACTOR * b1.se)
    assert b1.gated is False                      # the demo book clears 150 exits


def test_gap_band_gate_fires_below_min_exits():
    res = _demo_world(0.4, "disposition", n_months=40)   # far fewer exits
    b = sd.gap_band(res, reps=200, seed=7, min_exits=10_000)
    assert b.gated is True


def test_curve_band_has_one_interval_per_horizon():
    res = _demo_world(0.4, "disposition")
    bands = sd.curve_band(res, reps=300, seed=7)
    assert len(bands) == res.horizon
    for (point, lo, hi), c in zip(bands, res.curve):
        assert lo <= point <= hi
        assert point == pytest.approx(c)


def test_pool_contamination_biases_the_random_seller_negative():
    # §6.3 gate 4 (the mock's one real bug): a pool that includes the month's fresh
    # buys (B_e instead of B_{e-1}) manufactures phantom sell-skill -> the RANDOM
    # seller reads spuriously negative. The correct incumbent pool does not.
    market = simulate_market(MarketConfig(n_assets=90, n_months=90, seed=1, idio_ar1=0.4))
    hist = simulate_manager(
        market, ManagerConfig(n_long=40, n_short=0, information_coefficient=0.35,
                              rebalance_fraction=0.15, seed=2, exit_style="random"))
    exits = sd.extract_exits(hist.weights)
    holdings = sd.holdings_by_month(hist.weights)
    correct = sd.counterfactual_gap(market.idio_returns, holdings, exits, horizon=4)
    # Contaminate: shift holdings so pool for exit e reads B_e (includes fresh buys).
    contaminated_holdings = holdings[1:] + [holdings[-1]]
    contaminated = sd.counterfactual_gap(
        market.idio_returns, contaminated_holdings, exits, horizon=4)
    assert contaminated.gap < correct.gap          # the bug drags the ghost negative


def test_horizon_robustness_sign_stable_across_H():
    # §6.3 gate 5: the verdict sign is stable across H in {2..6}; the slider is not a
    # verdict-shopping device.
    market = simulate_market(MarketConfig(n_assets=90, n_months=110, seed=1, idio_ar1=0.4))
    hist = simulate_manager(
        market, ManagerConfig(n_long=40, n_short=0, information_coefficient=0.35,
                              rebalance_fraction=0.15, seed=2, exit_style="disposition"))
    exits = sd.extract_exits(hist.weights)
    holdings = sd.holdings_by_month(hist.weights)
    for H in range(2, 7):
        res = sd.counterfactual_gap(market.idio_returns, holdings, exits, horizon=H)
        assert res.gap > 0.0


def test_trend_buckets_refuse_small_buckets():
    res = _demo_world(0.4, "disposition")
    labels = np.array([f"y{m // 12}" for m in res.exit_months])   # yearly buckets
    yearly = sd.trend_buckets(res.per_exit_gaps, res.exit_months, labels,
                              reps=200, seed=7, min_exits=60)
    assert all(isinstance(b.label, str) for b in yearly)
    quarterly_labels = np.array([f"q{m // 3}" for m in res.exit_months])
    quarterly = sd.trend_buckets(res.per_exit_gaps, res.exit_months, quarterly_labels,
                                 reps=200, seed=7, min_exits=60)
    assert any(b.sufficient is False for b in quarterly)          # ~18/quarter refused


def test_roster_shrink_wraps_s1():
    gaps = np.array([-0.0159, 0.0385])
    ses = np.array([0.004, 0.005])
    shrunk = sd.roster_shrink(gaps, ses)
    assert shrunk.posterior_alpha.shape == (2,)
    # Two very-different managers -> weak shrinkage; posteriors keep their signs.
    assert shrunk.posterior_alpha[0] < 0 < shrunk.posterior_alpha[1]


def test_verdict_chip_reads_the_band():
    res = _demo_world(0.4, "disposition")
    assert sd.verdict_chip(sd.gap_band(res, reps=300, seed=7)) in (
        "culls well", "edge leaks at the exit", "indistinguishable from a random sell"
    )
