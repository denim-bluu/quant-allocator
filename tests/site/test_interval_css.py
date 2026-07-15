from pathlib import Path
import re

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
    ".card-context",
    ".card-context__facts",
    ".attestation-chip",
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


PAGE_TOKENS = [
    ".ledger",
    ".ledger-row",
    ".ledger-row--mover",
    ".rank-move--up",
    ".rank-move--down",
    ".advisory-band",
    '.verdict-chip[data-verdict="aligned"]',
    '.verdict-chip[data-verdict="partial"]',
    '.verdict-chip[data-verdict="contradicted"]',
    ".saydo-row",
    ".saydo-side--said",
    ".saydo-side--did",
    ".saydo-quote",
    ".conviction-dot",
    ".conviction-dot--on",
    ".saydo-spark__band",
    ".saydo-spark__line",
    ".saydo-illustrative",
    ".saydo--focus",
]


def test_interval_css_defines_page_classes():
    css = CSS_PATH.read_text(encoding="utf-8")
    missing = [token for token in PAGE_TOKENS if token not in css]
    assert not missing, f"interval.css missing page classes: {missing}"


def test_global_navigation_fixes_keep_skip_link_and_controls_accessible():
    css = CSS_PATH.read_text(encoding="utf-8")
    focused = re.search(r"\.skip-link:focus\s*\{(?P<body>[^}]*)\}", css)
    assert focused is not None
    assert "position: static" in focused.group("body")
    assert "position: fixed" not in focused.group("body")
    assert "min-height: 44px" in css


def test_editorial_publication_styles_cover_shell_articles_and_mobile():
    gallery = (REPO_ROOT / "site" / "assets" / "gallery.css").read_text(encoding="utf-8")
    interval = CSS_PATH.read_text(encoding="utf-8")

    for selector in (
        ".publication-header",
        ".publication-nav",
        ".publication-wordmark",
        ".article-shell",
        ".article-intro",
        ".article-intro__meta",
        ".article-link",
    ):
        assert selector in interval
    for selector in (
        ".editorial-hero",
        ".editorial-overview",
        ".start-here",
        ".pillar-guide",
        ".featured-research",
        ".research-browser",
        ".research-entry",
    ):
        assert selector in gallery
    assert "@media (max-width: 640px)" in interval
    assert "@media (max-width: 640px)" in gallery
    assert "min-height: 44px" in interval
    assert "min-height: 44px" in gallery


def test_gallery_and_context_metadata_never_drop_below_twelve_pixels():
    gallery = (REPO_ROOT / "site" / "assets" / "gallery.css").read_text(encoding="utf-8")
    interval = CSS_PATH.read_text(encoding="utf-8")

    def declaration(css, selector):
        matches = re.findall(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}", css)
        assert matches, selector
        return "\n".join(matches)

    for value, unit in re.findall(r"font-size:\s*([0-9.]+)(px|rem)", gallery):
        minimum = 12 if unit == "px" else 0.75
        assert float(value) >= minimum, f"gallery font-size {value}{unit} is below 12px"

    for selector in (
        ".gallery-intro__eyebrow",
        ".journey-nav strong",
        ".gallery-filters legend",
        ".journey-stage__header p",
        ".card-tile__facts dt",
        ".card-tile__facts dd",
    ):
        body = declaration(gallery, selector)
        assert re.search(r"font-size:\s*(?:0\.(?:7[5-9]|[89]\d)rem|[1-9]\d*rem|1[2-9]px|[2-9]\dpx)", body), selector

    for selector in (
        ".card-context__lead h2",
        ".card-context__facts dt",
        ".card-context__facts dd",
        ".badge-row .tier-badge",
        ".badge-row .synthetic-badge",
    ):
        body = declaration(interval, selector)
        assert re.search(r"font-size:\s*(?:0\.(?:7[5-9]|[89]\d)rem|[1-9]\d*rem|1[2-9]px|[2-9]\dpx)", body), selector
