import json

from quant_allocator.demo_data import s1_ledger
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_valid(tmp_path):
    data = _load(s1_ledger.build(out_dir=tmp_path))
    assert data["meta"]["n_managers"] == 20
    assert data["meta"]["credible_level"] == 0.90
    assert {g["group"] for g in data["groups"]} == {"A", "B"}
    assert len(data["managers"]) == 20
    keys = {
        "code", "group", "months", "true_alpha_annual", "ols_alpha",
        "posterior_alpha", "prob_positive", "shrinkage_weight",
        "ols_rank", "posterior_rank", "advisory_band",
    }
    for m in data["managers"]:
        assert keys <= set(m)
        assert set(m["ols_alpha"]) == {"point", "ci_lo", "ci_hi"}
        assert set(m["posterior_alpha"]) == {"point", "ci_lo", "ci_hi"}
        assert m["advisory_band"] in {"review", "minimum", "standard", "conviction"}


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = s1_ledger.build(out_dir=tmp_path).read_bytes()
    second = s1_ledger.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s1_ledger.json").read_bytes()
    assert first == committed  # regeneration matches the committed file


def test_domain_invariants(tmp_path):
    data = _load(s1_ledger.build(out_dir=tmp_path))
    for m in data["managers"]:
        w = m["shrinkage_weight"]
        assert 0.0 <= w <= 1.0
        assert 0.0 <= m["prob_positive"] <= 1.0
        group_mean = next(g["mu_hat_annual"] for g in data["groups"] if g["group"] == m["group"])
        post = m["posterior_alpha"]["point"]
        ols = m["ols_alpha"]["point"]
        assert min(ols, group_mean) - 1e-6 <= post <= max(ols, group_mean) + 1e-6
        ols_width = m["ols_alpha"]["ci_hi"] - m["ols_alpha"]["ci_lo"]
        post_width = m["posterior_alpha"]["ci_hi"] - m["posterior_alpha"]["ci_lo"]
        assert post_width <= ols_width + 1e-6

    ranks_ols = sorted(m["ols_rank"] for m in data["managers"])
    ranks_post = sorted(m["posterior_rank"] for m in data["managers"])
    assert ranks_ols == list(range(1, 21))
    assert ranks_post == list(range(1, 21))


def test_reshuffle_invariant(tmp_path):
    # The whole demo is that OLS and posterior rankings genuinely differ
    # (heavier shrinkage on shorter/noisier tracks). Conservative floor, not
    # pinned to the current count (7), so a constant flip that keeps the
    # visual alive doesn't break the test (gate hardening).
    data = _load(s1_ledger.build(out_dir=tmp_path))
    reshuffled = sum(m["ols_rank"] != m["posterior_rank"] for m in data["managers"])
    assert reshuffled >= 3
