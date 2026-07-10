import numpy as np
import pandas as pd
import pytest

from quant_allocator.flagships.crowding import pipeline as crowding
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_section_3_2_toy_overlap_and_cosine():
    a = np.array([0.40, 0.30, 0.20, 0.10, 0.00])
    b = np.array([0.15, 0.00, 0.10, 0.10, 0.65])
    assert crowding.common_weight_overlap(a, b) == pytest.approx(0.35)
    assert crowding.cosine_overlap(a, b) == pytest.approx(0.240966, abs=1e-6)


def test_teaching_pair_raw_and_liquidity_overlap():
    adv = np.array([25.0, 35.0, 30.0, 120.0, 110.0, 130.0, 115.0])
    a = np.array([0.10, 0.08, 0.06, 0.42, 0.34, 0.00, 0.00])
    b = np.array([0.12, 0.07, 0.05, 0.00, 0.00, 0.40, 0.36])
    assert crowding.common_weight_overlap(a, b) == pytest.approx(0.22)
    assert crowding.liquidity_adjusted_overlap(a * 500.0, b * 500.0, adv) == pytest.approx(
        0.519, abs=1e-3
    )


def test_common_weight_counts_only_same_direction_and_is_bounded():
    a = np.array([0.6, -0.4, 0.0])
    b = np.array([-0.6, -0.2, 0.2])
    assert crowding.common_weight_overlap(a, b) == pytest.approx(0.2)
    assert crowding.common_weight_overlap(a, b) == crowding.common_weight_overlap(b, a)
    assert crowding.common_weight_overlap(a, a) == pytest.approx(1.0)
    assert 0.0 <= crowding.common_weight_overlap(a, b) <= 1.0


@pytest.mark.parametrize(
    "bad",
    [np.zeros(3), np.array([1.0, np.nan]), np.array([1.0, np.inf])],
)
def test_overlap_rejects_invalid_vectors(bad):
    with pytest.raises(ValueError):
        crowding.gross_normalize(bad)


def test_overlap_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="same shape"):
        crowding.common_weight_overlap([1.0, 0.0], [1.0])


def test_days_to_cover_and_guards():
    result = crowding.days_to_cover([50_000_000.0], [25_000_000.0])
    assert result[0] == pytest.approx(10.0)
    with pytest.raises(ValueError, match="strictly positive"):
        crowding.days_to_cover([1.0], [0.0])
    with pytest.raises(ValueError, match="participation"):
        crowding.days_to_cover([1.0], [1.0], participation=0.0)


def test_participation_changes_dtc_but_cancels_from_normalized_overlap():
    a = np.array([10.0, 20.0, 0.0])
    b = np.array([5.0, 20.0, 10.0])
    adv = np.array([100.0, 10.0, 100.0])
    dtc_20 = crowding.days_to_cover(a, adv, participation=0.20)
    dtc_10 = crowding.days_to_cover(a, adv, participation=0.10)
    np.testing.assert_allclose(dtc_10, 2.0 * dtc_20)
    assert crowding.liquidity_adjusted_overlap(
        a, b, adv, participation=0.20
    ) == pytest.approx(crowding.liquidity_adjusted_overlap(a, b, adv, participation=0.10))


def test_roster_matrices_are_aligned_symmetric_and_find_hot_pair():
    positions = pd.DataFrame(
        [[60.0, 40.0, 0.0], [50.0, 50.0, 0.0], [0.0, 0.0, 100.0]],
        index=["Hollowmere", "Brackenford", "Control"],
        columns=["A", "B", "C"],
    )
    adv = pd.Series([10.0, 20.0, 100.0], index=positions.columns)
    result = crowding.roster_overlap_matrix(positions, adv)
    assert result.managers == tuple(positions.index)
    for matrix in (result.raw, result.cosine, result.liquidity):
        pd.testing.assert_index_equal(matrix.index, positions.index)
        pd.testing.assert_index_equal(matrix.columns, positions.index)
        np.testing.assert_allclose(matrix.to_numpy(), matrix.to_numpy().T)
        np.testing.assert_allclose(np.diag(matrix), 1.0)
    assert result.liquidity.loc["Hollowmere", "Brackenford"] > 0.8
    assert result.liquidity.loc["Hollowmere", "Control"] == 0.0


def test_pair_overlap_packages_the_three_measures():
    adv = np.array([10.0, 20.0, 100.0])
    result = crowding.pair_overlap([60.0, 40.0, 0.0], [50.0, 50.0, 0.0], adv)
    assert result.raw == pytest.approx(0.9)
    assert 0.0 <= result.liquidity <= 1.0
    assert -1.0 <= result.cosine <= 1.0


def test_unwind_separates_directions_and_requires_two_holders():
    positions = pd.DataFrame(
        [[20.0, -10.0, 10.0], [30.0, -15.0, 0.0], [-40.0, 5.0, 0.0]],
        index=["A", "B", "C"],
        columns=["X", "Y", "Solo"],
    )
    adv = pd.Series([10.0, 5.0, 10.0], index=positions.columns)
    report = crowding.unwind_stress(positions, adv, stress_delta=0.5)
    rows = {(row.asset, row.direction): row for row in report.rows}
    assert rows[("X", "long")].holder_count == 2
    assert rows[("X", "long")].combined_dollars == 50.0
    assert rows[("X", "long")].days_stressed_volume == pytest.approx(10.0)
    assert ("X", "short") not in rows
    assert rows[("Y", "short")].combined_dollars == 25.0
    assert ("Y", "long") not in rows
    assert not any(row.asset == "Solo" for row in report.rows)


def test_stress_delta_scaling_and_illustrative_impact():
    positions = pd.DataFrame([[20.0], [30.0]], index=["A", "B"], columns=["X"])
    adv = pd.Series([10.0], index=positions.columns)
    vol = pd.Series([0.02], index=positions.columns)
    base = crowding.unwind_stress(positions, adv, daily_vol=vol, stress_delta=0.5)
    crisis = crowding.unwind_stress(positions, adv, daily_vol=vol, stress_delta=0.25)
    assert crisis.worst.days_stressed_volume == pytest.approx(
        2.0 * base.worst.days_stressed_volume
    )
    assert base.worst.illustrative_impact_rate == pytest.approx(
        0.02 * np.sqrt(base.worst.days_stressed_volume)
    )
    no_overlay = crowding.unwind_stress(positions, adv, stress_delta=0.5)
    assert no_overlay.worst.illustrative_impact_rate is None


def test_shared_crowd_dial_recovers_monotonic_average_overlap():
    market = simulate_market(MarketConfig(n_assets=240, n_months=120, seed=17))
    averages = []
    for participation in (0.0, 0.25, 0.50, 0.75, 0.90):
        histories = [
            simulate_manager(
                market,
                ManagerConfig(
                    n_long=n_long,
                    n_short=n_short,
                    target_gross=1.0,
                    target_net=0.4,
                    information_coefficient=0.1,
                    seed=seed,
                    crowd_participation=participation,
                    crowd_seed=77,
                ),
            )
            for seed, n_long, n_short in ((101, 24, 12), (202, 30, 10))
        ]
        overlaps = [
            crowding.common_weight_overlap(histories[0].weights.iloc[t], histories[1].weights.iloc[t])
            for t in range(24, market.config.n_months)
        ]
        averages.append(float(np.mean(overlaps)))
    assert np.all(np.diff(averages) > 0.0), averages
