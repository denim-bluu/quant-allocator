import pytest

from quant_allocator.demo_data import x_grid


@pytest.mark.slow
def test_projected_full_run_is_well_under_one_hour():
    report = x_grid.estimate_runtime(sample_configs=2, n_reps=x_grid.N_REPS)
    assert report["projected_wall_seconds"] < x_grid.RUNTIME_BUDGET_SECONDS
    assert report["per_config_seconds"] > 0.0
    assert report["processes"] >= 1


def test_estimate_runtime_smoke_extrapolation():
    # Fast structural check with tiny reps: the projection math is exercised
    # even when the measured per-config time is small.
    report = x_grid.estimate_runtime(sample_configs=1, n_reps=8)
    assert report["projected_total_seconds"] == pytest.approx(
        report["per_config_seconds"] * 30, rel=1e-6
    )
    assert report["projected_wall_seconds"] <= report["projected_total_seconds"] + 1e-6
