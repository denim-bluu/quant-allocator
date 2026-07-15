from collections import Counter
import html
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from quant_allocator.site.build import build


REPO_ROOT = Path(__file__).resolve().parents[2]


def _built_index(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "index.html").read_text(encoding="utf-8")


def _tile_attribute(index_html, card_id, attribute):
    tile = re.search(
        rf'<article class="card-tile[^"]*"[^>]*data-card-id="{card_id}"[^>]*>',
        index_html,
    )
    assert tile is not None
    value = re.search(rf'{attribute}="([^"]*)"', tile.group(0))
    assert value is not None
    return html.unescape(value.group(1))


def test_homepage_is_an_editorial_publication_before_it_is_a_catalog(tmp_path):
    page = _built_index(tmp_path)

    assert "Evidence should change what you are allowed to say." in page
    assert "Quantitative methods for allocator decisions under partial transparency." in page
    assert 'id="start-here"' in page
    assert 'id="research"' in page
    assert 'id="featured"' in page
    assert 'id="browse"' in page
    ordered_sections = [
        page.index('id="start-here"'),
        page.index('id="research"'),
        page.index('id="featured"'),
        page.index('id="browse"'),
    ]
    assert ordered_sections == sorted(ordered_sections)

    start_here = page.split('id="start-here"', 1)[1].split('id="research"', 1)[0]
    assert re.findall(r'data-curriculum-id="([^"]+)"', start_here) == ["s2", "s1", "m3"]
    for text in (
        "Treating a point estimate as evidence.",
        "Read track-record statistics as uncertain estimates and know when to refuse a conclusion.",
        "Treating a noisy ranking as a ranking of manager skill.",
        "Understand shrinkage, partial pooling, and posterior rank uncertainty.",
        "Applying the same flat drawdown threshold to unlike managers.",
        "Compare a realized drawdown with the manager-specific null",
        "Reading time",
        "Difficulty",
        "Why this comes next",
    ):
        assert text in start_here
    assert "Tier &amp; Power Atlas" not in start_here
    assert "Transparency playground" not in start_here
    for pillar, count in (
        ("Signal &amp; skill", 7),
        ("Monitoring", 6),
        ("Portfolio decisions", 3),
        ("Evidence &amp; engagement", 4),
        ("Cross-cutting foundations", 3),
    ):
        assert pillar in page
        assert f'data-pillar-count="{count}"' in page
    assert page.count('data-card-id="') == 23


def test_homepage_article_index_links_every_idea_to_its_long_form_article(tmp_path):
    page = _built_index(tmp_path)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))

    for card in cards:
        assert f'href="specs/{card["id"]}.html">Read article</a>' in page
        assert f'href="{card["id"]}.html">View exhibit</a>' in page


def test_static_gallery_is_complete_without_javascript(tmp_path):
    html = _built_index(tmp_path)

    assert "All research" in html
    assert 'data-gallery-view="journey"' in html
    assert 'data-gallery-view="catalog"' in html
    assert ">Detailed</button>" in html
    assert ">Compact</button>" in html
    assert 'aria-pressed="true"' in html
    assert 'aria-pressed="false"' in html
    for stage in ("discover", "underwrite", "construct", "monitor", "govern"):
        assert f'id="stage-{stage}"' in html
        assert f'href="#stage-{stage}"' in html
    assert 'id="stage-mandate"' not in html
    assert "Research by allocator journey" not in html
    assert html.count('data-card-id="') == 23
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    assert f"All {len(cards)} ideas remain available when JavaScript is disabled." in html


def test_gallery_exposes_search_presets_facets_and_explicit_empty_state(tmp_path):
    html = _built_index(tmp_path)

    assert "data-gallery-search" in html
    for preset in (
        "returns-only",
        "holdings",
        "screen-managers",
        "ic-preparation",
        "credit-private",
    ):
        assert f'data-gallery-preset="{preset}"' in html
    for facet in ("stage", "asset", "vehicle", "access", "modality", "readiness"):
        assert f'data-filter-group="{facet}"' in html
    assert 'data-filter-group="attestation"' not in html
    assert "Current attestation" not in html
    assert "data-gallery-count" in html
    assert "data-gallery-empty" in html
    assert html.count("data-gallery-clear") == 1
    assert re.search(r'<a[^>]+href="index\.html"[^>]+data-gallery-clear', html)
    empty = html.split('class="gallery-empty"', 1)[1].split("</section>", 1)[0]
    assert "data-gallery-clear" not in empty
    assert "data-card='{\"" not in html


def test_static_no_javascript_count_is_derived_from_the_manifest(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "site", repo / "site")
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", repo / "docs" / "ideas" / "specs")
    shutil.copytree(
        REPO_ROOT / "docs" / "ideas" / "articles",
        repo / "docs" / "ideas" / "articles",
    )
    manifest_path = repo / "site" / "cards.yaml"
    cards = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))[:-1]
    manifest_path.write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")

    out = tmp_path / "out"
    build(repo / "site", out)
    html = (out / "index.html").read_text(encoding="utf-8")

    assert f"All {len(cards)} ideas remain available when JavaScript is disabled." in html
    assert "All 20 ideas remain available" not in html


def test_primary_stage_mapping_matches_the_approved_research_audit():
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    primary_by_id = {card["id"]: card["primary_stage"] for card in cards}
    expected = {
        "discover": {"s6", "e3", "x3"},
        "underwrite": {"s1", "s3", "s5", "e4", "s7"},
        "mandate": set(),
        "construct": {"m4", "p1", "p2"},
        "monitor": {"s2", "s4", "m1", "m2", "m3", "m5", "m6"},
        "govern": {"p3", "e1", "e2", "x1", "x2"},
    }

    for stage, card_ids in expected.items():
        assert {card_id for card_id, primary in primary_by_id.items() if primary == stage} == card_ids
    assert Counter(primary_by_id.values()) == Counter(
        {"discover": 3, "underwrite": 5, "construct": 3, "monitor": 7, "govern": 5}
    )


def test_search_corpus_contains_reader_facing_metadata_only(tmp_path):
    index = _built_index(tmp_path)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    for card in cards:
        corpus = _tile_attribute(index, card["id"], "data-search")
        for expected in (
            card["title"],
            card["one_liner"],
            card["decision_question"],
            card["minimum_data"],
        ):
            assert expected in corpus, card["id"]
        for claim in card["claims"]:
            assert claim["access_semantics"] not in corpus, card["id"]
            assert claim["current_attestation"] not in corpus.split(), card["id"]
            if "_" in claim["id"]:
                assert claim["id"] not in corpus, card["id"]


def test_home_and_exhibit_index_use_full_pillar_names(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")
    exhibits = (out / "exhibits.html").read_text(encoding="utf-8")
    article = (out / "specs" / "s1.html").read_text(encoding="utf-8")

    assert "Signal &amp; skill" in index
    assert 'class="research-entry__family"' not in index
    assert 'class="research-entry__family"' not in exhibits
    assert "Signal &amp; skill" in article
    assert "<span>S</span>" not in article


def test_tile_access_tokens_are_exactly_the_claim_access_union(tmp_path):
    index = _built_index(tmp_path)
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    for card in cards:
        claim_access = set().union(
            *(set(claim["access_contexts"]) for claim in card["claims"])
        )
        tile_access = set(_tile_attribute(index, card["id"], "data-access").split())
        claim_semantics = {claim["access_semantics"] for claim in card["claims"]}
        assert tile_access == claim_access
        assert tile_access.isdisjoint(claim_semantics)


def test_search_corpus_omits_controlled_access_semantics(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "site", repo / "site")
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", repo / "docs" / "ideas" / "specs")
    shutil.copytree(
        REPO_ROOT / "docs" / "ideas" / "articles",
        repo / "docs" / "ideas" / "articles",
    )
    manifest = repo / "site" / "cards.yaml"
    cards = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    semantics = [
        "exact-per-dataset",
        "exact-per-selected-dataset",
        "all-required-per-selected-dataset",
        "all-required-per-dataset",
        "synthetic-fixture-only",
        "refusal-in-every-context",
        "refusal-per-inadmissible-input",
    ]
    semantic_cards = cards[: len(semantics)]
    for card, semantic in zip(semantic_cards, semantics, strict=True):
        card["claims"][0]["access_semantics"] = semantic
    manifest.write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")

    out = tmp_path / "out"
    build(repo / "site", out)
    index = (out / "index.html").read_text(encoding="utf-8")

    for card, semantic in zip(semantic_cards, semantics, strict=True):
        assert semantic not in _tile_attribute(index, card["id"], "data-search")


def test_p3_does_not_advertise_drawdown_fund_support():
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    p3 = next(card for card in cards if card["id"] == "p3")
    assert "drawdown-fund" not in p3["vehicle_types"]


def test_gallery_query_state_and_filtering_are_deterministic():
    script_path = REPO_ROOT / "site" / "assets" / "gallery.js"
    harness = r"""
const assert = require('assert');
const gallery = require(process.argv[1]);
const parsed = gallery.parseQuery('?view=catalog&q=alpha&stage=monitor&stage=underwrite&asset=public-equity');
assert.equal(parsed.view, 'catalog');
assert.equal(parsed.q, 'alpha');
assert.deepEqual(parsed.facets.stage, ['monitor', 'underwrite']);
assert.deepEqual(parsed.facets.asset, ['public-equity']);
const encoded = gallery.serializeState(parsed);
assert.equal(encoded, '?view=catalog&q=alpha&stage=monitor&stage=underwrite&asset=public-equity');
const card = {
  search: 'Bayesian alpha public equity',
  stage: ['underwrite', 'construct'],
  asset: ['public-equity'], vehicle: ['pooled-fund'], access: ['shortlisted-nda'],
  modality: ['returns', 'documents'], minimumModality: ['returns'],
  readiness: ['data-conditional'], family: ['S']
};
assert.equal(gallery.matchesCard(card, parsed), true);
parsed.facets.access = ['public'];
assert.equal(gallery.matchesCard(card, parsed), false);
assert.equal(gallery.matchesCard(card, gallery.presetState('returns-only')), true);
card.minimumModality = ['returns', 'documents'];
assert.equal(gallery.matchesCard(card, gallery.presetState('returns-only')), false);
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_complete_exhibit_index_is_generated_from_the_manifest(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    page = (out / "exhibits.html").read_text(encoding="utf-8")
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))

    assert "All exhibits" in page
    assert page.count('class="exhibit-index__entry"') == 23
    for card in cards:
        assert f'href="{card["id"]}.html">View exhibit</a>' in page
        assert f'href="specs/{card["id"]}.html">Read article</a>' in page


def test_gallery_styles_cover_views_controls_empty_state_and_mobile():
    css = (REPO_ROOT / "site" / "assets" / "gallery.css").read_text(encoding="utf-8")
    required = [
        ".journey-nav",
        ".curriculum-step",
        ".exhibit-index",
        ".gallery-tools",
        ".gallery-view",
        ".gallery-search",
        ".gallery-presets",
        ".gallery-filters",
        ".gallery-empty",
        '[data-view="catalog"]',
        "@media (max-width: 640px)",
        "min-height: 44px",
    ]
    assert not [token for token in required if token not in css]

    option_rule = css.split(".gallery-filter__option {", 1)[1].split("}", 1)[0]
    assert "min-height: 44px" in option_rule

    thesis_rule = css.split(".editorial-hero h1 {", 1)[1].split("}", 1)[0]
    assert "clamp(3rem, 5vw, 4.5rem)" in thesis_rule

    mobile_thesis_rule = css.rsplit(".editorial-hero h1 {", 1)[1].split("}", 1)[0]
    assert "max-width: none" in mobile_thesis_rule
    assert "clamp(2.65rem, 12vw, 3.4rem)" in mobile_thesis_rule
