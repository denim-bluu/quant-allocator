import numpy as np
import pandas as pd

from quant_allocator.flagships.holdings13f.pipeline import emit_13f_long_book


def _panel():
    months = pd.period_range("2024-01", periods=6, freq="M", name="month")
    assets = pd.Index([f"A{i}" for i in range(4)], name="asset")
    # A0,A1 long; A2 short; A3 long. Quarter-ends: 2024-03, 2024-06.
    data = np.tile([0.4, 0.2, -0.3, 0.1], (6, 1))
    return pd.DataFrame(data, index=months, columns=assets)


def test_longs_only_and_renormalized_to_shares():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = pd.period_range("2024-03", periods=2, freq="3M")
    book = emit_13f_long_book(weights, q, eligible)
    # short A2 dropped; longs 0.4/0.2/0.1 renormalize to 4/7, 2/7, 1/7.
    row = book.loc[book.index[0]]
    assert row["A2"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1", "A3"]].to_numpy(), [4 / 7, 2 / 7, 1 / 7])
    assert np.isclose(row.sum(), 1.0)


def test_ineligible_names_are_cropped_before_renormalization():
    weights = _panel()
    eligible = pd.Series([True, True, True, False], index=weights.columns)  # A3 ineligible
    q = pd.period_range("2024-03", periods=1, freq="3M")
    book = emit_13f_long_book(weights, q, eligible)
    row = book.loc[book.index[0]]
    assert row["A3"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1"]].to_numpy(), [4 / 6, 2 / 6])


def test_emitter_is_deterministic_and_rng_free():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = pd.period_range("2024-03", periods=2, freq="3M")
    pd.testing.assert_frame_equal(
        emit_13f_long_book(weights, q, eligible), emit_13f_long_book(weights, q, eligible)
    )
