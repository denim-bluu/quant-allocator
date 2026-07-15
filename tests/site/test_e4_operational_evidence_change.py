from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
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


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "template"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


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
    assert "Based only on evidence available by this cutoff" in html
    assert "assets/pages/e4-operational-evidence-change.css" in html
    assert "assets/e4-operational-evidence-change.js" in html
    assert (out / "assets" / "pages" / "e4-operational-evidence-change.css").exists()
    assert (out / "assets" / "e4-operational-evidence-change.js").exists()


def test_timeline_queue_and_refusal_precede_secondary_controls(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    timeline = html.index('class="e4-primary-timeline"')
    queue = html.index('class="e4-primary-queue"')
    refusal = html.index('class="e4-primary-refusal"')
    guide = html.index("What this exhibit shows")
    controls = html.index('class="e4-controls"')
    advanced = html.index('<details class="e4-advanced">')

    assert timeline < queue < refusal < guide < controls < advanced
    assert "Effective date" in html and "First known" in html
    assert "10 actions require review" in _visible_text(html)
    assert "A categorical work queue is shown; an operational-risk score is not calculated" in html


def test_controls_use_readable_labels_and_keep_exact_state_tokens_hidden(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    assert html.count("data-e4-cutoff-control=") == 3
    assert html.count("data-e4-source-control=") == 2
    assert "First evidence cutoff" in html
    assert "Interim evidence cutoff" in html
    assert "Latest evidence cutoff" in html
    assert "Public sources only" in html
    assert "All permitted sources" in html
    assert 'aria-live="polite"' in html
    css = (REPO_ROOT / "site/assets/pages/e4-operational-evidence-change.css").read_text()
    assert "min-height: 45px" in css


def test_no_internal_identifiers_or_governance_tokens_are_visible(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    page_local_html = '<section class="e4-boundary"' + html.split(
        '<section class="e4-boundary"', 1
    )[1].split('<details class="evidence-appendix">', 1)[0]
    visible = _visible_text(page_local_html)
    prohibited = (
        r"sha256",
        r"\bE4\b",
        r"manager:e4",
        r"operational-(?:fact|queue|change|refusal|exclusion)",
        r"receipt",
        r"reason code",
        r"output pointer",
        r"claim id",
        r"access semantics",
        r"attestation",
        r"all-entitled",
        r"public-only",
        r"latest\|",
        r"fixture",
    )
    for pattern in prohibited:
        assert re.search(pattern, visible, re.IGNORECASE) is None, (pattern, visible)


def test_default_state_preserves_exact_precomputed_timeline_and_queue(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    data = json.loads((REPO_ROOT / "site/data/e4_operational_change.json").read_text())
    default_key = data["meta"]["default_state"]
    default_state = data["interaction_states"][default_key]

    change_rows = re.findall(r'<article data-e4-change-id="([^"]+)"([^>]*)>', html)
    visible_changes = {identifier for identifier, attrs in change_rows if " hidden" not in attrs}
    assert visible_changes == set(default_state["change_ids"])
    assert html.count("data-e4-queue-id=") == len(data["reunderwriting_queue"][default_key]) == 10
    for token, count in (("corroborated", 1), ("asserted", 3), ("conflicted", 3), ("stale", 3)):
        assert re.search(
            rf'data-e4-count="{token}">{count}</strong>\s*<span>{token}</span>', html
        )
    assert "unknown incident materiality" in html


def test_supporting_tables_keep_accessible_equivalence_without_public_ids(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    data = json.loads((REPO_ROOT / "site/data/e4_operational_change.json").read_text())
    assert 'aria-label="Operational fact table"' in html
    assert html.count("data-e4-fact-id=") == len(data["facts"]) == 32
    assert html.count("data-e4-relationship-id=") == len(data["relationships"]) == 16
    assert html.count("data-e4-relationship-row-id=") == len(data["relationships"]) == 16
    assert html.count('<article class="e4-edge"') == len(data["relationships"]) == 16
    assert '<button type="button" class="e4-edge"' not in html
    assert "Relationship rows equivalent to the diagram" in html
    assert "<noscript>" in html


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


def test_javascript_is_syntax_clean_and_selects_precomputed_outputs(tmp_path: Path) -> None:
    _, out = _build(tmp_path)
    script = out / "assets" / "e4-operational-evidence-change.js"
    subprocess.run(["node", "--check", str(script)], check=True)
    source = script.read_text(encoding="utf-8")
    for prohibited in (
        "age_days",
        "stale_threshold",
        "independence_groups",
        "choose_state",
        ".reason_codes",
        "receipt_ids_by_state",
    ):
        assert prohibited not in source
    assert "cutoffLabels" in source and "sourceLabels" in source
    assert "interaction.visible_id_sets[displayKey()]" in source
    assert "renderQueue" in source


def test_method_spec_contains_strict_math_and_render_source(tmp_path: Path) -> None:
    _, out = _build(tmp_path)
    spec_html = (out / "specs" / "e4.html").read_text(encoding="utf-8")
    assert "A_f(t)" in spec_html
    assert "freshness" in spec_html
    assert "math-render" in spec_html or "MathJax" in spec_html
