from pathlib import Path
from html.parser import HTMLParser

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _visible_text(html):
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def _page_content(html):
    start = html.index('<section class="saydo-intro">')
    end = html.index('<details class="evidence-appendix">', start)
    return html[start:end]


def test_m5_page_provenance_and_copy(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    # numerics gate: the delta dead-band is labeled illustrative wherever shown.
    assert "illustrative, uncalibrated" in html
    assert 'id="card-data"' in html
    assert "specs/m5.html" in html
    assert (out / "specs" / "m5.html").exists()
    # Editorial explainer: the gallery page teaches how to read the exhibit.
    assert "What this exhibit shows" in html


def test_m5_page_verdict_contract_and_quotes(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    # VerdictChip contract states present in the data (aligned + contradicted;
    # "partial" is a supported state exercised by CSS, not by this dataset).
    assert 'data-verdict="aligned"' in html
    assert 'data-verdict="contradicted"' in html
    assert 'class="verdict-chip"' in html
    # The contradiction row is the centerpiece.
    assert "saydo-row--contradicted" in html
    # Verbatim quote from the JSON (receipts always ship with claims).
    assert "crowded momentum has become" in html


def test_m5_rows_precede_guide_and_language_model_is_defined(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    content = _page_content(html)
    visible = _visible_text(content)
    assert content.index('class="saydo"') < content.index('id="m5-exhibit-shows"')
    assert "A language model is a system that turns prose into structured fields" in visible
    for prohibited in ("eval harness", "passes its gate", "live build", "receipt"):
        assert prohibited not in visible

    article = (
        REPO_ROOT / "docs" / "ideas" / "articles" / "m5-say-do-gap.md"
    ).read_text(encoding="utf-8")
    assert "A language model is a system that turns prose into structured fields" in article
    assert "receipt" not in article.lower()


def test_m5_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "assets/m5-saydo.js" in html
    assert (out / "assets" / "m5-saydo.js").exists()
