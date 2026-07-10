import numpy as np
import pandas as pd
import pytest

from quant_allocator.flagships.holdings13f.pipeline import (
    M6_OPTION_FLAG_SHARE,
    concentration,
    conviction_persistence,
    cosine_overlap,
    coverage_ratio,
    emit_13f_long_book,
    reported_option_share,
)


def _panel():
    months = pd.period_range("2024-01", periods=6, freq="M", name="month")
    assets = pd.Index([f"A{i}" for i in range(4)], name="asset")
    # A0,A1 long; A2 short; A3 long. Quarter-ends: 2024-03, 2024-06.
    data = np.tile([0.4, 0.2, -0.3, 0.1], (6, 1))
    return pd.DataFrame(data, index=months, columns=assets)


def _quarter_ends(start_month: str, periods: int) -> pd.PeriodIndex:
    # 3M periods span forward from their anchor label (e.g. "2024-01" spans Jan-Feb-Mar),
    # so anchoring at each quarter's FIRST month is what lets emit_13f_long_book's
    # asfreq(how="end") resolve to the true quarter-end month (M6 §3.3).
    return pd.period_range(start_month, periods=periods, freq="3M")


def test_longs_only_and_renormalized_to_shares():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = _quarter_ends("2024-01", periods=2)
    book = emit_13f_long_book(weights, q, eligible)
    # short A2 dropped; longs 0.4/0.2/0.1 renormalize to 4/7, 2/7, 1/7.
    row = book.loc[book.index[0]]
    assert row["A2"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1", "A3"]].to_numpy(), [4 / 7, 2 / 7, 1 / 7])
    assert np.isclose(row.sum(), 1.0)


def test_ineligible_names_are_cropped_before_renormalization():
    weights = _panel()
    eligible = pd.Series([True, True, True, False], index=weights.columns)  # A3 ineligible
    q = _quarter_ends("2024-01", periods=1)
    book = emit_13f_long_book(weights, q, eligible)
    row = book.loc[book.index[0]]
    assert row["A3"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1"]].to_numpy(), [4 / 6, 2 / 6])


def test_emitter_is_deterministic_and_rng_free():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = _quarter_ends("2024-01", periods=2)
    pd.testing.assert_frame_equal(
        emit_13f_long_book(weights, q, eligible), emit_13f_long_book(weights, q, eligible)
    )


def test_snapshot_is_the_quarter_end_month_not_the_quarter_start():
    # _panel() is constant across months, so it cannot tell which month inside a quarter
    # was snapshotted. Give every month its own row so a wrong-month snapshot is visible.
    months = pd.period_range("2024-01", periods=6, freq="M", name="month")
    assets = pd.Index(["A0", "A1"], name="asset")
    data = [
        [0.1, 0.9],  # Jan (Q1 start)
        [0.2, 0.8],  # Feb
        [0.3, 0.7],  # Mar (Q1 end)
        [0.4, 0.6],  # Apr (Q2 start)
        [0.5, 0.5],  # May
        [0.6, 0.4],  # Jun (Q2 end)
    ]
    weights = pd.DataFrame(data, index=months, columns=assets)
    eligible = pd.Series(True, index=weights.columns)
    q = _quarter_ends("2024-01", periods=2)
    book = emit_13f_long_book(weights, q, eligible)
    # Both names are long and each month already sums to 1, so shares equal the raw
    # month's row exactly -- isolating month selection from renormalization.
    np.testing.assert_allclose(book.loc[book.index[0]].to_numpy(), [0.3, 0.7])
    np.testing.assert_allclose(book.loc[book.index[1]].to_numpy(), [0.6, 0.4])
    # And NOT the quarter-start month -- guards against regressing to how="start".
    assert not np.allclose(book.loc[book.index[0]].to_numpy(), [0.1, 0.9])
    assert not np.allclose(book.loc[book.index[1]].to_numpy(), [0.4, 0.6])


def test_concentration_reproduces_the_teaching_vector():
    book = pd.Series([0.684, 0.158, 0.079, 0.053, 0.026])
    result = concentration(book, top_n=3)
    assert result.top_n_weight == pytest.approx(0.921)
    assert result.hhi == pytest.approx(0.502546)
    assert result.effective_names == pytest.approx(1.989867, rel=1e-6)


def test_persistence_counts_latest_positive_names_back_to_first_break():
    panel = pd.DataFrame(
        [
            [0.5, 0.3, 0.2, 0.0],
            [0.5, 0.0, 0.2, 0.3],
            [0.4, 0.0, 0.2, 0.4],
        ],
        columns=["A", "B", "C", "D"],
    )
    assert conviction_persistence(panel, k=10) == {"A": 3, "D": 2, "C": 3}


def test_cosine_truncates_each_book_independently_before_union_alignment():
    a = pd.Series({"A": 0.6, "B": 0.4, "TAIL_A": 0.2})
    b = pd.Series({"A": 0.3, "C": 0.7, "TAIL_B": 0.2})
    result = cosine_overlap(a, b, depth=2)
    expected = 0.6 * 0.3 / (np.linalg.norm([0.6, 0.4]) * np.linalg.norm([0.3, 0.7]))
    assert result == pytest.approx(expected)
    assert cosine_overlap(pd.Series({"A": 0.0}), b) == 0.0


def test_options_are_excluded_from_emitted_shares_and_usable_coverage():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    option_mask = pd.Series([False, True, False, False], index=weights.columns)
    book = emit_13f_long_book(
        weights, _quarter_ends("2024-01", periods=1), eligible, option_mask=option_mask
    )
    row = book.iloc[0]
    assert row["A1"] == 0.0
    np.testing.assert_allclose(row[["A0", "A3"]].to_numpy(), [0.8, 0.2])
    latest = weights.iloc[-1]
    assert coverage_ratio(latest, eligible, option_mask=option_mask) == pytest.approx(0.5 / 0.7)
    assert reported_option_share(latest, eligible, option_mask) == pytest.approx(0.2 / 0.7)


def test_option_heavy_threshold_is_strictly_greater_than_ten_percent():
    eligible = pd.Series(True, index=["stock", "option"])
    option_mask = pd.Series([False, True], index=eligible.index)
    at_threshold = pd.Series({"stock": 0.9, "option": 0.1})
    above_threshold = pd.Series({"stock": 0.899, "option": 0.101})
    assert reported_option_share(at_threshold, eligible, option_mask) == pytest.approx(
        M6_OPTION_FLAG_SHARE
    )
    assert not (
        reported_option_share(at_threshold, eligible, option_mask) > M6_OPTION_FLAG_SHARE
    )
    assert reported_option_share(above_threshold, eligible, option_mask) > M6_OPTION_FLAG_SHARE


def test_coverage_denominator_is_positive_long_book_only():
    weights = pd.Series({"visible": 0.3, "hidden": 0.2, "short": -0.9})
    eligible = pd.Series({"visible": True, "hidden": False, "short": True})
    assert coverage_ratio(weights, eligible) == pytest.approx(0.6)
