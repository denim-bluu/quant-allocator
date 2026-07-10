import json
from pathlib import Path

import pytest

from quant_allocator.demo_data import s5_shortbook
from quant_allocator.demo_data._emit import SITE_DATA_DIR

pytestmark = pytest.mark.slow  # multi-seed pipeline + bootstrap intervals; offline generator

def _load_publication_terms() -> tuple[str, ...]:
    # Source the banned terms from the gitignored canary instead of inlining
    # them in committed test source. Parsed like tools/publication_check.sh:
    # one term per line, '#' comments and blank lines skipped, lowercased.
    # Skip-if-missing: the canary is absent from git worktrees/CI, so this
    # returns () there; tools/publication_check.sh is the enforcing gate.
    canary = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not canary.exists():
        return ()
    terms = []
    for line in canary.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return tuple(terms)


_BANNED = _load_publication_terms()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_two_manager_split(tmp_path):
    data = _load(s5_shortbook.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "s5_shortbook"
    assert data["meta"]["months"] == 120
    assert data["meta"]["borrow_cost_annual"] == 0.02
    assert data["meta"]["short_trade_gate"] == 780
    split = {m["role"]: m for m in data["split"]}
    assert set(split) == {"alpha", "hedge"}
    assert split["alpha"]["name"] == "Saxbridge Capital"
    assert split["hedge"]["name"] == "Drybrook Capital"
    # §3.1: both sleeves are ~80% hedge by variance — HS alone convicts no one.
    for m in split.values():
        assert 0.70 <= m["hedge_share"] <= 0.90
        assert len(m["cum_hedge"]) == 120 and len(m["cum_alpha"]) == 120
        assert len(m["exposure_market"]) == 120


def test_verdicts_split_alpha_vs_hedge(tmp_path):
    data = _load(s5_shortbook.build(out_dir=tmp_path))
    split = {m["role"]: m for m in data["split"]}
    # Saxbridge: signal short -> calibrated. Drybrook: noise short -> no detectable + fee line.
    assert split["alpha"]["verdict"] == "Short alpha, calibrated"
    assert split["hedge"]["verdict"] == "No detectable short alpha net of borrow"
    assert split["alpha"]["fee_line"] is None
    assert "priced as alpha and measures as hedge" in split["hedge"]["fee_line"]
    # Net interval sign matches the chip.
    assert split["alpha"]["net_ci"][0] > 0.0
    assert split["hedge"]["net_ci"][0] <= 0.0


def test_borrow_dial_grid_is_precomputed(tmp_path):
    data = _load(s5_shortbook.build(out_dir=tmp_path))
    split = {m["role"]: m for m in data["split"]}
    for m in split.values():
        fees = [round(e["fee"], 4) for e in m["borrow_dial"]]
        assert fees[0] == 0.0 and fees[-1] == 0.05
        for e in m["borrow_dial"]:
            assert set(e) >= {"fee", "net", "net_ci_lo", "net_ci_hi", "calibrated"}
    # §5: Saxbridge stays calibrated across the whole 0-5% dial; Drybrook never calibrates.
    assert all(e["calibrated"] for e in split["alpha"]["borrow_dial"])
    assert not any(e["calibrated"] for e in split["hedge"]["borrow_dial"])


def test_trade_gate_toggle(tmp_path):
    data = _load(s5_shortbook.build(out_dir=tmp_path))
    for m in data["split"]:
        assert m["hit_full"]["trades"] == 745 and m["hit_full"]["renders"] is False
        assert m["hit_reduced"]["trades"] == 385 and m["hit_reduced"]["renders"] is False
        assert m["hit_full"]["gate"] == 780


def test_r_disclosed_fallback_present(tmp_path):
    data = _load(s5_shortbook.build(out_dir=tmp_path))
    for m in data["split"]:
        rd = m["r_disclosed"]
        assert 0.60 <= rd["r2"] <= 0.95
        assert rd["chip"] == "manager-disclosed attribution"


def test_no_banned_words_in_json(tmp_path):
    raw = s5_shortbook.build(out_dir=tmp_path).read_text(encoding="utf-8").lower()
    for w in _BANNED:
        assert w not in raw


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = s5_shortbook.build(out_dir=tmp_path).read_bytes()
    second = s5_shortbook.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s5_shortbook.json").read_bytes()
    assert first == committed
