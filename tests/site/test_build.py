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
    assert len(list(out.glob("*.html"))) + len(list((out / "specs").glob("*.html"))) == 48


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
        assert f"assets/{asset}?v=editorial-v8" in index


def test_demo_page_exposes_decision_and_evidence_context(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")

    assert 'class="card-context"' in html
    assert "Is the reported alpha robust enough to support selection or sizing?" in html
    assert "Underwrite manager and strategy" in html
    assert "Data conditional" in html
    assert "Comparable, point-in-time monthly net returns with strategy labels." in html
    assert "Illustrative synthetic evidence" in html
    assert "Highest readiness with live evidence" in html
    assert "Reproducible manager output" in html
    assert "Current D" not in html
    assert "Live ceiling B" not in html
    assert "Access semantics" not in html


def test_all_exhibits_put_focal_content_before_collapsed_evidence(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))

    for card in cards:
        html = (out / f'{card["id"]}.html').read_text(encoding="utf-8")
        focal = html.index("What this exhibit shows")
        evidence = html.index("<summary>Evidence and readiness</summary>")
        article_link = html.index("Read the full article")
        assert focal < evidence < article_link, card["id"]
        appendix = html[evidence:article_link]
        assert 'class="card-context"' in appendix, card["id"]
        assert "Methodology" in appendix, card["id"]
        assert any(
            marker in appendix
            for marker in ("golive-box", "golive-replaced", "usage-note")
        ), card["id"]


def test_foundation_exhibits_continue_the_curriculum_path(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)

    s2 = (out / "s2.html").read_text(encoding="utf-8")
    s1 = (out / "s1.html").read_text(encoding="utf-8")
    m3 = (out / "m3.html").read_text(encoding="utf-8")

    assert 'class="article-continuation exhibit-continuation"' in s2
    assert 'href="s1.html"' in s2
    assert "Next in this path" in s2

    assert 'href="s2.html"' in s1
    assert 'href="m3.html"' in s1
    assert "Previous in this path" in s1
    assert "Next in this path" in s1

    assert 'href="s1.html"' in m3
    assert 'href="index.html#research"' in m3
    assert "Continue to the research pillars" in m3

    p1 = (out / "p1.html").read_text(encoding="utf-8")
    assert "exhibit-continuation" not in p1


def test_publication_shell_connects_home_articles_and_exhibits(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")
    article = (out / "specs" / "s1.html").read_text(encoding="utf-8")
    exhibit = (out / "s1.html").read_text(encoding="utf-8")

    assert "QUANT ALLOCATOR" in index
    for target in ("#start-here", "#research", "exhibits.html", "#browse"):
        assert f'href="{target}"' in index
    assert 'href="../exhibits.html"' in article
    assert 'href="exhibits.html"' in exhibit
    assert 'href="../index.html#research"' in article
    assert 'href="../s1.html"' in article
    assert "Open the paired exhibit" in article
    assert 'class="article-intro article-intro--reader"' in article
    assert '<h1 id="article-title">Hierarchical Bayesian alpha engine</h1>' in article
    assert "Posterior alpha across the roster" in article
    assert "Foundation · Step 2 of 3" in article
    assert "14 min read" in article
    assert "Technical method and provenance" in article
    assert 'href="specs/s1.html"' in exhibit
    assert "Read the full article" in exhibit


def test_demo_appendix_translates_claim_access_and_readiness(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    card = next(card for card in cards if card["id"] == "s1")
    html = (out / "s1.html").read_text(encoding="utf-8")

    assert "Access semantics" not in html
    assert "Current A" not in html
    assert "Current B" not in html
    assert "Current C" not in html
    assert "Current D" not in html
    assert "Live ceiling" not in html
    assert "Build effort" not in html
    assert "data-claim-id=" not in html
    assert "data-access-semantics=" not in html
    for claim in card["claims"]:
        assert claim["access_semantics"] not in html


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
