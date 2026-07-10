import numpy as np
import pytest

from quant_allocator.flagships.crowding import pipeline as crowding


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
