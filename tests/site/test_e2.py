import shutil

import yaml

from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_with_e2_live(tmp_path):
    # E2 is `planned` in the committed manifest and cards.yaml is a prohibited
    # shared seam, so the page is built from a tmp copy of the site with e2
    # flipped live (the S2/X1 build-test idiom, adapted to a planned card).
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site", site)
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", tmp_path / "docs" / "ideas" / "specs")

    cards_path = site / "cards.yaml"
    cards = yaml.safe_load(cards_path.read_text(encoding="utf-8"))
    for card in cards:
        if card["id"] == "e2":
            card["status"] = "live"
            card["demo"] = "pages/e2-pack.html.j2"
            card["data"] = "e2_pack.json"
            card["spec"] = "e2-engagement-pack.md"
            card["golive"] = {
                "data_ask": "None of its own — inherits each section's ask",
                "sample": "Inherited — the X1 PowerGate registry gates each section",
                "effort": "S",
            }
    cards_path.write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")

    out = tmp_path / "out"
    build(site, out)
    return (out / "e2.html").read_text(encoding="utf-8"), out


def test_e2_provenance_furniture(tmp_path):
    html, out = _build_with_e2_live(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/e2.html" in html
    assert (out / "specs" / "e2.html").exists()


def test_e2_renders_the_three_section_states(tmp_path):
    html, _ = _build_with_e2_live(tmp_path)
    # Rendered tear sheet.
    assert "Honest tear sheet" in html
    assert html.count('class="interval-stat"') >= 3
    assert 'class="verdict-chip"' in html
    assert "provisionally alternative beta" in html
    # Refused posterior standing renders the PowerGate empty-state (content).
    assert "Posterior skill standing" in html
    assert 'class="power-gate"' in html
    assert "no tenure" in html
    # Omitted-and-footnoted: never silently dropped.
    assert "Exposure hygiene &amp; drift" in html or "Exposure hygiene & drift" in html
    assert "shown at tier E" in html


def test_e2_certified_numbers_render_verbatim(tmp_path):
    html, _ = _build_with_e2_live(tmp_path)
    assert "0.71" in html       # reported Sharpe
    assert "0.60" in html       # de-smoothed Sharpe
    assert "+3.2%" in html      # alpha point
    assert "95% interval" in html
    assert "90% interval" in html


def test_e2_print_furniture_and_script(tmp_path):
    html, out = _build_with_e2_live(tmp_path)
    assert 'class="pack-page"' in html           # print @page container (interval.css)
    assert "pack-section__prov" in html          # per-section provenance survives paper (INV-4)
    assert "assets/e2-pack.js" in html
    assert (out / "assets" / "e2-pack.js").exists()
    assert (out / "assets" / "pages" / "e2-pack.css").exists()


def test_e2_honesty_note_states_hand_authored(tmp_path):
    html, _ = _build_with_e2_live(tmp_path)
    assert "hand-authored" in html or "human-edited" in html


def test_e2_gallery_explainer_present(tmp_path):
    html, _ = _build_with_e2_live(tmp_path)
    assert "What this exhibit shows" in html
