import json

import numpy as np
import pytest

from quant_allocator.demo_data import p1_allocation
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.demo_data.roster import MANAGER_NAMES


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.slow
def test_schema_and_ordering(tmp_path):
    data = _load(p1_allocation.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "p1_allocation"
    assert data["meta"]["n_managers"] == 20
    assert data["meta"]["n_draws"] == 50000
    assert data["meta"]["band_pct"] == [10, 90]
    assert data["meta"]["tau_scales"] == [0.5, 1.0, 2.0]
    managers = data["managers"]
    assert len(managers) == 20
    # Ordered by band anchor descending (the page renders rows in this order, §5).
    anchors = [m["anchor"] for m in managers]
    assert anchors == sorted(anchors, reverse=True)
    for m in managers:
        assert m["name"] in MANAGER_NAMES.values()      # fictional names only
        assert m["floor"] <= m["anchor"] <= m["ceil"]   # anchor inside its band
        assert m["q25"] <= m["q75"]
        assert 0.0 <= m["prob_positive"] <= 1.0
        assert m["advisory_band"] in {"review", "minimum", "standard", "conviction"}
        assert m["action"] in {"inside", "review"}
        assert len(m["fan"]) == 3                        # τ-scale dial states
        for f in m["fan"]:
            assert f["scale"] in (0.5, 1.0, 2.0)
            assert f["floor"] <= f["anchor"] <= f["ceil"]


@pytest.mark.slow
def test_posteriors_match_the_certified_s1_ledger(tmp_path):
    # §8.5: P1 reads posteriors from the SAME build that emits s1_ledger.json; the two can never
    # disagree. Pin P1's posterior mean per manager against the committed S1 ledger point.
    p1 = _load(p1_allocation.build(out_dir=tmp_path))
    s1 = _load(SITE_DATA_DIR / "s1_ledger.json")
    s1_mean = {m["code"]: m["posterior_alpha"]["point"] for m in s1["managers"]}
    for m in p1["managers"]:
        assert abs(m["post_mean"] - s1_mean[m["code"]]) < 1e-9


@pytest.mark.slow
def test_b10_headline_naive_weight_sits_above_its_band(tmp_path):
    # The centerpiece (§5): Cinderbank Capital (B10) — the naive OLS point weight sits ABOVE the
    # whole honest band, and its action trips a review.
    data = _load(p1_allocation.build(out_dir=tmp_path))
    b10 = next(m for m in data["managers"] if m["code"] == "B10")
    assert b10["naive_ols"] > b10["ceil"]
    assert b10["action"] == "review"
    # The headline block is precomputed for the page (CI never computes).
    assert data["headline"]["code"] == "B10"
    assert data["headline"]["naive_ols"] > data["headline"]["ceil"]


@pytest.mark.slow
def test_matched_pair_and_marginal_names(tmp_path):
    # §5 matched pair: B09 (60m, tighter sd) earns a higher floor and narrower band than B07 (36m).
    data = _load(p1_allocation.build(out_dir=tmp_path))
    by_code = {m["code"]: m for m in data["managers"]}
    b09, b07 = by_code["B09"], by_code["B07"]
    assert b09["floor"] >= b07["floor"]
    assert (b09["ceil"] - b09["floor"]) <= (b07["ceil"] - b07["floor"])
    # Marginal names: funded (anchor > eps) but band floor exactly 0% -> fund-or-not is open.
    marginal = {m["code"] for m in data["managers"] if m["fund_or_not"]}
    assert marginal                                     # non-empty
    for code in marginal:
        assert by_code[code]["floor"] == 0.0
        assert by_code[code]["anchor"] > 0.005


@pytest.mark.slow
def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = p1_allocation.build(out_dir=tmp_path).read_bytes()
    second = p1_allocation.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "p1_allocation.json").read_bytes()
    assert first == committed
