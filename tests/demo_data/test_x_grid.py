import pytest

from quant_allocator.demo_data import x_grid


def test_grid_collapses_to_thirty_configs():
    configs = x_grid.base_configs()
    assert len(configs) == 30  # 5 IC x 3 half-life x 2 sizing
    assert len({(c.ic, c.half_life, c.sizing) for c in configs}) == 30
    assert [c.index for c in configs] == list(range(30))


def test_config_seeds_are_independent_and_deterministic():
    a = x_grid._config_seed(x_grid.GRID_BASE_SEED, 3, 17)
    b = x_grid._config_seed(x_grid.GRID_BASE_SEED, 3, 17)
    c = x_grid._config_seed(x_grid.GRID_BASE_SEED, 3, 18)
    assert a == b and a != c


def test_run_config_yields_all_t_and_tier_cells():
    cfg = x_grid.SimConfig(ic=0.10, half_life=12.0, sizing=0.8, index=0)
    cells = x_grid.run_config(cfg, n_reps=24, base_seed=x_grid.GRID_BASE_SEED, use_cache=False)
    keys = {(c.T, c.tier) for c in cells}
    assert keys == {(t, tier) for t in x_grid.T_GRID for tier in x_grid.TIER_GRID}
    for cell in cells:
        for name, a in cell.analytics.items():
            assert a.lo <= a.point <= a.hi  # band contains point
            assert 0.0 <= a.power <= 1.0
            assert a.wilson_hw >= 0.0
    # P-tier unlocks trade-level analytics; R/E do not carry them.
    p_cell = next(c for c in cells if c.T == 120 and c.tier == "P")
    r_cell = next(c for c in cells if c.T == 120 and c.tier == "R")
    assert "hit_rate" in p_cell.analytics and "sizing_slope" in p_cell.analytics
    assert "hit_rate" not in r_cell.analytics


def test_power_monotone_in_ic_for_alpha_on_a_small_grid():
    # A reduced-rep smoke of the X1 §4 monotonicity invariant on the alpha metric.
    cells = {}
    for cfg in [c for c in x_grid.base_configs() if c.half_life == 12.0 and c.sizing == 0.8]:
        for cell in x_grid.run_config(cfg, n_reps=60, base_seed=x_grid.GRID_BASE_SEED, use_cache=False):
            cells[(cell.ic, cell.half_life, cell.sizing, cell.T, cell.tier)] = cell
    # At the longest T, R-tier alpha power should trend up with IC (within MC noise).
    powers = [
        cells[(ic, 12.0, 0.8, 120, "R")].analytics["alpha_ols"].power
        for ic in x_grid.IC_GRID
    ]
    assert powers[-1] >= powers[0] - 0.15  # tolerant of MC noise at 60 reps


@pytest.mark.slow
def test_size_near_five_percent_at_ic_zero():
    cfg = next(c for c in x_grid.base_configs() if c.ic == 0.0 and c.half_life == 12.0 and c.sizing == 0.8)
    cells = x_grid.run_config(cfg, n_reps=200, base_seed=x_grid.GRID_BASE_SEED, use_cache=False)
    cell = next(c for c in cells if c.T == 120 and c.tier == "R")
    assert cell.analytics["alpha_ols"].power < 0.15  # size, not power, at IC=0
