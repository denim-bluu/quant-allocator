import numpy as np
import pandas as pd

from quant_allocator.flagships.holdings13f.pipeline import emit_13f_long_book


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
