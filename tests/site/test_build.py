from pathlib import Path

from markupsafe import escape

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TITLES = [
    "Hierarchical Bayesian alpha engine",
    "Uncertainty-honest tear-sheet engine",
    "Sizing & alpha-decay lab",
    "Sell-discipline diagnostic",
    "Short-book quality score",
    "Returns-only sizing & decay signatures",
    "Exposure hygiene & drift monitor",
    "Hidden-convexity / short-vol screen",
    "Simulation-calibrated drawdown alarms",
    "Crowding & overlap radar",
    "Say–do gap monitor",
    "13F long-book intelligence",
    "Allocation under alpha uncertainty",
    "Tiered book X-ray",
    "Hire/fire decision audit & journal",
    "Trust-preserving transparency ladder",
    "Narrated engagement-pack generator",
    "Manager knowledge graph & retrieval",
    "Tier & Power Atlas",
    "Transparency playground",
]


def test_index_lists_all_cards(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "All data on this site is synthetic or public." in index
    assert index.count("card-tile__title") == 20
    # NOTE: Task 6 flips e1 to live; update this count to 19 there.
    assert index.count("card-tile--planned") == 20
    for title in EXPECTED_TITLES:
        # Titles are rendered through Jinja2 with autoescape=True, so "&" in a
        # title (e.g. "Sizing & alpha-decay lab") becomes "&amp;" in the output.
        # Compare against the same escaping the renderer applies.
        assert str(escape(title)) in index


def test_assets_copied(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    assert (out / "assets" / "design-tokens.css").exists()
    assert (out / "assets" / "interval.js").exists()
