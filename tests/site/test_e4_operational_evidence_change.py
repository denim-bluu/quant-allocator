from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "e4",
    "title": "Operational evidence & change graph",
    "lane": "E",
    "one_liner": (
        "Reconstruct dated operational facts and route evidence gaps without a scalar ODD score."
    ),
    "decisions": ["engage", "monitor", "select"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/e4-operational-evidence-change.html.j2",
    "data": "e4_operational_change.json",
    "spec": "e4-operational-evidence-change.md",
    "golive": {
        "data_ask": "Permissioned versioned operational sources with exact evidence closure.",
        "sample": "Validation coverage, not an estimator sample threshold.",
        "effort": "L",
    },
}


def _build(tmp_path: Path) -> tuple[str, Path]:
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site" / "data" / "e4_operational_change.json",
        site / "data" / "e4_operational_change.json",
    )
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "e4-operational-evidence-change.md",
        specs / "e4-operational-evidence-change.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out, allow_legacy=True)
    return (out / "e4.html").read_text(encoding="utf-8"), out


def test_page_furniture_assets_and_answer_first_copy(tmp_path: Path) -> None:
    html, out = _build(tmp_path)
    assert "SYNTHETIC DATA" in html and "golive-box" in html
    assert 'id="card-data"' in html and "specs/e4.html" in html
    assert "What this exhibit shows" in html and "How to read it" in html
    assert "Re-underwrite the evidence gaps, not a synthetic score" in html
    assert ">latest</span> ·" in html and ">all-entitled</span>" in html
    assert "committed fact, state, and queue inventories" in html
    assert "assets/pages/e4-operational-evidence-change.css" in html
    assert "assets/e4-operational-evidence-change.js" in html
    assert (out / "assets" / "pages" / "e4-operational-evidence-change.css").exists()
    assert (out / "assets" / "e4-operational-evidence-change.js").exists()
    for tier in ("R", "E", "P"):
        assert f'data-tier="{tier}"' in html


def test_e4_narrates_one_opening_state_before_advanced_tables(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)

    opening = html.index('class="e4-opening-state"')
    guide = html.index("What this exhibit shows")
    advanced = html.index('<details class="e4-advanced">')
    assert opening < guide < advanced
    opening_html = html[opening:advanced]
    assert "Latest entitled state" in opening_html
    assert "10 actions require review" in opening_html
    advanced_html = html[advanced:]
    assert "Explore the complete evidence graph" in advanced_html
    assert 'aria-label="Operational fact table"' in advanced_html


def test_e4_advanced_receipts_are_mobile_overflow_safe() -> None:
    css = (
        REPO_ROOT
        / "site"
        / "assets"
        / "pages"
        / "e4-operational-evidence-change.css"
    ).read_text(encoding="utf-8")

    selector = css.split(".e4-advanced code", 1)[1].split("}", 1)[0]
    containers = re.findall(r"\.e4-advanced \{([^}]*)\}", css)
    assert any("overflow-wrap: anywhere" in block for block in containers)
    assert "max-width: 100%" in selector
    assert "overflow-wrap: anywhere" in selector
    assert "white-space: normal" in selector


def test_controls_accessible_table_queue_and_refusal_are_server_rendered(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    assert html.count("data-e4-cutoff-control=") == 3
    assert html.count("data-e4-source-control=") == 2
    assert html.count("data-e4-panel-control=") == 3
    assert 'aria-live="polite"' in html
    assert 'scope="col"' in html and 'aria-label="Operational fact table"' in html
    assert "Categorical action queue" in html
    assert "Scalar operational judgement is refused" in html
    assert "unknown incident materiality" in html
    assert html.count("data-e4-claim-id=") == 7
    assert "refusal-per-inadmissible-input" in html
    assert "synthetic-fixture-only" in html
    assert "<noscript>" in html
    assert 'min-height: 45px' in (REPO_ROOT / "site/assets/pages/e4-operational-evidence-change.css").read_text()


def test_exact_counts_graph_table_equivalence_and_receipts_render(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    assert ">1</strong>\n    <span>corroborated" in html
    assert ">3</strong>\n    <span>asserted" in html
    assert ">3</strong>\n    <span>conflicted" in html
    assert ">3</strong>\n    <span>stale" in html
    data = json.loads((REPO_ROOT / "site/data/e4_operational_change.json").read_text())
    assert html.count("data-e4-fact-id=") == len(data["facts"])
    assert html.count("data-e4-relationship-id=") == len(data["relationships"])
    assert html.count("data-e4-relationship-row-id=") == len(data["relationships"])
    graph_ids = set(re.findall(r'data-e4-relationship-id="([^"]+)"', html))
    table_ids = set(re.findall(r'data-e4-relationship-row-id="([^"]+)"', html))
    assert graph_ids == table_ids == {row["relationship_id"] for row in data["relationships"]}
    visible_graph_ids = {
        identifier
        for identifier, attributes in re.findall(
            r'<button[^>]*data-e4-relationship-id="([^"]+)"([^>]*)>', html
        )
        if " hidden" not in attributes
    }
    visible_table_ids = {
        identifier
        for identifier, attributes in re.findall(
            r'<tr[^>]*data-e4-relationship-row-id="([^"]+)"([^>]*)>', html
        )
        if " hidden" not in attributes
    }
    assert visible_graph_ids == visible_table_ids == {
        row["relationship_id"] for row in data["relationships"]
    }
    assert 'data-e4-panel="graph" aria-labelledby="e4-graph-title" hidden' not in html
    assert "receipt:sha256:" in html


def test_all_540_display_combinations_are_precomputed_membership_only() -> None:
    data = json.loads((REPO_ROOT / "site/data/e4_operational_change.json").read_text())
    domains = ("all", "organisation", "process", "control", "provider", "incident")
    states = ("all", "corroborated", "asserted", "conflicted", "stale")
    panels = ("timeline", "graph", "table")
    combinations = list(itertools.product(data["interaction_states"], domains, states, panels))
    assert len(combinations) == 6 * 6 * 5 * 3 == 540
    for state_key, domain, evidence_state, panel in combinations:
        interaction = data["interaction_states"][state_key]
        visible = interaction["visible_id_sets"][f"{domain}|{evidence_state}|{panel}"]
        assert set(visible["fact_ids"]) <= set(interaction["fact_ids"])
        assert set(visible["change_ids"]) <= set(interaction["change_ids"])
        assert set(visible["relationship_ids"]) <= set(interaction["relationship_ids"])
        assert set(visible["queue_ids"]) <= set(interaction["queue_ids"])
        assert domain in domains and evidence_state in states and panel in panels


def test_no_javascript_fallback_keeps_full_tables_and_default_queue_visible(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    data = json.loads((REPO_ROOT / "site/data/e4_operational_change.json").read_text())
    default_key = data["meta"]["default_state"]
    fact_rows = re.findall(r'<tr data-e4-fact-id="([^"]+)"([^>]*)>', html)
    relationship_rows = re.findall(
        r'<tr data-e4-relationship-row-id="([^"]+)"([^>]*)>', html
    )
    assert len(fact_rows) == len(data["facts"]) == 32
    assert len(relationship_rows) == len(data["relationships"]) == 16
    assert {identifier for identifier, attrs in fact_rows if " hidden" not in attrs} == set(
        row["fact_id"] for row in data["facts"]
    )
    assert {
        identifier for identifier, attrs in relationship_rows if " hidden" not in attrs
    } == {row["relationship_id"] for row in data["relationships"]}
    assert html.count("data-e4-queue-id=") == len(data["reunderwriting_queue"][default_key])
    rendered_refusals = re.findall(
        r'<article data-e4-refusal-id="([^"]+)">.*?<code>([^<]*)</code>.*?</article>',
        html,
        re.DOTALL,
    )
    assert {identifier for identifier, _ in rendered_refusals} == set(
        data["interaction_states"][default_key]["data_boundary_refusal_ids"]
    )
    assert len(rendered_refusals) == 6
    assert all(receipt.startswith("receipt:sha256:") for _, receipt in rendered_refusals)

    valid_state_keys = set(data["interaction_states"])
    facts_by_id = {row["fact_id"]: row for row in data["facts"]}
    rendered_fact_receipts = re.findall(
        r'<tr data-e4-fact-id="([^"]+)"[^>]*>.*?'
        r'<small data-e4-receipt-state="([^"]+)">.*?</small>.*?'
        r'<code>(receipt:sha256:[^<]+)</code>.*?</tr>',
        html,
        re.DOTALL,
    )
    assert len(rendered_fact_receipts) == 32
    for fact_id, state_key, receipt in rendered_fact_receipts:
        row = facts_by_id[fact_id]
        expected_key = default_key if row["receipt_ids_by_state"].get(default_key) else sorted(
            key for key, value in row["receipt_ids_by_state"].items() if value
        )[0]
        assert state_key == expected_key in valid_state_keys
        assert receipt == row["receipt_ids_by_state"][expected_key]

    relationships_by_id = {row["relationship_id"]: row for row in data["relationships"]}
    rendered_relationship_receipts = re.findall(
        r'<tr data-e4-relationship-row-id="([^"]+)"[^>]*>.*?'
        r'<small data-e4-receipt-state="([^"]+)">.*?</small>.*?'
        r'<code>(receipt:sha256:[^<]+)</code>.*?</tr>',
        html,
        re.DOTALL,
    )
    assert len(rendered_relationship_receipts) == 16
    for relationship_id, state_key, receipt in rendered_relationship_receipts:
        row = relationships_by_id[relationship_id]
        expected_key = default_key if row["receipt_ids_by_state"].get(default_key) else sorted(
            key for key, value in row["receipt_ids_by_state"].items() if value
        )[0]
        assert state_key == expected_key in valid_state_keys
        assert receipt == row["receipt_ids_by_state"][expected_key]

    rendered_graph_receipts = re.findall(
        r'<button[^>]*data-e4-relationship-id="([^"]+)"[^>]*>.*?'
        r'<small data-e4-receipt-state="([^"]+)">.*?</small>.*?'
        r'<code>(receipt:sha256:[^<]+)</code>.*?</button>',
        html,
        re.DOTALL,
    )
    assert rendered_graph_receipts == rendered_relationship_receipts
    assert "JavaScript is optional" in html
    assert "full receipted cross-state audit catalog" in html
    assert (
        "Queue, counts, and six data-boundary refusals use the latest/all-entitled default."
        in html
    )


def test_javascript_is_syntax_clean_and_contains_no_estimators(tmp_path: Path) -> None:
    _, out = _build(tmp_path)
    script = out / "assets" / "e4-operational-evidence-change.js"
    subprocess.run(["node", "--check", str(script)], check=True)
    source = script.read_text(encoding="utf-8")
    for prohibited in ("age_days", "stale_threshold", "independence_groups", "choose_state"):
        assert prohibited not in source
    assert "data.state_summary" in source
    assert "interaction.visible_id_sets[displayKey()]" in source


def test_method_spec_contains_strict_math_and_render_source(tmp_path: Path) -> None:
    _, out = _build(tmp_path)
    spec_html = (out / "specs" / "e4.html").read_text(encoding="utf-8")
    assert "A_f(t)" in spec_html
    assert "freshness" in spec_html
    assert "math-render" in spec_html or "MathJax" in spec_html
