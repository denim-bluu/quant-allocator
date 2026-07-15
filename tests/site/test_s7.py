from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_ALL_CONTEXTS = [
    "public",
    "pre-hire-public",
    "shortlisted-nda",
    "funded-commingled",
    "funded-private-partnership",
    "segregated-mandate",
]
_PERMISSIONED = _ALL_CONTEXTS[2:]


def _claim(
    claim_id: str,
    output_type: str,
    contexts: list[str],
    ceiling: str,
    refusal: str,
    *,
    access_semantics: str = "all-required-per-selected-dataset",
) -> dict[str, object]:
    return {
        "id": claim_id,
        "output_type": output_type,
        "access_contexts": contexts,
        "access_semantics": access_semantics,
        "current_attestation": "D",
        "live_attestation_ceiling": ceiling,
        "validation_status": "live-calibration-required",
        "receipt_required": True,
        "refusal": refusal,
    }


_CARD = {
    "id": "s7",
    "title": "Track-record provenance inspector",
    "lane": "S",
    "one_liner": (
        "Separate knowable history from later backfills, basis breaks, and unsupported "
        "predecessor claims."
    ),
    "decision_question": (
        "Is this track record complete, comparable, point-in-time, and portable to the "
        "current team and process?"
    ),
    "primary_stage": "underwrite",
    "stages": ["discover", "underwrite", "monitor", "govern"],
    "decisions": ["discover", "underwrite", "monitor", "govern"],
    "asset_classes": [
        "public-equity",
        "hedge-funds",
        "fixed-income-credit",
        "private-credit",
        "private-equity",
    ],
    "vehicle_types": ["pooled-fund", "segregated-mandate", "drawdown-fund"],
    "access_contexts": _ALL_CONTEXTS,
    "supported_data_modalities": [
        "returns",
        "cashflows-nav",
        "documents",
        "filings",
        "mandate-terms",
    ],
    "minimum_data_modalities": ["returns"],
    "minimum_data": "Versioned return or cash-flow records with lineage and basis.",
    "decision_readiness": "data-conditional",
    "evidence_roles": ["operational-analysis", "governance-workflow"],
    "validation_status": "live-calibration-required",
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/s7-provenance.html.j2",
    "data": "s7_provenance.json",
    "spec": "s7-track-record-provenance.md",
    "claims": [
        _claim("track_lineage", "exact-measurement", _ALL_CONTEXTS, "B", "Missing lineage."),
        _claim("point_in_time_vintage_audit", "exact-measurement", _ALL_CONTEXTS, "B", "Missing vintages."),
        _claim("basis_breaks", "verdict", _ALL_CONTEXTS[1:], "B", "Incomparable basis."),
        _claim("comparable_native_panel", "exact-measurement", _ALL_CONTEXTS[1:], "B", "Panel gates fail."),
        _claim("predecessor_portability_evidence", "verdict", _PERMISSIONED, "C", "Missing transfer evidence."),
        _claim("historical_selection_refusal", "refusal", _ALL_CONTEXTS, "B", "Historical denominator is unavailable."),
        _claim(
            "performance_estimator_refusal",
            "refusal",
            _ALL_CONTEXTS,
            "D",
            "No performance estimate is produced.",
            access_semantics="refusal-in-every-context",
        ),
    ],
    "golive": {
        "data_ask": "Archived source versions with complete lineage and basis.",
        "sample": "One permissioned case per intended source shape.",
        "effort": "Reconcile source schemas and independently reproduce one panel.",
    },
}


def _build(tmp_path: Path) -> tuple[str, Path]:
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site" / "data" / "s7_provenance.json",
        site / "data" / "s7_provenance.json",
    )
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "s7-track-record-provenance.md",
        specs / "s7-track-record-provenance.md",
    )
    (site / "cards.yaml").write_text(
        yaml.safe_dump([_CARD], sort_keys=False), encoding="utf-8"
    )
    out = tmp_path / "out"
    build(site, out)
    return (out / "s7.html").read_text(encoding="utf-8"), out


def _demo_content(html: str) -> str:
    payload_start = html.index('<script type="application/json" id="card-data">')
    payload_end = html.index("</script>", payload_start) + len("</script>")
    appendix = html.index('<details class="evidence-appendix">', payload_end)
    return html[payload_end:appendix]


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "template"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def test_s7_server_default_is_a_source_to_decision_flow(tmp_path: Path) -> None:
    html, out = _build(tmp_path)
    content = _demo_content(html)
    visible = _visible_text(content)

    source = content.index("Source observations")
    checks = content.index("Identity and basis checks")
    admitted = content.index("Admitted panel")
    excluded = content.index("Kept out")
    assert source < checks < admitted
    assert source < checks < excluded
    assert "7 records attach to one exact lineage segment" in content
    assert "17 records stay outside that lineage" in content
    assert "3 comparable monthly returns" in content
    assert "One return is excluded because it is reported on an incompatible fee basis." in content
    assert "Documented lineage is not evidence that historical skill transferred." in visible
    assert "assets/s7-provenance.css" in html
    assert "assets/s7-provenance.js" in html
    assert (out / "assets" / "s7-provenance.css").exists()
    assert (out / "assets" / "s7-provenance.js").exists()


def test_s7_separates_effective_and_first_known_dates(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    content = _demo_content(html)
    visible = _visible_text(content)

    assert "Effective date" in content
    assert "29 February 2024" in content
    assert "First known" in content
    assert "15 September 2024" in content
    assert "The later publication date prevents this revision from entering an earlier decision." in visible


def test_s7_controls_explore_precomputed_states_without_rewriting_the_focal_flow(
    tmp_path: Path,
) -> None:
    html, out = _build(tmp_path)
    content = _demo_content(html)
    explorer = content.index('<details class="s7-explorer">')
    summary = content.index("<summary>Explore another evidence state</summary>", explorer)
    controls = content.index('<section class="s7-controls"', explorer)
    announcement = content.index('data-s7-announcer', explorer)
    result = content.index('data-s7-explorer-body', explorer)
    assert explorer < summary < controls < announcement < result
    assert '<details class="s7-explorer" open' not in content
    assert html.count("data-s7-scenario-control=") == 4
    assert html.count("data-s7-cutoff-control=") == 2
    assert html.count("data-s7-view-control=") == 3
    assert 'aria-live="polite"' in content
    assert "data-s7-conclusion" not in content
    assert "Complete opening example" in content

    script = out / "assets" / "s7-provenance.js"
    result = subprocess.run(
        ["node", "--check", str(script)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    source = script.read_text(encoding="utf-8")
    for required in (
        "data.states[key]",
        'data.meta.default_state.split("|")',
        "URLSearchParams",
        "pushState",
        "replaceState",
        'addEventListener("popstate"',
        "active.focus()",
        "textContent",
        "createElement",
    ):
        assert required in source
    for prohibited in (
        "[data-s7-conclusion]",
        "innerHTML",
        ".sort(",
        ".join(",
        ".reduce(",
        "Math.",
        "calculate",
        "estimator(",
        "selectRevision",
        "compareBasis",
        "convertFx",
    ):
        assert prohibited not in source


def test_s7_public_copy_omits_raw_identifiers_and_process_codes(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    content = _visible_text(_demo_content(html))
    article = (
        REPO_ROOT / "docs" / "ideas" / "articles" / "s7-track-record-provenance.md"
    ).read_text(encoding="utf-8")

    for prohibited in (
        "sha256",
        "receipt:",
        "Current D",
        "live ceiling",
        "hedge-fund|early|lineage",
        "fee-basis-incomparable",
        "entity-mapping-ambiguous",
        "membership-absence-not-inferable",
        "reason code",
    ):
        assert prohibited not in content
        assert prohibited not in article
    assert not re.search(r"\bS7\b", article)


def test_s7_css_is_responsive_and_controls_are_accessible() -> None:
    source = (REPO_ROOT / "site" / "assets" / "s7-provenance.css").read_text(
        encoding="utf-8"
    )
    assert "min-height: 44px" in source and "min-width: 44px" in source
    assert ":focus-visible" in source
    assert "@media (max-width: 768px)" in source
    assert "@media (max-width: 390px)" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert 'button[aria-pressed="true"]' in source
    assert "grid-template-columns: minmax(0, 1fr)" in source


def _source_math(source: str) -> list[str]:
    without_fences = re.sub(r"```.*?```", "", source, flags=re.DOTALL)
    displays = re.findall(r"(?<!\\)\$\$(.*?)(?<!\\)\$\$", without_fences, re.DOTALL)
    without_displays = re.sub(
        r"(?<!\\)\$\$.*?(?<!\\)\$\$", "", without_fences, flags=re.DOTALL
    )
    inline = re.findall(
        r"(?<!\\)\$(?!\$)(.*?)(?<!\\)\$(?!\$)", without_displays, re.DOTALL
    )
    return [expression.strip() for expression in (*displays, *inline)]


def test_spec_has_required_knowledge_lag_and_fx_formulas_strict_katex() -> None:
    source = (
        REPO_ROOT / "docs" / "ideas" / "specs" / "s7-track-record-provenance.md"
    ).read_text(encoding="utf-8")
    expressions = _source_math(source)
    assert any("L_{\\mathrm{known}}" in expression for expression in expressions)
    assert any(
        "R^{\\mathrm{base}}_t" in expression
        and "R^{\\mathrm{local}}_t" in expression
        and "R^{\\mathrm{FX}}_t" in expression
        for expression in expressions
    )
    assert "first-known time" in source and "effective time" in source
    assert "local-currency investment return" in source
    assert "currency return into the base currency" in source

    katex = REPO_ROOT / "site" / "assets" / "katex" / "katex.min.js"
    check = r'''
const fs = require("fs");
const katex = require(process.argv[1]);
const rows = JSON.parse(fs.readFileSync(0, "utf8"));
for (const row of rows) {
  katex.renderToString(row, {throwOnError: true, strict: "error"});
}
'''
    result = subprocess.run(
        ["node", "-e", check, str(katex)],
        input=json.dumps(expressions),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
