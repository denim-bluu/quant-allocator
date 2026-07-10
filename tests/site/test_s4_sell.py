import json
import shutil
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_publication_terms() -> tuple[str, ...]:
    # Source banned terms from the gitignored canary instead of inlining them
    # in committed test source. Parsed like tools/publication_check.sh: one term
    # per line, '#' comments and blanks skipped, lowercased. Skip-if-missing:
    # canary is absent from worktrees/CI so this returns () there;
    # tools/publication_check.sh is the enforcing gate.
    canary = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not canary.exists():
        return ()
    terms = []
    for line in canary.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return tuple(terms)


_BANNED = _load_publication_terms()


class _HorizonAttrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "data-horizons":
                self.values.append(value)

# The exact fields the integration task will paste into cards.yaml to flip S4 live.
_CARD = {
    "id": "s4",
    "title": "Sell-discipline diagnostic",
    "lane": "S",
    "one_liner": "Where the edge leaks — exit timing vs a random-sell counterfactual.",
    "decisions": ["engage", "monitor"],
    "tiers": ["P", "E"],
    "status": "live",
    "demo": "pages/s4-sell.html.j2",
    "data": "s4_sell.json",
    "spec": "s4-sell-discipline.md",
    "golive": {
        "data_ask": (
            "Tier P — transaction history or monthly holdings with exit dates and "
            "security identifiers, plus a factor/risk model for residualization"
        ),
        "sample": (
            "150 exits minimum for the headline gap (~270 bp/exit leaks); ~1,900 exits "
            "for field-size effects; a 30-name low-turnover book never clears"
        ),
        "effort": "M",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "s4_sell.json", site / "data" / "s4_sell.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "s4-sell-discipline.md",
        specs / "s4-sell-discipline.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out")
    return (tmp_path / "out" / "s4.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_css(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s4.html" in html
    assert "assets/pages/s4.css" in html
    assert (out / "assets" / "pages" / "s4.css").exists()
    assert "assets/s4-sell.js" in html
    assert (out / "assets" / "s4-sell.js").exists()
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_two_manager_split_and_ghost(tmp_path):
    html, _ = _build(tmp_path)
    assert "Larkspur Ridge Partners" in html
    assert "Redgate Harbor Capital" in html
    assert "culls well" in html
    assert "edge leaks at the exit" in html
    assert "the diagnostic auditing itself" in html
    # Gap rails as IntervalStats with a zero reference (no bare points).
    assert html.count('data-domain="gap"') >= 3
    assert "interval-stat__zero" in html


def test_sign_convention_and_demo_live_disclosure(tmp_path):
    html, _ = _build(tmp_path)
    # Sign convention stated cold (spec §5 / gate-ruled copy).
    assert "positive gap = the sold names beat the book = the exits leak" in html
    # Mandatory demo-vs-live disclosure (spec §8.3, test-pinned).
    assert "ground-truth" in html
    assert "teaching-scale" in html
    assert "order\n" not in html  # sanity: sentence not truncated; see full-string check next
    assert "the measured field effect in the literature is an order\n      of magnitude smaller" in html \
        or "an order of magnitude smaller" in html


def test_horizon_slider_and_curve(tmp_path):
    html, _ = _build(tmp_path)
    assert 'id="s4-horizon"' in html
    assert "s4-curve" in html
    assert "Forward horizon" in html
    parser = _HorizonAttrs()
    parser.feed(html)
    assert len(parser.values) == 5
    for value in parser.values:
        states = json.loads(value)
        assert [state["horizon"] for state in states] == [1, 2, 3, 4, 5, 6]
    assert 'data-horizons="[{&#34;' in html


def test_horizon_control_updates_text_attributes_paths_and_rails(tmp_path):
    html, out = _build(tmp_path)
    js = (out / "assets" / "s4-sell.js").read_text(encoding="utf-8")
    for marker in (
        "dataset.lo", "dataset.point", "dataset.hi", "dataset.nExits",
        "data-horizon-value", "drawCurve",
        "interval-stat__band", "interval-stat__point",
    ):
        assert marker in js
    assert 'data-horizon-value="point"' in html
    assert 'data-horizon-value="range"' in html
    assert 'data-horizon-value="exits"' in html
    assert "quarterly toggle" not in html
    assert "tier tabs" not in html


def test_quarterly_trend_refused_with_arithmetic(tmp_path):
    html, _ = _build(tmp_path)
    assert "power-gate" in html
    assert "Quarterly trend refused" in html
    assert "exits/quarter" in html
    assert "standard error" in html


def test_tier_tabs_and_roster_not_fdr(tmp_path):
    html, _ = _build(tmp_path)
    assert "cannot be inferred from monthly returns" in html   # R-tier refusal
    assert "exit-behavior hint, not a measurement" in html      # E-tier hint
    # roster is not an FDR screen (pinned full phrase, not bare "not"/"FDR" substrings)
    assert "pooled for stability, <strong>not</strong> an\n    FDR luck-screen on alphas." in html
    # trend is descriptive, not a persistence test (pinned full phrase)
    assert "within-manager series with intervals — not a\n    persistence test" in html


def test_golive_box_values(tmp_path):
    html, _ = _build(tmp_path)
    assert "transaction history or monthly holdings" in html
    assert "150 exits minimum" in html


def test_no_banned_words(tmp_path):
    html, _ = _build(tmp_path)
    lowered = html.lower()
    for banned in _BANNED:
        assert banned not in lowered
