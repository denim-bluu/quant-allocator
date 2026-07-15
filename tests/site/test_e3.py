import shutil
import subprocess
from html.parser import HTMLParser
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
    build(site, out, allow_legacy=True)
    return (out / "e3.html").read_text(encoding="utf-8"), out


def _demo_content(html: str) -> str:
    payload_start = html.index('<script type="application/json" id="card-data">')
    payload_end = html.index("</script>", payload_start) + len("</script>")
    appendix = html.index('<details class="evidence-appendix">', payload_end)
    return html[payload_end:appendix]


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "template"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def _publication_terms() -> tuple[str, ...]:
    path = REPO_ROOT / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_e3_leads_with_ranked_results_and_formal_refusal(tmp_path):
    html, out = _build(tmp_path)
    content = _demo_content(html)

    assert "What did Corvid Lane say about liquidity in 2024?" in content
    assert "Relevant" in content
    assert "Wrong manager" in content
    assert "Missed paraphrase" in content
    assert "Formal recall@10: no measured improvement" in content
    assert "Illustrative top-three mechanism check" in content
    assert content.index("Formal recall@10") < content.index(
        "Illustrative top-three mechanism check"
    )
    assert "1.00" in content and "0.00" in content
    assert "assets/pages/e3.css" in html
    assert "assets/e3-knowledge.js" in html
    assert (out / "assets" / "pages" / "e3.css").exists()
    assert (out / "assets" / "e3-knowledge.js").exists()


def test_e3_uses_only_committed_relations_in_one_readable_path(tmp_path):
    html, _ = _build(tmp_path)
    content = _demo_content(html)

    assert 'class="e3-evidence-path"' in content
    assert "First-quarter letter" in content
    assert "authored by" in content
    assert "Elena Voss" in content
    assert "employed by" in content
    assert "Corvid Lane Capital" in content
    assert "expresses" in content
    assert "Liquidity view" in content
    assert "about theme" in content
    assert "Liquidity" in content
    assert "Underwriting question" in content
    assert "The question is a presentation endpoint, not a stored graph relation." in content
    assert 'class="e3-wrong-branch"' in content
    assert "Wexford Green Capital" in content
    assert "wrong manager" in content.lower()


def test_e3_public_copy_has_no_inventory_or_internal_identifiers(tmp_path):
    html, _ = _build(tmp_path)
    content = _visible_text(_demo_content(html))
    article = (
        REPO_ROOT / "docs" / "ideas" / "articles" / "e3-manager-knowledge-graph.md"
    ).read_text(encoding="utf-8")

    for prohibited in (
        "E3-owned",
        ">Nodes<",
        ">Edges<",
        "DDQ-2024",
        "DDQ-WEX",
        "L-2024Q1",
        "MTG-2024-05",
        "employed_by",
        "about_theme",
        "authored concept-table stand-in",
    ):
        assert prohibited not in content
        assert prohibited not in article


def test_e3_source_selection_is_accessible_and_does_not_compute(tmp_path):
    _, out = _build(tmp_path)
    script = out / "assets" / "e3-knowledge.js"
    result = subprocess.run(
        ["node", "--check", str(script)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr

    source = script.read_text(encoding="utf-8")
    for required in (
        "dataset.sourceDoc",
        'setAttribute("aria-pressed"',
        "textContent",
    ):
        assert required in source
    for prohibited in (
        "innerHTML",
        "Math.",
        ".reduce(",
        ".sort(",
        "calculate",
        "estimate",
        "traverse",
    ):
        assert prohibited not in source


def test_loaded_publication_terms_do_not_appear(tmp_path):
    html, _ = _build(tmp_path)
    lowered = html.lower()
    assert not any(term in lowered for term in _publication_terms())
