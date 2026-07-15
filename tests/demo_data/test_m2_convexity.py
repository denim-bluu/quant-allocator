import json

import pytest

from quant_allocator.demo_data import m2_convexity
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.flagships.convexity.screen import M2_COMPOSITE_K
from quant_allocator.flagships.convexity.diagnostics import M2_COSKEW_BAND


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_valid(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    assert data["meta"]["coskew_band"] == M2_COSKEW_BAND == 0.35
    assert data["meta"]["months"] == 48
    assert data["meta"]["tier"] == "R"
    assert set(data["managers"]) == {"honest", "overlaid"}
    assert len(data["market_returns"]) == data["meta"]["months"] == 48
    for m in data["managers"].values():
        assert len(m["monthly_returns"]) == len(data["market_returns"])
        assert set(m["sharpe"]) >= {"point", "ci_lo", "ci_hi"}
        diags = m["screen"]["diagnostics"]
        assert set(diags) == {
            "treynor_mazuy", "updown_beta", "market_coskew", "drawdown_vol", "straddle_loading"
        }
        for name, d in diags.items():
            if d["played"]:
                assert d["ci_lo"] <= d["point"] <= d["ci_hi"]
        assert diags["straddle_loading"]["played"] is False
    # DK-7 ruling: the demo premium is a flat carry set RICH of the payouts' fair value.
    assert data["overlay"]["fair_premium"] is False
    assert data["overlay"]["premium_annual"] > data["overlay"]["fair_value_annual"] > 0.0
    assert len(data["stress_months"]) >= 1


def test_payoff_observations_keep_market_and_manager_months_aligned(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    honest, overlaid, market, _ = m2_convexity._simulate_pair()

    assert data["market_returns"] == pytest.approx(market.to_numpy(), abs=1e-6)
    assert data["managers"]["honest"]["monthly_returns"] == pytest.approx(
        honest.to_numpy(), abs=1e-6
    )
    assert data["managers"]["overlaid"]["monthly_returns"] == pytest.approx(
        overlaid.to_numpy(), abs=1e-6
    )


def test_paired_sharpe_is_matched_to_two_decimals(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    honest = data["managers"]["honest"]["sharpe"]["point"]
    overlaid = data["managers"]["overlaid"]["sharpe"]["point"]
    assert round(honest, 2) == round(overlaid, 2)
    # DK-7 ruling: the pair matches at a HEALTHY Sharpe, not a degenerate near-zero one.
    assert honest > 0.5


def test_overlaid_flags_but_honest_does_not(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    assert data["managers"]["overlaid"]["screen"]["composite"]["chip"] == "shrink"
    assert data["managers"]["overlaid"]["screen"]["composite"]["short_vol_count"] >= M2_COMPOSITE_K
    assert data["managers"]["honest"]["screen"]["composite"]["chip"] == "noise"


def test_powergate_open_at_t48(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    assert data["managers"]["overlaid"]["screen"]["power_gate"]["open"] is True


def test_stress_month_shows_divergence(tmp_path):
    data = _load(m2_convexity.build(out_dir=tmp_path))
    worst = min(data["stress_months"], key=lambda s: s["overlaid_return"])
    # On the stress month the overlaid manager bled relative to the honest one.
    assert worst["overlaid_return"] < worst["honest_return"]
    assert worst["payout"] > 0.0


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m2_convexity.build(out_dir=tmp_path).read_bytes()
    second = m2_convexity.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "m2_convexity.json").read_bytes()
    assert first == committed
