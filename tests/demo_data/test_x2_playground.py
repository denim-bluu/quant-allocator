import json

import pytest

from quant_allocator.demo_data import x2_playground, x_grid
from quant_allocator.demo_data._emit import SITE_DATA_DIR

# Every test here builds off x_grid.build_grid() with the real N_REPS=500 grid.
# On a cold site/_grid_cache/ (gitignored — absent on a fresh checkout) the
# first invocation in the whole test session runs the full 30-config
# multiprocessing build (~4-5 min); once that cache is warm, later invocations
# in this file and in later test sessions are fast. Follows the existing
# slow-marker convention (test_x_grid.py, test_x_grid_timing.py).
pytestmark = pytest.mark.slow


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_cell_count(tmp_path):
    data = _load(x2_playground.build(out_dir=tmp_path))
    assert data["meta"]["n_cells"] == 450
    assert data["meta"]["n_reps"] == x_grid.N_REPS
    assert len(data["cells"]) == 450
    # A known cell tuple is addressable and carries alpha + sharpe.
    key = x2_playground._cell_key(0.10, 12.0, 0.8, 120, "P")
    cell = data["cells"][key]
    assert set(cell) >= {"alpha", "sharpe", "hit_rate", "sizing_slope"}
    alpha = cell["alpha"]
    # Short-array payload: [point, lo, hi, verdict, gate_state, threshold, units, wilson_hw].
    assert len(alpha) == 8
    assert alpha[1] <= alpha[0] <= alpha[2]  # band contains point
    assert alpha[3] in {"robust", "shrink", "noise"}
    assert alpha[4] in {"open", "closed"}


def test_budget_under_300kb(tmp_path):
    path = x2_playground.build(out_dir=tmp_path)
    assert path.stat().st_size <= x2_playground.MAX_BYTES


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = x2_playground.build(out_dir=tmp_path).read_bytes()
    second = x2_playground.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "x2_playground.json").read_bytes()
    assert first == committed


def test_null_threshold_cell_serializes_to_json_null(tmp_path):
    # CRITICAL serialization rule: float("inf") is a valid in-memory threshold
    # (a metric/tier pair whose power curve never reaches the gate target) but
    # json.dumps cannot emit it, so _short_payload must map it to None (JSON
    # null) before write_json ever sees it.
    data = _load(x2_playground.build(out_dir=tmp_path))
    null_thresholds = [
        (key, name, arr)
        for key, cell in data["cells"].items()
        for name, arr in cell.items()
        if arr[5] is None
    ]
    if null_thresholds:
        key, name, arr = null_thresholds[0]
        assert arr[4] == "closed", f"{key}/{name}: null threshold can never be cleared"
    else:
        # No inf threshold occurs in the actual grid: cover the serializer
        # helper directly instead, so the mapping is still exercised.
        payload = {
            "point": 0.0, "lo": 0.0, "hi": 0.0, "verdict": "noise",
            "gate_state": "closed", "threshold": float("inf"),
            "gate_quantity": 24.0, "units": "months", "wilson_hw": 0.0,
        }
        assert x2_playground._short_payload(payload)[5] is None
