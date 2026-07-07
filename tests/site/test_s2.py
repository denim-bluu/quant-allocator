from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "s2.html").read_text(encoding="utf-8"), out


def test_s2_provenance_and_copy(tmp_path):
    html, out = _build(tmp_path)
    # Provenance furniture from demo.html.j2.
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s2.html" in html
    assert (out / "specs" / "s2.html").exists()
    # the lead reviewer copy obligations (verbatim band labels).
    assert "95% interval" in html   # both Sharpe stats
    assert "90% interval" in html   # alpha stat
    assert "pointwise" in html      # drawdown null envelope
    # rf_annual labeled synthetic.
    assert "2.0%" in html
    assert "(synthetic)" in html


def test_s2_desmoothing_and_altbeta(tmp_path):
    html, _ = _build(tmp_path)
    # De-smoothing story: reported vs de-smoothed Sharpe side by side.
    assert "0.71" in html          # reported Sharpe point (0.708543)
    assert "0.60" in html          # de-smoothed Sharpe point (0.597257)
    # Theta shown.
    assert "0.82" in html          # theta_0 (0.824455)
    # Alt-beta VerdictChip states the label and its CI.
    assert 'class="verdict-chip"' in html
    assert "provisionally alternative beta" in html
    # Interval alpha verbatim.
    assert "+3.2%" in html         # alpha point (0.032342)
    # Two Sharpe IntervalStats + one alpha IntervalStat share the interval-stat class.
    assert html.count('class="interval-stat"') >= 3


def test_s2_drawdown_and_strip(tmp_path):
    html, _ = _build(tmp_path)
    # Drawdown chart + monthly strip SVG scaffolding rendered server-side.
    assert "s2-drawdown" in html
    assert "s2-strip" in html
    # Realized path stays within the 99th-percentile envelope (breaches_p99 == false).
    assert "within the 99th-percentile envelope" in html


def test_s2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/s2-tearsheet.js" in html
    assert (out / "assets" / "s2-tearsheet.js").exists()
