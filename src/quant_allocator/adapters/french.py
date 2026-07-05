"""Ken French data library adapter: download, cache, and parse monthly factors."""

from __future__ import annotations

import io
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

FF5_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_5_Factors_2x3_CSV.zip"
)

_MONTHLY_ROW = re.compile(r"^\s*\d{6}\s*,")


def parse_french_monthly_csv(text: str) -> pd.DataFrame:
    """Parse the monthly block of a Ken French CSV.

    The files carry a free-text preamble, a header row, YYYYMM rows, then
    annual blocks. We take the first run of YYYYMM rows and the header line
    immediately above it. Values are percentages; returned as decimals.
    """
    lines = text.splitlines()
    header: list[str] | None = None
    rows: list[list[str]] = []
    for i, line in enumerate(lines):
        if _MONTHLY_ROW.match(line):
            if header is None:
                header = [cell.strip() for cell in lines[i - 1].split(",")]
            rows.append([cell.strip() for cell in line.split(",")])
        elif header is not None:
            break
    if header is None:
        raise ValueError("no monthly data block found in French CSV")

    df = pd.DataFrame(rows, columns=header)
    month_col = header[0]
    index = pd.to_datetime(df[month_col], format="%Y%m").dt.to_period("M")
    df = df.drop(columns=[month_col]).set_index(pd.PeriodIndex(index, name="month"))
    return df.astype(float) / 100.0


def load_ff5_monthly(cache_dir: Path | None = None) -> pd.DataFrame:
    """Fama-French 5 factors + RF, monthly. Downloads and caches on first call."""
    cache_dir = cache_dir or Path.home() / ".cache" / "quant_allocator"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "ff5_monthly.csv"
    if not cache_path.exists():
        with urllib.request.urlopen(FF5_URL, timeout=30) as response:
            payload = response.read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_bytes = archive.read(archive.namelist()[0])
        parsed = parse_french_monthly_csv(csv_bytes.decode("latin-1"))
        cache_path.write_bytes(csv_bytes)
        return parsed
    try:
        return parse_french_monthly_csv(cache_path.read_text(encoding="latin-1"))
    except ValueError as error:
        raise ValueError(
            f"cached French data at {cache_path} failed to parse; delete it to force a re-download"
        ) from error
