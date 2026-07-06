from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = REPO_ROOT / "site" / "assets" / "interval.css"

REQUIRED_TOKENS = [
    ".interval-stat",
    ".interval-stat__label",
    ".interval-stat__value",
    ".interval-stat__rail",
    ".interval-stat__band",
    ".interval-stat__point",
    ".interval-stat__range",
    ".power-gate",
    ".power-gate__title",
    ".power-gate__reason",
    ".tier-badge",
    ".verdict-chip",
    '[data-verdict="robust"]',
    '[data-verdict="shrink"]',
    '[data-verdict="noise"]',
    ".synthetic-badge",
    ".golive-box",
    ".usage-note",
    ".card-tile",
    ".card-tile--planned",
    ".decision-chip",
    ".pack-page",
    ".ladder-rung",
    "@media print",
    "@page",
    "prefers-reduced-motion",
    ":focus-visible",
]


def test_interval_css_defines_all_contract_classes():
    css = CSS_PATH.read_text(encoding="utf-8")
    missing = [token for token in REQUIRED_TOKENS if token not in css]
    assert not missing, f"interval.css missing: {missing}"
