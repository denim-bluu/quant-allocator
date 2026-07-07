import numpy as np
import pytest

from quant_allocator.flagships.drift import bands, calibrate


def _band():
    return bands.BandSpec(lower=-0.10, upper=0.10, delta=0.05)


def test_wilson_interval_brackets_the_point_and_is_ordered():
    lo, hi = calibrate.wilson_interval(5, 10)
    assert 0.0 <= lo < 0.5 < hi <= 1.0


def test_wilson_interval_handles_zero_and_full():
    lo0, hi0 = calibrate.wilson_interval(0, 20)
    assert lo0 == pytest.approx(0.0, abs=1e-9)
    assert hi0 > 0.0
    lo1, hi1 = calibrate.wilson_interval(20, 20)
    assert hi1 == pytest.approx(1.0, abs=1e-9)
    assert lo1 < 1.0


def test_higher_threshold_lowers_false_alarm_rate():
    band = _band()
    # Null paths that poke over the edge: raising h must not raise the alarm rate.
    rng = np.random.default_rng(0)
    null = [0.10 + rng.normal(0, 0.04, size=60) for _ in range(50)]
    r_low, _, _ = calibrate.false_alarm_rate(null, band, k=0.0125, h=0.10)
    r_high, _, _ = calibrate.false_alarm_rate(null, band, k=0.0125, h=0.60)
    assert r_high <= r_low


def test_calibrate_threshold_meets_budget_and_is_smallest_qualifying():
    band = _band()
    rng = np.random.default_rng(1)
    null = [0.10 + rng.normal(0, 0.04, size=60) for _ in range(80)]
    grid = np.arange(0.05, 1.0, 0.05)
    h = calibrate.calibrate_threshold(null, band, k=0.0125, budget_per_year=0.05, h_grid=grid)
    rate, _, _ = calibrate.false_alarm_rate(null, band, k=0.0125, h=h)
    assert rate <= 0.05
    # One grid step lower must exceed the budget (smallest-qualifying).
    lower = h - 0.05
    if lower >= grid[0]:
        rate_lower, _, _ = calibrate.false_alarm_rate(null, band, k=0.0125, h=lower)
        assert rate_lower > 0.05


def test_measure_detection_reports_rate_delay_and_wilson():
    band = _band()
    onset = 10
    alt = [
        np.concatenate([np.full(onset, 0.10), np.linspace(0.10, 0.45, 50)])
        for _ in range(30)
    ]
    res = calibrate.measure_detection(alt, band, k=0.0125, h=0.20, drift_onset=onset, detection_window=48)
    assert res.n_paths == 30
    assert res.rate == pytest.approx(res.n_detected / res.n_paths)
    assert 0.0 <= res.wilson_lo <= res.rate <= res.wilson_hi <= 1.0
    assert res.median_delay is not None and res.median_delay >= 0


@pytest.mark.slow
def test_draw_beta_paths_null_wanders_and_drift_shifts_it():
    kwargs = {"information_coefficient": 0.05, "seed": 0}
    null = calibrate.draw_beta_paths(
        6, base_seed=20260707, n_assets=120, n_months=36, target_net=0.10,
        drift=None, manager_kwargs=kwargs,
    )
    # Honest wander is non-degenerate (beta_market varies month to month).
    assert all(np.std(p) > 0 for p in null)
    drift = calibrate.NetBetaDrift(total_walk=0.30, ramp_months=12, onset_month=12)
    alt = calibrate.draw_beta_paths(
        6, base_seed=20260707, n_assets=120, n_months=36, target_net=0.10,
        drift=drift, manager_kwargs=kwargs,
    )
    # Drift walks the terminal net beta materially above the honest terminal level.
    assert np.mean([p[-1] for p in alt]) > np.mean([p[-1] for p in null]) + 0.15
