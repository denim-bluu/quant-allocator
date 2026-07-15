import json
import shutil
import subprocess
from html.parser import HTMLParser
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
    "golive": {
        "data_ask": "Source records linked to a typed target grid",
        "sample": "381 perfect identity links",
        "effort": "L",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site/data/x3_universe.json", site / "data/x3_universe.json"
    )
    specs = tmp_path / "docs/ideas/specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs/ideas/specs/x3-manager-universe.md",
        specs / "x3-manager-universe.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out, allow_legacy=True)
    return (out / "x3.html").read_text(encoding="utf-8"), out


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


def test_x3_server_baseline_is_a_missing_link_flow(tmp_path) -> None:
    html, out = _build(tmp_path)
    content = _demo_content(html)
    visible = _visible_text(content)

    source = content.index("Named source records")
    resolved = content.index("Resolved strategies")
    missing = content.index("Missing assignment link")
    eligible = content.index("Eligible target cells")
    refused = content.index("Coverage not calculated")
    assert source < resolved < missing < eligible < refused
    assert "835" in content
    assert "24" in content
    assert "21" in content
    assert "3 cells are outside target scope" in visible
    assert "No heat map is drawn because no strategy-to-cell assignments exist." in visible
    assert "assets/pages/x3.css" in html
    assert "assets/x3-universe.js" in html
    assert (out / "assets" / "pages" / "x3.css").exists()
    assert (out / "assets" / "x3-universe.js").exists()


def test_x3_names_the_selected_sources_without_inventing_source_counts(tmp_path) -> None:
    html, _ = _build(tmp_path)
    content = _demo_content(html)

    for source_name in (
        "Public adviser records",
        "Registered fund records",
        "Holdings filer records",
        "RFI and DDQ responses",
        "Strategy export",
    ):
        assert source_name in content
    assert "Source set: public records plus pre-hire submissions" in content
    assert "Per-source row counts are not available in this exhibit." in content


def test_x3_controls_preserve_complete_server_default_and_readable_announcements(
    tmp_path,
) -> None:
    html, out = _build(tmp_path)
    content = _demo_content(html)
    assert content.count("<select") == 3
    assert 'id="x3-cutoff"' in content
    assert 'id="x3-source"' in content
    assert 'id="x3-scope"' in content
    assert "Latest available evidence" in content
    assert "Public records plus pre-hire submissions" in content
    assert "Cross-asset research map" in content
    assert 'aria-live="polite"' in content
    assert "Showing the latest available evidence" in content

    script = out / "assets" / "x3-universe.js"
    result = subprocess.run(
        ["node", "--check", str(script)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    source = script.read_text(encoding="utf-8")
    assert "data.states[stateKey]" in source
    assert "URLSearchParams" in source and "history.replaceState" in source
    assert "history.pushState" in source
    assert "popstate" in source and ".focus()" in source
    assert "sourceLabels" in source and "scopeLabels" in source and "cutoffLabels" in source
    assert "Showing ${stateKey}" not in source
    for forbidden in (
        "Math.",
        "wilson",
        "estimate",
        "canonicalize",
        "resolveEntity",
        "conversion =",
        ".reduce(",
    ):
        assert forbidden not in source


def test_x3_public_copy_omits_raw_pointers_codes_and_registers(tmp_path) -> None:
    html, _ = _build(tmp_path)
    content = _visible_text(_demo_content(html))
    article = (
        REPO_ROOT / "docs" / "ideas" / "articles" / "x3-manager-universe.md"
    ).read_text(encoding="utf-8")

    for prohibited in (
        "receipt:",
        "sha256",
        "typed-membership-cell-projection-required",
        "typed-mandate-brief-cohort-projection-required",
        "/target_grid/",
        "/funnel/",
        "Claim access",
        "attestation",
        "dataset:x3-",
        "source_card",
        "fixture",
    ):
        assert prohibited not in content
        assert prohibited not in article
    assert "X3" not in article


def test_x3_exact_state_keys_remain_embedded_not_visible(tmp_path) -> None:
    html, _ = _build(tmp_path)
    start = html.index('<script type="application/json" id="card-data">')
    payload = html[start:].split(">", 1)[1].split("</script>", 1)[0]
    data = json.loads(payload)
    assert len(data["states"]) == 27
    assert data["meta"]["default_state"] in data["states"]
    assert data["states"][data["meta"]["default_state"]]["target_grid"]["observed_cells"] is None
    assert data["meta"]["default_state"] not in _visible_text(_demo_content(html))


def test_x3_css_is_responsive_and_preserves_large_targets() -> None:
    source = (REPO_ROOT / "site/assets/pages/x3.css").read_text(encoding="utf-8")
    assert "min-height: 44px" in source
    assert "@media (max-width: 768px)" in source
    assert "@media (max-width: 390px)" in source
    assert ":focus-visible" in source
    assert "grid-template-columns: minmax(0, 1fr)" in source
