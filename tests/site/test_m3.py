import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "m3",
    "title": "Simulation-calibrated drawdown alarms",
    "lane": "M",
    "one_liner": "Drawdown alarms tuned to each manager's own null, not a flat rule.",
    "decisions": ["redeem", "monitor"],
    "tiers": ["R", "E"],
    "status": "live",
    "demo": "pages/m3-alarms.html.j2",
    "data": "m3_alarms.json",
    "spec": "m3-drawdown-alarms.md",
    "golive": {
        "data_ask": "Monthly net returns (R) + a maintained Sharpe + a risk-free series",
        "sample": "Any T; detection improves with T",
        "effort": "S",
    },
}


def _build(tmp_path):
    # Adapts the S2/X1 idiom: the card is 'planned' in the real manifest, so build a tmp site
    # with a fixture cards.yaml that flips m3 live (this plan must not touch site/cards.yaml).
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "m3_alarms.json", site / "data" / "m3_alarms.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "m3-drawdown-alarms.md",
        specs / "m3-drawdown-alarms.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out")
    return (tmp_path / "out" / "m3.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_css(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/m3.html" in html
    assert "assets/pages/m3.css" in html
    assert (out / "assets" / "pages" / "m3.css").exists()
    assert "assets/m3-alarms.js" in html
    assert (out / "assets" / "m3-alarms.js").exists()
    # Editorial explainer block (deliverable 2).
    assert "What this exhibit shows" in html


def test_two_manager_split_green_vs_red(tmp_path):
    html, _ = _build(tmp_path)
    # The centerpiece: same -12%, opposite verdicts, each an outline VerdictChip.
    assert "Windward Trend Partners" in html
    assert "Stillwater Credit Partners" in html
    assert html.count('class="verdict-chip"') >= 2
    assert 'data-verdict="green"' in html
    assert 'data-verdict="red"' in html
    # Realized MDD rendered as an IntervalStat (null 95th-99th band around the realized point).
    assert html.count('class="interval-stat"') >= 2
    # Calibrated statement, never a bare threshold (spec §3.3, §6 receipts).
    assert "percentile" in html
    assert "maintained Sharpe" in html


def test_roster_heat_list_and_gate_copy(tmp_path):
    html, _ = _build(tmp_path)
    # Roster heat-list prints its expected-false-RED count (spec §3.4).
    assert "expected by chance" in html
    # Gate rulings as verbatim copy obligations.
    assert "per review window" in html          # budgets are per-review-window (gate)
    assert "full evaluated track" in html       # ALARM_WINDOW v1 (gate)
    assert "not a" in html and "FDR" in html     # distinction from the prohibited FDR alpha-screen
    # PowerGate refusal: detection is low-power at T <= 60.
    assert "power-gate" in html
    assert "T &le; 60" in html or "T ≤ 60" in html


def test_dietvorst_dial_is_precomputed(tmp_path):
    html, _ = _build(tmp_path)
    # The skepticism slider snaps among precomputed fan states (x2 idiom); no client computation.
    assert "data-dial" in html or "m3-dial" in html
