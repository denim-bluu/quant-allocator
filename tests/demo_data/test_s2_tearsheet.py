import json

from quant_allocator.demo_data import s2_tearsheet
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_valid(tmp_path):
    data = _load(s2_tearsheet.build(out_dir=tmp_path))
    assert data["meta"]["manager_code"] == "M07"
    assert data["meta"]["months"] == 48
    assert data["meta"]["tier"] == "R"
    for key in ("sharpe_reported", "sharpe_desmoothed", "alpha", "mppm"):
        assert key in data["statistics"]
    for stat in ("sharpe_reported", "sharpe_desmoothed", "alpha"):
        s = data["statistics"][stat]
        assert set(s) >= {"point", "ci_lo", "ci_hi"}
        assert s["ci_lo"] <= s["point"] <= s["ci_hi"]  # band contains its point
    assert data["alt_beta"]["chip"] in {"provisionally alternative beta", "skill supported"}
    dd = data["drawdown_band"]
    assert len(dd["realized"]) == 48
    assert len(dd["p50"]) == len(dd["p95"]) == len(dd["p99"]) == 48
    assert len(data["monthly_returns"]) == 48
    assert len(data["theta"]) == 3


def test_alt_beta_chip_matches_alpha_ci(tmp_path):
    data = _load(s2_tearsheet.build(out_dir=tmp_path))
    alpha = data["statistics"]["alpha"]
    crosses_zero = alpha["ci_lo"] <= 0.0 <= alpha["ci_hi"]
    chip = data["alt_beta"]["chip"]
    assert (chip == "provisionally alternative beta") == crosses_zero


def test_desmoothed_sharpe_not_above_reported(tmp_path):
    # S2 spec §3.1: de-smoothing restores hidden vol => de-smoothed Sharpe <= reported.
    data = _load(s2_tearsheet.build(out_dir=tmp_path))
    assert (
        data["statistics"]["sharpe_desmoothed"]["point"]
        <= data["statistics"]["sharpe_reported"]["point"] + 1e-6
    )


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = s2_tearsheet.build(out_dir=tmp_path).read_bytes()
    second = s2_tearsheet.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s2_tearsheet.json").read_bytes()
    assert first == committed
