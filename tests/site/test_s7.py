from __future__ import annotations

import shutil
import json
import re
import subprocess
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
    "minimum_data": (
        "Versioned native-frequency returns or cashflows/NAV, entity and composite lineage, "
        "fee/currency/benchmark basis, X3 membership vintages, dead products, receipt times, "
        "rights, and predecessor/team evidence for portability claims."
    ),
    "decision_readiness": "data-conditional",
    "evidence_roles": ["operational-analysis", "governance-workflow"],
    "validation_status": "live-calibration-required",
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/s7-provenance.html.j2",
    "data": "s7_provenance.json",
    "spec": "s7-track-record-provenance.md",
    "claims": [
        _claim(
            "track_lineage",
            "exact-measurement",
            _ALL_CONTEXTS,
            "B",
            "A selected source version, right, canonical entity grain, X3 membership, "
            "lineage relation, or typed receipt is missing or unresolved.",
        ),
        _claim(
            "point_in_time_vintage_audit",
            "exact-measurement",
            _ALL_CONTEXTS,
            "B",
            "Archived versions, observations, delivery/absence semantics, dead products, or "
            "all-known-versions receipts are incomplete.",
        ),
        _claim(
            "basis_breaks",
            "verdict",
            _ALL_CONTEXTS[1:],
            "B",
            "Fee, currency/FX, benchmark, frequency/calendar, valuation, composite-membership, "
            "or cash-flow basis is missing or incomparable.",
        ),
        _claim(
            "comparable_native_panel",
            "exact-measurement",
            _ALL_CONTEXTS[1:],
            "B",
            "Identity, membership, completeness, basis, native-frequency, inclusion/exclusion "
            "reconciliation, or typed receipt gates do not all pass.",
        ),
        _claim(
            "predecessor_portability_evidence",
            "verdict",
            _PERMISSIONED,
            "C",
            "Predecessor identity, transfer scope, current-team chronology, or source evidence "
            "is missing or contradictory.",
        ),
        _claim(
            "historical_selection_refusal",
            "refusal",
            _ALL_CONTEXTS,
            "B",
            "Historical selection is refused without archived vintages, dead products, "
            "first-known times, and exact denominator scope.",
        ),
        _claim(
            "performance_estimator_refusal",
            "refusal",
            _ALL_CONTEXTS,
            "D",
            "S7 intentionally emits no alpha, Sharpe, IRR, PME, skill, or manager ranking; "
            "use the appropriate downstream method after its own gates.",
            access_semantics="refusal-in-every-context",
        ),
    ],
    "golive": {
        "data_ask": (
            "Archived source vintages and observations; complete full/delta/tombstone contract; "
            "entity/composite/vehicle/share-class lineage; fee/currency/benchmark/valuation "
            "basis; X3 memberships/dead products; predecessor/team evidence; per-dataset "
            "rights and receipts."
        ),
        "sample": (
            "At least one real, permissioned case in each intended source shape, including one "
            "known revision/backfill and one basis break. This is validation coverage, not an "
            "estimator sample-size threshold."
        ),
        "effort": (
            "Reconcile live schemas and licences, obtain manager/data-owner sign-off on lineage, "
            "independently reproduce one panel and one refusal, and calibrate copy without "
            "upgrading attestation beyond the evidence."
        ),
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


def test_complete_server_rendered_default_exists(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    assert "Track-record provenance inspector" in html
    assert "hedge-fund|early|lineage" in html


def test_default_furniture_controls_and_full_method_views(tmp_path: Path) -> None:
    html, out = _build(tmp_path)
    data = json.loads(
        (REPO_ROOT / "site" / "data" / "s7_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    default = data["states"][data["meta"]["default_state"]]

    assert "SYNTHETIC DATA" in html and "fictional demonstration" in html
    assert "availability varies by manager, vehicle, source, right, and decision date" in html
    assert "What this exhibit shows" in html and "golive-box" in html
    assert "Data conditional" in html and "assets/s7-provenance.css" in html
    assert "assets/s7-provenance.js" in html
    assert (out / "assets" / "s7-provenance.css").exists()
    assert (out / "assets" / "s7-provenance.js").exists()
    assert html.count("data-s7-scenario-control=") == 4
    assert html.count("data-s7-cutoff-control=") == 2
    assert html.count("data-s7-view-control=") == 3
    assert html.count("data-s7-claim-id=") == 7
    assert 'aria-live="polite"' in html and "<noscript>" in html
    assert 'data-s7-view-panel="basis" aria-labelledby="s7-basis-title" hidden' in html
    assert 'data-s7-view-panel="audit" aria-labelledby="s7-audit-title" hidden' in html
    assert "Documented lineage is not evidence that historical skill transferred." in html
    assert "source observation" in html and "not an estimate" in html
    assert default["conclusion"] in html
    assert default["limitation"] in html
    assert default["what_changed"] in html
    for tier in ("R", "E", "P"):
        assert f'data-tier="{tier}"' in html
    for label in (
        "Lineage segment table",
        "Portability evidence table",
        "Basis break table",
        "Basis signature table",
        "Native source observation table",
        "Vintage finding table",
        "Typed exclusion table",
        "S7 claim register",
    ):
        assert f'aria-label="{label}"' in html


def test_s7_narrates_one_opening_state_before_advanced_tables(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)

    opening = html.index('class="s7-opening-state"')
    guide = html.index("What this exhibit shows")
    advanced = html.index('<details class="s7-advanced">')
    assert opening < guide < advanced
    opening_html = html[opening:advanced]
    assert "Opening state" in opening_html
    assert "7 source observations" in opening_html
    assert "17 remain excluded" in opening_html
    advanced_html = html[advanced:]
    assert "Explore lineage, basis, and vintage evidence" in advanced_html
    assert 'aria-label="Lineage segment table"' in advanced_html


def test_exact_24_states_claim_receipts_and_plan_copy(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    data = json.loads(
        (REPO_ROOT / "site" / "data" / "s7_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(data["states"]) == 24
    assert set(data["states"]) == {
        f"{scenario}|{cutoff}|{view}"
        for scenario in ("public-equity", "hedge-fund", "credit", "private-market")
        for cutoff in ("early", "latest")
        for view in ("lineage", "basis", "audit")
    }
    default_key = data["meta"]["default_state"]
    for claim_id, claim in data["claims"].items():
        assert f'data-s7-claim-receipts="{claim_id}"' in html
        for receipt_id in claim["receipt_ids_by_state"][default_key]:
            assert receipt_id in html
    assert _CARD["claims"][-1]["refusal"] in html
    assert _CARD["golive"]["data_ask"] in html
    assert _CARD["golive"]["sample"] in html
    assert _CARD["golive"]["effort"] in html


def test_no_javascript_default_is_complete_and_exact(tmp_path: Path) -> None:
    html, _ = _build(tmp_path)
    data = json.loads(
        (REPO_ROOT / "site" / "data" / "s7_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    default = data["states"][data["meta"]["default_state"]]
    assert html.count("data-s7-lineage-row=") == len(default["lineage_segments"])
    assert html.count("data-s7-portability-row=") == len(default["portability_findings"])
    assert html.count("data-s7-break-row=") == len(default["basis_breaks"])
    assert html.count("data-s7-panel-row=") == len(default["panel"].get("rows", []))
    assert html.count("data-s7-vintage-row=") == len(default["vintage_findings"])
    assert html.count("data-s7-exclusion-row=") == len(default["exclusions"])
    assert html.count("data-s7-refusal>") == len(default["refusals"])
    assert ".s7-view[hidden] { display: block !important; }" in html
    assert "All three complete method views above are the" in html
    assert default["analytic_bundle_digest"] in html
    assert default["audit_bundle_digest"] in html
    assert default["join_receipt_ids"]["analytic"] in html
    assert default["join_receipt_ids"]["audit"] in html
    assert ", ".join(default["access_contexts"]) in html


def test_css_responsive_accessible_and_color_independent() -> None:
    source = (REPO_ROOT / "site" / "assets" / "s7-provenance.css").read_text(
        encoding="utf-8"
    )
    assert "min-height: 44px" in source and "min-width: 44px" in source
    assert ":focus-visible" in source
    assert "@media (max-width: 768px)" in source
    assert "@media (max-width: 390px)" in source
    assert "@media (max-width: 320px)" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "overflow-x: auto" in source and "max-width: 100%" in source
    assert 'button[aria-pressed="true"]' in source
    assert "border-left" in source and 'data-state="refused"' in source
    assert ".demo-page .access-semantics-chip" in source
    assert "white-space: normal" in source
    assert ".demo-page .golive-box" in source
    assert "grid-template-columns: minmax(0, 1fr)" in source
    assert ".s7-view > p code" in source
    assert ".demo-page .badge-row .synthetic-badge" in source
    assert "position: static" in source


def test_javascript_state_lookup_history_focus_and_invalid_fallback(tmp_path: Path) -> None:
    _, out = _build(tmp_path)
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
        "unsupported-state-key",
        "textContent",
        "createElement",
    ):
        assert required in source
    for prohibited in (
        "innerHTML",
        ".sort(",
        ".join(",
        ".reduce(",
        "Math.",
        "calculate",
        "estimator(",
        "managerRank",
        "selectRevision",
        "compareBasis",
        "convertFx",
        "createVerdict",
    ):
        assert prohibited not in source
    assert "[data-s7-access-contexts]" in source
    assert "[data-s7-basis-signature-body]" in source
    assert not re.search(
        r"(?:state|item|panel|scenario|claim)\.[A-Za-z_][\w.]*\s*[+\-*/%]",
        source,
    )


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
