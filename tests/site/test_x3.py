import json
import re
import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]
_CARD = {
    "id": "x3",
    "title": "Manager-universe & sourcing-funnel coverage map",
    "lane": "X",
    "one_liner": "Source-conditioned coverage without a global denominator.",
    "decisions": ["discover", "underwrite", "govern"],
    "tiers": ["P", "E", "R"],
    "status": "live",
    "demo": "pages/x3-universe.html.j2",
    "data": "x3_universe.json",
    "spec": "x3-manager-universe.md",
    "golive": {"data_ask": "Receipted typed projections", "sample": "381 perfect links", "effort": "L"},
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site/data/x3_universe.json", site / "data/x3_universe.json")
    specs = tmp_path / "docs/ideas/specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs/ideas/specs/x3-manager-universe.md", specs / "x3-manager-universe.md")
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out, allow_legacy=True)
    return (out / "x3.html").read_text(encoding="utf-8"), out


def test_server_baseline_is_complete_accessible_and_disclosed(tmp_path) -> None:
    html, out = _build(tmp_path)
    assert "This map measures the named sources and funnel, not the manager universe of the world." in html
    assert "It prioritizes research cells, never managers." in html
    assert "What this exhibit shows" in html and "specs/x3.html" in html
    assert "synthetic-badge" in html and "golive-box" in html
    assert 'aria-live="polite"' in html
    assert "Source and receipt table" in html and "Excluded target cells" in html
    assert "Claim access, attestation, and refusal register" in html
    assert html.count("Current D · live ceiling") >= 12
    for claim_id in ("global_universe_coverage", "manager_quality_ranking"):
        claim_row = re.search(
            rf"<tr><td><code>{claim_id}</code>.*?</tr>",
            html,
            flags=re.DOTALL,
        )
        assert claim_row is not None
        assert "Current D · live ceiling D" in claim_row.group()
        assert "live ceiling none" not in claim_row.group()
    assert "public, pre-hire-public, shortlisted-nda, internal-governance" in html
    assert html.count("receipt:sha256:") >= 12
    assert "assets/pages/x3.css" in html and (out / "assets/pages/x3.css").exists()
    assert "assets/x3-universe.js" in html and (out / "assets/x3-universe.js").exists()


def test_controls_are_native_and_default_content_survives_without_javascript(tmp_path) -> None:
    html, _ = _build(tmp_path)
    assert html.count("<select") == 3
    assert 'id="x3-cutoff"' in html and 'id="x3-source"' in html and 'id="x3-scope"' in html
    assert "latest" in html and "public-plus-prehire" in html and "cross-asset" in html
    assert "typed-membership-cell-projection-required" in html
    assert "typed-mandate-brief-cohort-projection-required" in html
    assert "Conversion interval: refused" in html


def test_precomputed_js_has_exact_lookup_url_focus_and_no_estimators() -> None:
    script = (REPO_ROOT / "site/assets/x3-universe.js").read_text(encoding="utf-8")
    assert "data.states[stateKey]" in script
    assert "URLSearchParams" in script and "history.replaceState" in script
    assert "history.pushState" in script
    assert "popstate" in script and ".focus()" in script
    assert "x3-live" in script and "unsupported-state-key" in script
    assert 'document.getElementById("x3-live").textContent = `Showing ${stateKey}.`' in script
    forbidden = ("Math.", "wilson", "estimate", "canonicalize", "resolveEntity", "conversion =")
    assert not any(token in script for token in forbidden)


def test_exact_state_keys_are_embedded_and_no_truth_labels_leak(tmp_path) -> None:
    html, _ = _build(tmp_path)
    start = html.index('<script type="application/json" id="card-data">')
    payload = html[start:].split(">", 1)[1].split("</script>", 1)[0]
    data = json.loads(payload)
    assert len(data["states"]) == 27
    assert data["meta"]["default_state"] in data["states"]
    assert "truth" not in json.dumps(data["states"]).lower()
