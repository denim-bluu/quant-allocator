import pandas as pd
import pytest

from quant_allocator.adapters.french import load_ff5_monthly, parse_french_monthly_csv

SAMPLE = """This file was created using the 202412 CRSP database.

,Mkt-RF,SMB,HML,RMW,CMA,RF
192607,    2.96,   -2.56,   -2.43,   -1.48,   -1.18,    0.22
192608,    2.64,   -1.17,    3.82,    0.42,    3.13,    0.25

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RMW,CMA,RF
1927,   29.47,   -2.46,   -3.75,   -1.53,   -4.30,    3.12
"""


def test_parses_monthly_block_only_as_decimals():
    df = parse_french_monthly_csv(SAMPLE)
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert df.shape == (2, 6)
    assert isinstance(df.index, pd.PeriodIndex)
    assert df.index[0] == pd.Period("1926-07", freq="M")
    assert df.loc[pd.Period("1926-07", freq="M"), "Mkt-RF"] == pytest.approx(0.0296)


def test_raises_on_text_without_monthly_block():
    with pytest.raises(ValueError, match="no monthly data block"):
        parse_french_monthly_csv("just some text\nwith no data\n")


@pytest.mark.network
def test_download_real_ff5(tmp_path):
    df = load_ff5_monthly(cache_dir=tmp_path)
    assert df.index[0] == pd.Period("1963-07", freq="M")
    assert "Mkt-RF" in df.columns
    assert len(df) > 700
