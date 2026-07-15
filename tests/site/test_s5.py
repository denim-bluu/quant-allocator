import json
import shutil
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

def _load_publication_terms() -> tuple[str, ...]:
    # Source the banned terms from the gitignored canary instead of inlining
    # them in committed test source. Parsed like tools/publication_check.sh:
    # one term per line, '#' comments and blank lines skipped, lowercased.
    # Skip-if-missing: the canary is absent from git worktrees/CI, so this
    # returns () there; tools/publication_check.sh is the enforcing gate.
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


class _StructuredAttrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"data-cum-hedge", "data-cum-alpha", "data-borrow-dial"}:
                self.values.append((key, value))

S5_CARD = {
    "id": "s5",
    "title": "Short-book quality score",
    "lane": "S",
    "one_liner": "Is the short book alpha, or an expensive beta hedge? Decompose the sleeve "
                 "and price it as what it is.",
    "decisions": ["size", "redeem"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/s5-shortbook.html.j2",
    "data": "s5_shortbook.json",
    "spec": "s5-short-book-quality.md",
    "golive": {
        "data_ask": "Tier P — month-end positions with signed weights, a risk-model loadings "
                    "feed (bought), per-name borrow fees where disclosed; E buys the factor "
                    "split only; R refuses unless the manager discloses sleeve returns",
        "sample": "Decomposition and hedge share honest at any T; the alpha verdict needs "
                  "T >= 36 to render; the hit rate is gated on independent trades",
        "effort": "M (demo scope; borrow realism and FINRA adapter deferred). Upstream: the "
                  "short-side IC simulator dial (S)",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "s5_shortbook.json", site / "data" / "s5_shortbook.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "s5-short-book-quality.md",
        specs / "s5-short-book-quality.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([S5_CARD]), encoding="utf-8")
    build(site, tmp_path / "out", allow_legacy=True)
    return (tmp_path / "out" / "s5.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_assets(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s5.html" in html
    assert "assets/pages/s5.css" in html and (out / "assets" / "pages" / "s5.css").exists()
    assert "assets/s5-shortbook.js" in html and (out / "assets" / "s5-shortbook.js").exists()


def test_exhibit_explainer_present(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_two_manager_split_and_chips(tmp_path):
    html, _ = _build(tmp_path)
    assert "Saxbridge Capital" in html
    assert "Drybrook Capital" in html
    assert "Short alpha, calibrated" in html
    assert "No detectable short alpha net of borrow" in html
    # Borrow-adjusted alpha rail is an IntervalStat; the split renders >= 2 chips.
    assert html.count('class="interval-stat"') >= 2
    assert html.count("verdict-chip") >= 2
    # Hedge share renders descriptive, with the factor-offset gloss.
    assert "factor offset" in html


def test_fee_implication_line_pinned(tmp_path):
    html, _ = _build(tmp_path)
    # §3.6 wow-demo sentence — exact substring, Drybrook only.
    assert ("this sleeve is priced as alpha and measures as hedge; an index overlay "
            "replicates the hedge component at near-zero fee and no borrow") in html


def test_demo_window_copy_and_gate_toggle(tmp_path):
    html, _ = _build(tmp_path)
    text = " ".join(html.split())
    # §8 ruling 2: the "deliberately generous" sentence is required, test-pinned.
    assert "deliberately generous" in html
    # The mandatory T=60 gate-refusal toggle with the trade arithmetic.
    assert "Insufficient N" in html
    assert "385" in html and "780" in html
    assert "power-gate" in html
    assert text.count("745 round trips; 35 trades short of the 780 certification line") == 2
    assert text.count("385 round trips; 395 trades short of the 780 certification line") == 2
    assert "52.8%" not in html
    assert "t = +3.58" not in html
    assert '"hit_rate"' not in html
    assert '"hit_t"' not in html
    assert "0.527667" not in html
    assert "3.58149" not in html


def test_structured_attributes_and_default_borrow_readouts(tmp_path):
    html, _ = _build(tmp_path)
    parser = _StructuredAttrs()
    parser.feed(html)
    assert len(parser.values) == 6
    for _, value in parser.values:
        json.loads(value)
    assert 'data-borrow-dial="[{&#34;' in html
    text = " ".join(html.split())
    assert "at 2.0%/yr borrow: net +5.58% (+2.39% … +8.89%) — still calibrated" in text
    assert "at 2.0%/yr borrow: net +0.66% (-2.27% … +3.62%) — no detectable alpha" in text


def test_borrow_dial_and_tier_strip(tmp_path):
    html, _ = _build(tmp_path)
    assert "data-dial" in html                       # the Dietvorst borrow slider
    assert "manager-disclosed attribution" in html   # R-disclosed exception chip
    # Tier strip present at E and R (TierBadges on every panel).
    assert 'data-tier="E"' in html and 'data-tier="R"' in html


def test_no_banned_words(tmp_path):
    html, _ = _build(tmp_path)
    low = html.lower()
    for w in _BANNED:
        assert w not in low
