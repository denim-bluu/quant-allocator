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
    assert "assets/p2-xray.js" in html
    assert (out / "assets" / "pages" / "p2.css").exists()
    assert (out / "assets" / "p2-xray.js").exists()
    assert "specs/p2.html" in html


def test_explainer_and_binding_copy(tmp_path):
    html, _ = _build(tmp_path)
    for text in (
        "What this exhibit shows",
        "What you are looking at",
        "How to read it",
        "provisional pending the atlas exposure rows",
        "synthetic returns-regression proxy at R tier",
        "book variance omits covariance cross-terms by design",
        "overlap and crowding belong to M4",
        "refuses the fused posterior",
        "temporal filter and live information-gain atlas are wave-3 work",
    ):
        assert text in html


def test_interval_provenance_counterfactual_and_fallback_render(tmp_path):
    html, _ = _build(tmp_path)
    assert 'data-domain="book-beta"' in html
    assert html.count("p2-provenance__bar") == 15
    assert "Westermark Strategies" in html
    assert "Juniper Vale Partners" in html
    assert "Ternhaven Capital" in html
    assert html.count("p2-counterfactual") == 3
    assert "power-gate" in html
    assert "demo threshold clears under provisional tier-noise assumptions" in html
    normalized = _normalized_rendered_text(html)
    assert (
        "All-R sd 0.0611 to actual-mix sd 0.0411 gives 32.8% tightening. "
        "The every-sleeve-at-least-E counterfactual sd 0.0180 gives 70.5% "
        "tightening, above the 20.0% demo floor."
    ) in normalized
    assert "20.0%" in html
    assert "p2-reconciliation" in html


def test_gate_failure_suppresses_fusion_and_makes_reconciliation_primary(tmp_path):
    html, _ = _build(tmp_path, gate_renders=False)
    data = json.loads((REPO_ROOT / "site" / "data" / "p2_xray.json").read_text())
    manager = data["managers"][0]
    posterior_interval = (
        f"{manager['posterior']['ci_lo']:+.3f} &hellip; "
        f"{manager['posterior']['ci_hi']:+.3f}"
    )
    assert 'data-gate-state="refuse"' in html
    assert 'data-fused-output="true"' not in html
    assert "Fused book net market beta" not in html
    assert "p2-provenance__bar" not in html
    assert "p2-counterfactual" not in html
    assert "information gain does not clear" in html
    assert "p2-reconciliation--primary" in html
    assert "un-fused — tiers not reconciled" in html
    refusal = html.split('<section class="p2-refusal"', 1)[1].split("</section>", 1)[0]
    assert posterior_interval not in refusal
    assert "returns_regression_proxy" in refusal
    assert "90% interval" not in refusal
    for manager in data["managers"]:
        assert str(manager["posterior"]["ci_lo"]) not in html
        assert str(manager["posterior"]["ci_hi"]) not in html
    for fused_key in ("book", "counterfactuals", "r_noise_dial", "tier_provenance"):
        assert f'"{fused_key}":' not in html


def test_provenance_is_capital_ordered_with_accessible_table(tmp_path):
    html, _ = _build(tmp_path)
    provenance = html.split('<section class="p2-provenance"', 1)[1].split("</section>", 1)[0]
    first = provenance.index("Oakhurst Capital")
    second = provenance.index("Verling Capital")
    third = provenance.index("Ternhaven Capital")
    assert first < second < third
    assert "Provenance table alternative" in html
    assert 'class="p2-provenance-table"' in html
    for heading in ("Manager", "Tier", "Capital", "90% interval", "Variance share"):
        assert heading in html


def test_skepticism_dial_uses_precomputed_states(tmp_path):
    html, _ = _build(tmp_path)
    data = json.loads((REPO_ROOT / "site" / "data" / "p2_xray.json").read_text())
    assert html.count("p2-dial__button") == len(data["r_noise_dial"])
    assert "data-r-sd" in html
    assert "precomputed" in html
    script = (REPO_ROOT / "site" / "assets" / "p2-xray.js").read_text(encoding="utf-8")
    assert "style.left" in script
    assert "style.width" in script
    assert 'setAttribute("data-lo"' in script
    assert 'setAttribute("data-point"' in script
    assert 'setAttribute("data-hi"' in script
    assert "90%" not in script


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
