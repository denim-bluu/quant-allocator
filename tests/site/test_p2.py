import html as html_lib
import json
import re
import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "p2",
    "title": "Tiered book X-ray",
    "lane": "P",
    "one_liner": "One book-level factor view fusing managers across transparency tiers.",
    "decisions": ["monitor", "size"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/p2-xray.html.j2",
    "data": "p2_xray.json",
    "spec": "p2-tiered-book-xray.md",
    "golive": {
        "data_ask": "Returns and a factor set for the full book (R), risk buckets where "
                    "disclosed (E), and dated holdings where position-transparent (P)",
        "sample": "Any tier mix renders an honest band; the information-gain claim requires "
                  "calibrated exposure-error rows and must clear the 20% floor",
        "effort": "L — static demo now; temporal filter and calibrated atlas rows in wave 3",
    },
}


def _normalized_rendered_text(rendered_html):
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", rendered_html)).split())


def _build(tmp_path, *, gate_renders=True):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    data_path = site / "data" / "p2_xray.json"
    shutil.copy(REPO_ROOT / "site" / "data" / "p2_xray.json", data_path)
    if not gate_renders:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        data["information_gate"]["gain"] = 0.10
        data["information_gate"]["renders"] = False
        data_path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "p2-tiered-book-xray.md", specs
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out, allow_legacy=True)
    return (out / "p2.html").read_text(encoding="utf-8"), out


def test_page_assets_furniture_and_spec_bridge(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert html.count("tier-badge") >= 3
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "assets/pages/p2.css" in html
    assert "assets/p2-xray.js" not in html
    assert (out / "assets" / "pages" / "p2.css").exists()
    assert (out / "assets" / "p2-xray.js").exists()
    assert "specs/p2.html" in html


def test_explainer_and_binding_copy(tmp_path):
    html, _ = _build(tmp_path)
    normalized = _normalized_rendered_text(html)
    for text in (
        "What this exhibit shows",
        "What you are looking at",
        "How to read it",
        "Current output: reconciliation only",
        "Returns regression estimate",
        "Exposure summary",
        "Position-derived exposure",
        "book variance omits covariance cross-terms by design",
        "overlap and crowding require a separate method",
        "not an operational result",
    ):
        assert text in normalized


def test_current_projection_is_reconciliation_for_both_teaching_gate_states(tmp_path):
    data = json.loads((REPO_ROOT / "site" / "data" / "p2_xray.json").read_text())
    for gate_renders in (True, False):
        html, _ = _build(tmp_path / str(gate_renders), gate_renders=gate_renders)
        assert "Current output: reconciliation only" in html
        assert 'data-current-output="reconciliation"' in html
        assert 'data-fused-output="true"' not in html
        current = html.split('data-current-output="reconciliation"', 1)[1].split(
            'class="p2-teaching-scenario"', 1
        )[0]
        assert "Fused book net market beta" not in current
        assert current.count('class="p2-manager-row"') == len(data["managers"])
        for manager in data["managers"]:
            assert manager["name"] in current
            assert f"{manager['posterior']['ci_lo']:+.3f}" in current
            assert f"{manager['posterior']['ci_hi']:+.3f}" in current
        for label in ("Returns only", "Exposure summaries", "Positions and trades"):
            assert label in current
        for internal in (
            "returns_regression_proxy",
            "exposure_summary",
            "position_derived",
            "wave-3",
            "M4",
        ):
            assert internal not in current


def test_provisional_fused_calculation_is_secondary_teaching_evidence(tmp_path):
    html, _ = _build(tmp_path)
    current_index = html.index("Current output: reconciliation only")
    teaching_index = html.index('class="p2-teaching-scenario"')

    assert current_index < teaching_index
    teaching = html[teaching_index:]
    assert "Provisional teaching calculation — not an operational result" in teaching
    assert "Fused book net market beta" in teaching
    assert teaching.count("p2-counterfactual") == 3
    assert "20.0%" in teaching


def test_public_page_omits_skepticism_dial_and_browser_recalculation(tmp_path):
    html, _ = _build(tmp_path)
    assert "p2-dial__button" not in html
    assert "data-r-sd" not in html
    assert "assets/p2-xray.js" not in html


def test_page_has_no_sentinel_leakage_or_hardcoded_headline():
    template = (REPO_ROOT / "site" / "templates" / "pages" / "p2-xray.html.j2").read_text(
        encoding="utf-8"
    )
    data = json.loads((REPO_ROOT / "site" / "data" / "p2_xray.json").read_text())
    for value in (data["book"]["point"], data["book"]["ci_lo"], data["book"]["ci_hi"]):
        assert str(value) not in template
    assert "Infinity" not in template
    assert ">None<" not in template
    assert ">null<" not in template
    assert "15-manager" not in template
    assert "90%" not in template


def test_rendered_html_has_no_publication_canary_terms(tmp_path):
    canary_path = REPO_ROOT / "tools" / ".publication_terms"
    if not canary_path.exists():
        return
    html, _ = _build(tmp_path)
    lowered = html.lower()
    for line in canary_path.read_text(encoding="utf-8").splitlines():
        term = line.strip().lower()
        if term and not term.startswith("#"):
            assert term not in lowered
