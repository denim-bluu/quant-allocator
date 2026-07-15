import re
from pathlib import Path

import yaml
from markupsafe import escape

from quant_allocator.site.build import TOKEN_LABELS, build

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
    "Manager-universe & sourcing-funnel coverage map",
    "Operational evidence & change graph",
    "Track-record provenance inspector",
]


def test_index_lists_all_cards(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "All data on this site is synthetic or public; all manager names are fictional." in index
    assert index.count("card-tile__title") == 23
    assert index.count("card-tile--planned") == 0
    for card_id in (
        "e1",
        "s1",
        "m5",
        "m1",
        "m2",
        "m3",
        "m4",
        "m6",
        "p2",
        "p3",
        "e2",
        "e3",
        "x3",
        "e4",
        "s7",
    ):
        assert f'href="specs/{card_id}.html"' in index
    assert (
        "Free quarterly 13F filings turned into reported-long concentration and "
        "persistence prompts."
    ) in index
    assert "Hybrid search is active; graph expansion remains a gated candidate." in index
    assert (
        "Posterior alpha across the roster — shrink noisy records before ranking."
        in index
    )
    assert "Choose the dials and watch honest claims dissolve into grey." in index
    for title in EXPECTED_TITLES:
        # Titles are rendered through Jinja2 with autoescape=True, so "&" in a
        # title (e.g. "Sizing & alpha-decay lab") becomes "&amp;" in the output.
        # Compare against the same escaping the renderer applies.
        assert str(escape(title)) in index
    assert len(list(out.glob("*.html"))) + len(list((out / "specs").glob("*.html"))) == 47


def test_assets_copied(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    assert (out / "assets" / "design-tokens.css").exists()
    assert (out / "assets" / "interval.js").exists()
    assert (out / "assets" / "gallery.css").exists()
    assert (out / "assets" / "gallery.js").exists()


def test_publication_assets_are_cache_busted(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")

    for asset in (
        "design-tokens.css",
        "interval.css",
        "gallery.css",
        "interval.js",
        "gallery.js",
    ):
        assert f"assets/{asset}?v=editorial-v4" in index


def test_demo_page_exposes_decision_and_evidence_context(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")

    assert 'class="card-context"' in html
    assert "Is the reported alpha robust enough to support selection or sizing?" in html
    assert "Underwrite manager and strategy" in html
    assert "Data conditional" in html
    assert "Comparable, point-in-time monthly net returns with strategy labels." in html
    assert "Current D" in html
    assert "Live ceiling B" in html


def test_publication_shell_connects_home_articles_and_exhibits(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")
    article = (out / "specs" / "s1.html").read_text(encoding="utf-8")
    exhibit = (out / "s1.html").read_text(encoding="utf-8")

    assert "QUANT ALLOCATOR" in index
    for target in ("#start-here", "#research", "#exhibits", "#browse"):
        assert f'href="{target}"' in index
    assert 'href="../index.html#research"' in article
    assert 'href="../s1.html"' in article
    assert "Open the paired exhibit" in article
    assert 'class="article-intro"' in article
    assert '<h1 id="article-title">Hierarchical Bayesian alpha engine</h1>' in article
    assert "Posterior alpha across the roster" in article
    assert "Is the reported alpha robust enough to support selection or sizing?" in article
    assert 'href="specs/s1.html"' in exhibit
    assert "Read the full article" in exhibit


def test_demo_pages_render_exactly_one_access_semantics_badge_per_claim(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))

    for card in cards:
        html = (out / f"{card['id']}.html").read_text(encoding="utf-8")
        badges = re.findall(
            r'<span class="attestation-chip access-semantics-chip" data-claim-id="([^"]+)" '
            r'data-access-semantics="([^"]+)">([^<]+)</span>',
            html,
        )
        expected = [
            (
                claim["id"],
                claim["access_semantics"],
                f"{claim['id']} · {TOKEN_LABELS[claim['access_semantics']]}",
            )
            for claim in card["claims"]
        ]
        assert badges == expected


def test_all_access_semantics_have_readable_labels():
    expected = {
        "exact-per-dataset": "Exact per dataset",
        "exact-per-selected-dataset": "Exact per selected dataset",
        "all-required-per-selected-dataset": "All required per selected dataset",
        "all-required-per-dataset": "All required per dataset",
        "synthetic-fixture-only": "Synthetic fixture only",
        "refusal-in-every-context": "Refusal in every context",
        "refusal-per-inadmissible-input": "Refusal per inadmissible input",
    }

    assert {semantic: TOKEN_LABELS.get(semantic) for semantic in expected} == expected
