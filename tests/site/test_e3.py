import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "e3",
    "title": "Manager knowledge graph & retrieval",
    "lane": "E",
    "one_liner": "Structured memory over letters and notes, anchored to decision hooks.",
    "decisions": ["engage", "select"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/e3-knowledge.html.j2",
    "data": "e3_knowledge.json",
    "spec": "e3-manager-knowledge-graph.md",
    "golive": {
        "data_ask": "Dated manager letters, DDQs, and meeting notes at tier R",
        "sample": "Extraction and retrieval eval gates, not a sample-size threshold",
        "effort": "M–L",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site" / "data" / "e3_knowledge.json",
        site / "data" / "e3_knowledge.json",
    )
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "e3-manager-knowledge-graph.md",
        specs / "e3-manager-knowledge-graph.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out)
    return (out / "e3.html").read_text(encoding="utf-8"), out


def _publication_terms() -> tuple[str, ...]:
    path = REPO_ROOT / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_e3_page_furniture_assets_and_explainer(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html and "golive-box" in html
    assert 'id="card-data"' in html and "specs/e3.html" in html
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html and "How to read it" in html
    assert "assets/pages/e3.css" in html and (out / "assets" / "pages" / "e3.css").exists()
    assert "assets/e3-knowledge.js" in html and (out / "assets" / "e3-knowledge.js").exists()
    for tier in ("R", "E", "P"):
        assert f'data-tier="{tier}"' in html


def test_active_hybrid_fallback_and_formal_gate_are_explicit(tmp_path):
    html, _ = _build(tmp_path)
    assert "Active retrieval: hybrid search" in html
    assert "candidate — gate not cleared" in html
    assert "Formal recall@10 is insufficient" in html
    assert "+0.10 absolute recall@10" in html
    assert "paired interval lower bound above zero" in html
    assert "Baseline recall@10" in html and "Graph-candidate recall@10" in html
    assert "1.00" in html and "0.00" in html


def test_retrieval_comparison_is_provenanced_and_illustrative(tmp_path):
    html, _ = _build(tmp_path)
    assert "Lexical only" in html
    assert "Plain hybrid" in html
    assert "Graph candidate" in html
    assert "Illustrative top-3" in html
    assert "0.67" in html and "1.00" in html
    assert "DDQ-WEX" in html and "MTG-2024-05" in html
    assert "meeting note ranks 5th" in html
    assert "Wexford distractor ranks 2nd" in html
    assert "provenance-chip" in html


def test_graph_has_all_types_signature_edge_and_clickable_receipts(tmp_path):
    html, _ = _build(tmp_path)
    for node_type in ("manager", "strategy", "person", "document", "view", "theme", "meeting"):
        assert f'data-node-type="{node_type}"' in html
    assert "employed_by" in html
    assert "Selby Point Advisors" in html
    assert "Tier R" in html and "granted 2024-01" in html
    assert 'class="e3-fact"' in html
    assert 'id="e3-provenance"' in html


def test_partial_brief_and_live_extraction_boundaries(tmp_path):
    html, _ = _build(tmp_path)
    assert "Document-native meeting brief" in html
    assert "same-manager M5 source" in html
    assert "same-manager S2 source unavailable" in html
    assert "authored concept-table stand-in" in html
    assert "precision and recall at least 0.8 per core slot" in html
    assert "before any real-document fact renders" in html
    assert "help, not an audit" in html
    assert "not a chatbot" in html
    assert "never a mechanical judgement" in html


def test_loaded_publication_terms_do_not_appear(tmp_path):
    html, _ = _build(tmp_path)
    lowered = html.lower()
    assert not any(term in lowered for term in _publication_terms())
