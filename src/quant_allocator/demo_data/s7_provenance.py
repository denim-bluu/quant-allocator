"""Deterministic S7 exhibit data built through reviewed evidence and method APIs."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Any, Mapping

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.evidence.fixtures.s7 import (
    S7_CUTOFFS,
    S7_SCENARIOS,
    build_s7_fixture,
    s7_policy_bundle,
    s7_source_requests,
    verify_s7_manifest,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.flagships.track_record_provenance.basis import (
    PanelDecision,
    build_basis_panel_from_s7_fixture,
)
from quant_allocator.flagships.track_record_provenance.inspector import (
    emit_s7_policy_refusal_receipt,
)
from quant_allocator.flagships.track_record_provenance.lineage import (
    build_lineage_from_s7_projections,
)
from quant_allocator.flagships.track_record_provenance.portability import (
    PORTABILITY_CAVEAT,
    assess_s7_portability_evidence,
)
from quant_allocator.flagships.track_record_provenance.vintage import (
    audit_s7_vintages,
)

VIEWS = ("lineage", "basis", "audit")
STATE_KEYS = tuple(
    "|".join(parts) for parts in product(S7_SCENARIOS, S7_CUTOFFS, VIEWS)
)
DEFAULT_STATE = "hedge-fund|early|lineage"

FICTIONAL_DISCLOSURE = (
    "This exhibit uses synthetic source records and fictional entities for demonstration."
)

SCENARIO_CATALOG: dict[str, dict[str, object]] = {
    "public-equity": {
        "label": "Public-equity registered vehicle",
        "source_shape": "Versioned public vehicle returns with benchmark and FX evidence.",
        "minimum_data": ["returns", "entity-lineage", "basis", "archived-vintages"],
        "portability_scope": "not-assessed-no-authenticated-predecessor-bundle",
    },
    "hedge-fund": {
        "label": "Hedge-fund composite",
        "source_shape": "Versioned composite returns, terms, and predecessor evidence.",
        "minimum_data": ["returns", "entity-lineage", "basis", "manager-terms"],
        "portability_scope": "authenticated-terms-evidence-only",
    },
    "credit": {
        "label": "Credit mandate",
        "source_shape": "Versioned liquid and private-credit observations at native frequency.",
        "minimum_data": ["returns", "entity-lineage", "basis", "valuation-policy"],
        "portability_scope": "not-assessed-no-authenticated-predecessor-bundle",
    },
    "private-market": {
        "label": "Private-market drawdown vehicle",
        "source_shape": "Irregular cash flows and versioned quarterly NAV evidence.",
        "minimum_data": ["cashflows-nav", "entity-lineage", "valuation-policy"],
        "portability_scope": "not-assessed-no-authenticated-predecessor-bundle",
    },
}

_CLAIM_SPECS: dict[str, dict[str, object]] = {
    "track_lineage": {
        "output_pointers": ["/states/*/lineage_segments"],
        "output_type": "exact-measurement",
        "access_contexts": [
            "public",
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "B",
    },
    "point_in_time_vintage_audit": {
        "output_pointers": ["/states/*/vintage_findings"],
        "output_type": "exact-measurement",
        "access_contexts": [
            "public",
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "B",
    },
    "basis_breaks": {
        "output_pointers": ["/states/*/basis_breaks"],
        "output_type": "verdict",
        "access_contexts": [
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "B",
    },
    "comparable_native_panel": {
        "output_pointers": ["/states/*/panel"],
        "output_type": "exact-measurement",
        "access_contexts": [
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "B",
    },
    "predecessor_portability_evidence": {
        "output_pointers": ["/states/*/portability_findings"],
        "output_type": "verdict",
        "access_contexts": [
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "C",
    },
    "historical_selection_refusal": {
        "output_pointers": ["/states/*/refusals"],
        "output_type": "refusal",
        "access_contexts": [
            "public",
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "all-required-per-selected-dataset",
        "live_attestation_ceiling": "B",
    },
    "performance_estimator_refusal": {
        "output_pointers": ["/refusals/performance-estimator"],
        "output_type": "refusal",
        "access_contexts": [
            "public",
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ],
        "access_semantics": "refusal-in-every-context",
        "live_attestation_ceiling": "D",
    },
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_safe(getattr(value, field.name)) for field in fields(value)}
    if hasattr(value, "_asdict"):
        return {key: _json_safe(child) for key, child in value._asdict().items()}
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(child) for child in value]
    return value


def _representative_panel(conn: Any, manifest: Any, scenario: str, cutoff: str) -> PanelDecision:
    if scenario == "public-equity":
        return build_basis_panel_from_s7_fixture(
            conn,
            manifest,
            scenario=scenario,
            cutoff_name=cutoff,
            panel_kind="total-return-series",
            source_product_key="s7-public-eur",
            base_currency="USD",
        )
    if scenario == "hedge-fund":
        return build_basis_panel_from_s7_fixture(
            conn,
            manifest,
            scenario=scenario,
            cutoff_name=cutoff,
            panel_kind="total-return-series",
            source_product_key="s7-hf-main",
            source_record_keys=("s7-hf-ambiguous",),
            base_currency="USD",
        )
    if scenario == "credit":
        return build_basis_panel_from_s7_fixture(
            conn,
            manifest,
            scenario=scenario,
            cutoff_name=cutoff,
            panel_kind="total-return-series",
            source_product_key=None,
            source_record_keys=("s7-credit-liquid", "s7-credit-private"),
            base_currency="USD",
        )
    return build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario=scenario,
        cutoff_name=cutoff,
        panel_kind="cashflow-nav-lineage",
        source_product_key="s7-private-main",
        base_currency="USD",
    )


def _basis_diagnostic(
    conn: Any,
    manifest: Any,
    scenario: str,
    cutoff: str,
    representative: PanelDecision,
) -> PanelDecision | None:
    if scenario == "public-equity":
        return build_basis_panel_from_s7_fixture(
            conn,
            manifest,
            scenario=scenario,
            cutoff_name=cutoff,
            panel_kind="excess-return-series",
            source_product_key=None,
            source_record_keys=("s7-public-benchmark-v1", "s7-public-benchmark-v2"),
            base_currency="USD",
        )
    if scenario == "hedge-fund":
        return build_basis_panel_from_s7_fixture(
            conn,
            manifest,
            scenario=scenario,
            cutoff_name=cutoff,
            panel_kind="total-return-series",
            source_product_key=None,
            source_record_keys=("s7-hf-fee-unresolved",),
            base_currency="USD",
        )
    if scenario == "credit":
        return representative
    return None


def _panel_payload(decision: PanelDecision) -> dict[str, object]:
    if decision.panel is not None:
        panel = decision.panel
        return {
            "status": "admitted",
            "panel_kind": panel.panel_kind,
            "entity_grain": panel.entity_grain,
            "canonical_entity_id": panel.canonical_entity_id,
            "native_frequency": panel.native_frequency,
            "basis_signature": _json_safe(panel.basis_signature),
            "rows": _json_safe(panel.rows),
            "row_ids": list(panel.row_ids),
            "excluded_row_ids": list(panel.excluded_row_ids),
            "receipt_id": panel.receipt_id,
        }
    refusal = decision.refusal
    if refusal is None:
        raise RuntimeError("S7 panel decision has neither panel nor refusal")
    return {
        "status": "refused",
        "panel_kind": None,
        "reason_code": refusal.reason_code,
        "reason_codes": list(refusal.reason_codes),
        "row_ids": list(refusal.row_ids),
        "receipt_id": refusal.receipt_id,
    }


def _basis_breaks(decision: PanelDecision) -> list[dict[str, object]]:
    refusal = decision.refusal
    if refusal is None:
        return []
    basis_codes = {
        "fee-basis-missing",
        "fee-basis-incomparable",
        "currency-basis-missing",
        "fx-series-missing",
        "fx-rule-incompatible",
        "benchmark-version-missing",
        "benchmark-basis-incomparable",
        "frequency-calendar-incomparable",
        "valuation-basis-incomparable",
        "cashflow-convention-incomparable",
        "silent-stitch-prohibited",
        "comparison-kind-incompatible",
    }
    if not basis_codes.intersection(refusal.reason_codes):
        return []
    return [
        {
            "disposition": "refused",
            "binding_reason": refusal.reason_code,
            "reason_codes": list(refusal.reason_codes),
            "row_ids": list(refusal.row_ids),
            "receipt_id": refusal.receipt_id,
        }
    ]


def _state_copy(
    *,
    scenario: str,
    cutoff: str,
    view: str,
    admitted_count: int,
    segment_count: int,
    exclusion_count: int,
    panel: dict[str, object],
    finding_count: int,
) -> tuple[str, str, str]:
    if view == "lineage":
        conclusion = (
            f"{admitted_count} source observations are owned by {segment_count} exact "
            f"lineage segments; {exclusion_count} remain excluded."
        )
        changed = "Entity ownership and predecessor evidence are shown at the selected cutoff."
    elif view == "basis":
        conclusion = (
            f"The representative native panel is {panel['status']} after exact basis and "
            "row-reconciliation gates."
        )
        changed = "The basis view shows source values, transforms, breaks, and panel disposition."
    else:
        conclusion = f"The point-in-time audit emits {finding_count} receipted vintage findings."
        changed = "The audit compares latest-known and all-known versions at the same cutoff."
    cutoff_copy = (
        "Only evidence knowable at the early decision cutoff is used."
        if cutoff == "early"
        else "Later-known evidence is shown without rewriting the early decision state."
    )
    limitation = (
        f"{SCENARIO_CATALOG[scenario]['source_shape']} {cutoff_copy} "
        f"{PORTABILITY_CAVEAT}"
    )
    return conclusion, limitation, f"{changed} {cutoff_copy}"


def _analysis_state(
    manifest: Any,
    *,
    scenario: str,
    cutoff: str,
    view: str,
    lineage: Any,
    vintage: Any,
    panel_decision: PanelDecision,
    basis_decision: PanelDecision | None,
    portability: Any | None,
    policy_receipt_id: str,
) -> dict[str, object]:
    panel = _panel_payload(panel_decision)
    exclusion_rows = [
        {
            "source": "lineage",
            "dataset_id": exclusion.dataset_id,
            "observation_id": exclusion.observation_id,
            "reason_code": exclusion.reason_code,
        }
        for exclusion in lineage.unmatched_exclusions
    ]
    if panel_decision.panel is not None:
        exclusion_rows.extend(
            {
                "source": "panel",
                "dataset_id": exclusion.evidence.dataset_id,
                "observation_id": exclusion.observation_id,
                "reason_code": exclusion.reason_code,
            }
            for exclusion in panel_decision.panel.exclusions
        )
    exclusions_by_identity: dict[tuple[str, str, str], dict[str, object]] = {}
    for exclusion in exclusion_rows:
        identity = (
            str(exclusion["dataset_id"]),
            str(exclusion["observation_id"]),
            str(exclusion["reason_code"]),
        )
        prior = exclusions_by_identity.get(identity)
        if prior is None:
            exclusions_by_identity[identity] = exclusion
        elif prior["source"] != exclusion["source"]:
            prior["source"] = "lineage-and-panel"
    exclusions = list(exclusions_by_identity.values())
    refusals: list[dict[str, object]] = [
        {
            "pointer": "/refusals/performance-estimator",
            "reason_code": "performance-estimator-prohibited",
            "detail": (
                "S7 reconstructs lineage and basis-qualified panels; it does not estimate "
                "alpha, Sharpe, IRR, PME, skill, or manager ranking."
            ),
            "current_attestation": "D",
            "live_attestation_ceiling": "D",
            "receipt_id": policy_receipt_id,
        }
    ]
    refusals.extend(
        {
            "pointer": "/lineage_segments",
            "reason_code": refusal.reason_code,
            "canonical_entity_id": refusal.canonical_entity_id,
            "entity_grain": refusal.entity_grain,
            "receipt_id": vintage.analytic_join_receipt_id,
        }
        for refusal in lineage.refusals
    )
    refusals.extend(
        {
            **_json_safe(refusal),
            "source": "historical-selection",
        }
        for refusal in vintage.historical_selection_refusals
    )
    if panel_decision.refusal is not None:
        refusals.append(
            {
                "pointer": panel_decision.refusal.pointer,
                "reason_code": panel_decision.refusal.reason_code,
                "reason_codes": list(panel_decision.refusal.reason_codes),
                "receipt_id": panel_decision.refusal.receipt_id,
            }
        )
    portability_findings: list[dict[str, object]] = []
    if portability is not None:
        portability_findings = [_json_safe(finding) for finding in portability.findings]
        refusals.append({**_json_safe(portability.segment_link_refusal), "source": "portability"})

    receipt_ids = {
        vintage.analytic_join_receipt_id,
        vintage.audit_join_receipt_id,
        *vintage.receipt_ids,
        panel_decision.receipt.receipt_id,
        policy_receipt_id,
    }
    if portability is not None:
        receipt_ids.update(portability.receipt_ids)
    if basis_decision is not None:
        receipt_ids.add(basis_decision.receipt.receipt_id)
    conclusion, limitation, what_changed = _state_copy(
        scenario=scenario,
        cutoff=cutoff,
        view=view,
        admitted_count=len(lineage.admitted_observation_ids),
        segment_count=len(lineage.segments),
        exclusion_count=len(exclusions),
        panel=panel,
        finding_count=len(vintage.findings),
    )
    requests = s7_source_requests(
        manifest,
        scenario=scenario,
        cutoff_name=cutoff,
        revision_mode="latest-known",
    )
    return {
        "scenario": scenario,
        "cutoff": cutoff,
        "view": view,
        "decision_at": S7_CUTOFFS[cutoff].isoformat(),
        "access_contexts": sorted({request.access_context for request in requests}),
        "revision_modes": {
            "analytic": "latest-known",
            "audit": "all-known-versions",
        },
        "analytic_bundle_digest": vintage.analytic_bundle_digest,
        "audit_bundle_digest": vintage.audit_bundle_digest,
        "join_receipt_ids": {
            "analytic": vintage.analytic_join_receipt_id,
            "audit": vintage.audit_join_receipt_id,
        },
        "lineage_segments": _json_safe(lineage.segments),
        "basis_breaks": [] if basis_decision is None else _basis_breaks(basis_decision),
        "vintage_findings": _json_safe(vintage.findings),
        "portability_findings": portability_findings,
        "panel": panel,
        "exclusions": sorted(
            exclusions,
            key=lambda row: (
                str(row["reason_code"]),
                str(row["observation_id"]),
                str(row["source"]),
            ),
        ),
        "refusals": sorted(
            refusals,
            key=lambda row: (
                str(row.get("pointer", "")),
                str(row.get("reason_code", "")),
                str(row.get("receipt_id", "")),
            ),
        ),
        "receipt_ids": sorted(receipt_ids),
        "conclusion": conclusion,
        "limitation": limitation,
        "what_changed": what_changed,
    }


def _claim_receipts(state: Mapping[str, object], claim_id: str) -> list[str]:
    join_ids = state["join_receipt_ids"]
    if not isinstance(join_ids, Mapping):
        raise RuntimeError("S7 state join receipt shape is invalid")
    if claim_id == "track_lineage":
        return [str(join_ids["analytic"])]
    if claim_id == "point_in_time_vintage_audit":
        return sorted(
            {
                str(join_ids["audit"]),
                *(
                    str(row["receipt_id"])
                    for row in state["vintage_findings"]
                    if isinstance(row, Mapping) and row.get("receipt_id")
                ),
            }
        )
    if claim_id == "basis_breaks":
        receipts = [
            str(row["receipt_id"])
            for row in state["basis_breaks"]
            if isinstance(row, Mapping) and row.get("receipt_id")
        ]
        if receipts:
            return sorted(set(receipts))
        panel = state["panel"]
        return [str(panel["receipt_id"])] if isinstance(panel, Mapping) else []
    if claim_id == "comparable_native_panel":
        panel = state["panel"]
        return [str(panel["receipt_id"])] if isinstance(panel, Mapping) else []
    if claim_id == "predecessor_portability_evidence":
        return sorted(
            {
                str(row["receipt_id"])
                for row in (*state["portability_findings"], *state["refusals"])
                if isinstance(row, Mapping)
                and row.get("receipt_id")
                and (
                    row in state["portability_findings"]
                    or row.get("source") == "portability"
                )
            }
        )
    if claim_id == "historical_selection_refusal":
        return sorted(
            {
                str(row["receipt_id"])
                for row in state["refusals"]
                if isinstance(row, Mapping)
                and row.get("source") == "historical-selection"
                and row.get("receipt_id")
            }
        ) or [str(join_ids["audit"])]
    return [
        str(row["receipt_id"])
        for row in state["refusals"]
        if isinstance(row, Mapping)
        and row.get("pointer") == "/refusals/performance-estimator"
    ]


def _claim_is_applicable(
    state: Mapping[str, object],
    claim_id: str,
    spec: Mapping[str, object],
) -> bool:
    state_contexts = set(state["access_contexts"])
    claim_contexts = set(spec["access_contexts"])
    if state_contexts.isdisjoint(claim_contexts):
        return False
    if claim_id == "predecessor_portability_evidence":
        return bool(state["portability_findings"]) or any(
            isinstance(row, Mapping) and row.get("source") == "portability"
            for row in state["refusals"]
        )
    return True


@lru_cache(maxsize=1)
def _build_data() -> dict[str, object]:
    conn = connect()
    initialize(conn)
    try:
        manifest = build_s7_fixture(conn)
        if not verify_s7_manifest(conn, manifest):
            raise RuntimeError("reviewed S7 fixture manifest failed verification")

        pairs = tuple(product(S7_SCENARIOS, S7_CUTOFFS))
        vintages = {
            pair: audit_s7_vintages(
                conn,
                manifest,
                scenario=pair[0],
                cutoff_name=pair[1],
            )
            for pair in pairs
        }
        portability = {
            cutoff: assess_s7_portability_evidence(
                conn, manifest, cutoff_name=cutoff
            )
            for cutoff in S7_CUTOFFS
        }
        lineages = {
            pair: build_lineage_from_s7_projections(
                conn,
                manifest,
                scenario=pair[0],
                cutoff_name=pair[1],
            )
            for pair in pairs
        }
        panels = {
            pair: _representative_panel(conn, manifest, pair[0], pair[1])
            for pair in pairs
        }
        basis_diagnostics = {
            pair: _basis_diagnostic(
                conn,
                manifest,
                pair[0],
                pair[1],
                panels[pair],
            )
            for pair in pairs
        }
        policy_bundle = s7_policy_bundle(conn, manifest)
        policy_receipt = emit_s7_policy_refusal_receipt(
            conn,
            policy_bundle=policy_bundle,
            policy=manifest.policy,
        )

        states = {
            "|".join((scenario, cutoff, view)): _analysis_state(
                manifest,
                scenario=scenario,
                cutoff=cutoff,
                view=view,
                lineage=lineages[(scenario, cutoff)],
                vintage=vintages[(scenario, cutoff)],
                panel_decision=panels[(scenario, cutoff)],
                basis_decision=basis_diagnostics[(scenario, cutoff)],
                portability=portability[cutoff] if scenario == "hedge-fund" else None,
                policy_receipt_id=policy_receipt.receipt_id,
            )
            for scenario, cutoff, view in product(S7_SCENARIOS, S7_CUTOFFS, VIEWS)
        }
        claims = {
            claim_id: {
                **spec,
                "current_attestation": "D",
                "validation_status": "live-calibration-required",
                "receipt_required": True,
                "applicable_by_state": {
                    state_key: _claim_is_applicable(state, claim_id, spec)
                    for state_key, state in states.items()
                },
                "receipt_ids_by_state": {
                    state_key: (
                        _claim_receipts(state, claim_id)
                        if _claim_is_applicable(state, claim_id, spec)
                        else []
                    )
                    for state_key, state in states.items()
                },
            }
            for claim_id, spec in _CLAIM_SPECS.items()
        }
        return {
            "meta": {
                "generator": "s7_provenance",
                "schema_version": "s7-provenance-output/v1",
                "state_axes": {
                    "scenario": list(S7_SCENARIOS),
                    "cutoff": list(S7_CUTOFFS),
                    "view": list(VIEWS),
                },
                "state_count": len(states),
                "default_state": DEFAULT_STATE,
                "fixture_id": manifest.fixture_id,
                "fixture_digest": manifest.fixture_digest,
                "fixture_closure_digest": manifest.closure_digest,
                "evidence_schema_version": manifest.schema_version,
                "evidence_schema_digest": manifest.schema_digest,
                "current_attestation": "D",
                "fictional_disclosure": FICTIONAL_DISCLOSURE,
            },
            "scenarios": SCENARIO_CATALOG,
            "states": states,
            "claims": claims,
        }
    finally:
        conn.close()


def build(*, out_dir: Path = SITE_DATA_DIR) -> Path:
    """Write the held S7 JSON artifact using canonical repository formatting."""
    return write_json(out_dir / "s7_provenance.json", _build_data())
