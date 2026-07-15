"""Exact basis comparison and native-panel admission for S7."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date
from decimal import Decimal
import sqlite3
from collections.abc import Mapping

from quant_allocator.evidence.lineage import make_receipt
from quant_allocator.evidence.model import (
    ReceiptReference,
    ReconstructionReceipt,
    SnapshotBundle,
    canonical_bytes,
    sha256,
)


_RECEIPT_REFERENCE_HEADER_COLUMNS = {
    "receipt_id",
    "ordinal",
    "output_field",
    "reference_type",
    "disposition",
    "reason_code",
    "source_schema_id",
    "source_field",
    "role",
}


@dataclass(frozen=True, slots=True)
class BasisSignature:
    """Controlled economic and observation basis for one lineage segment."""

    entity_grain: str
    frequency: str
    calendar_id: str
    return_kind: str
    gross_net_fee_basis: str
    fee_schedule_version: str | None
    base_currency: str
    fx_treatment: str
    fx_series_id: str | None
    fx_series_version: str | None
    benchmark_id: str | None
    benchmark_version: str | None
    benchmark_return_kind: str | None
    valuation_policy_id: str | None
    cashflow_convention_id: str | None
    composite_definition_id: str | None
    composite_membership_version: str | None
    fx_rule_id: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.entity_grain,
            self.frequency,
            self.calendar_id,
            self.return_kind,
            self.gross_net_fee_basis,
            self.base_currency,
            self.fx_treatment,
        )
        optional = (
            self.fee_schedule_version,
            self.fx_series_id,
            self.fx_series_version,
            self.benchmark_id,
            self.benchmark_version,
            self.benchmark_return_kind,
            self.valuation_policy_id,
            self.cashflow_convention_id,
            self.composite_definition_id,
            self.composite_membership_version,
            self.fx_rule_id,
        )
        if any(not isinstance(value, str) or not value for value in required):
            raise ValueError("s7-basis-signature-required-field-missing")
        if any(value is not None and (not isinstance(value, str) or not value) for value in optional):
            raise ValueError("s7-basis-signature-optional-field-invalid")


@dataclass(frozen=True, slots=True)
class BasisSegment:
    """A Unit-A lineage segment annotated with its exact basis signature."""

    segment_id: str
    observation_ids: tuple[str, ...]
    basis: BasisSignature

    def __post_init__(self) -> None:
        if not self.segment_id or not self.observation_ids:
            raise ValueError("s7-basis-segment-identity-invalid")
        if len(self.observation_ids) != len(set(self.observation_ids)) or any(
            not observation_id for observation_id in self.observation_ids
        ):
            raise ValueError("s7-basis-segment-observations-invalid")


@dataclass(frozen=True, slots=True)
class BasisBreak:
    """An explicit segment boundary that must not be silently stitched."""

    left_segment_id: str
    right_segment_id: str
    changed_fields: tuple[str, ...]
    disposition: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BasisEvidenceBinding:
    """Typed persisted evidence identities supporting one panel observation."""

    dataset_id: str
    source_record_id: str
    evidence_item_id: str
    dataset_observation_id: str
    dataset_version_id: str
    evidence_right_id: str
    snapshot_digest: str
    source_schema_id: str
    source_value_pointer: str
    mapping_ids: tuple[str, ...]
    observation_membership_link_ids: tuple[str, ...]
    membership_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        scalar_ids = (
            self.dataset_id,
            self.source_record_id,
            self.evidence_item_id,
            self.dataset_observation_id,
            self.dataset_version_id,
            self.evidence_right_id,
            self.snapshot_digest,
            self.source_schema_id,
        )
        grouped_ids = (
            self.mapping_ids,
            self.observation_membership_link_ids,
            self.membership_ids,
            self.relationship_ids,
        )
        if any(not value for value in scalar_ids) or any(
            any(not value for value in values) for values in grouped_ids
        ):
            raise ValueError("s7-basis-evidence-binding-incomplete")
        if not self.source_value_pointer.startswith("/"):
            raise ValueError("s7-basis-source-pointer-invalid")


@dataclass(frozen=True, slots=True)
class BasisObservation:
    """One exact source value admitted by Unit-A lineage closure."""

    observation_id: str
    segment_id: str
    canonical_entity_id: str
    observed_at: date
    value: Decimal
    value_kind: str
    basis: BasisSignature
    source_currency: str
    evidence: BasisEvidenceBinding

    def __post_init__(self) -> None:
        if not all(
            (
                self.observation_id,
                self.segment_id,
                self.canonical_entity_id,
                self.value_kind,
                self.source_currency,
            )
        ):
            raise ValueError("s7-basis-observation-identity-invalid")
        if not isinstance(self.value, Decimal):
            raise ValueError("s7-basis-observation-decimal-required")
        if any(
            not identifiers
            for identifiers in (
                self.evidence.mapping_ids,
                self.evidence.observation_membership_link_ids,
                self.evidence.membership_ids,
                self.evidence.relationship_ids,
            )
        ):
            raise ValueError("s7-basis-observation-lineage-binding-incomplete")


@dataclass(frozen=True, slots=True)
class FxObservation:
    """One exact, versioned FX return supporting a deterministic conversion."""

    observation_id: str
    observed_at: date
    value: Decimal
    series_id: str
    version: str
    source_currency: str
    target_currency: str
    quotation_direction: str
    hedge_treatment: str
    rule_id: str
    evidence: BasisEvidenceBinding

    def __post_init__(self) -> None:
        identifiers = (
            self.observation_id,
            self.series_id,
            self.version,
            self.source_currency,
            self.target_currency,
            self.quotation_direction,
            self.hedge_treatment,
            self.rule_id,
        )
        if any(not value for value in identifiers) or not isinstance(self.value, Decimal):
            raise ValueError("s7-fx-observation-invalid")


@dataclass(frozen=True, slots=True)
class PanelRow:
    """An exact admitted value; converted values remain deterministic Decimals."""

    observation_id: str
    observed_at: date
    source_value: Decimal
    admitted_value: Decimal
    fx_observation_id: str | None


@dataclass(frozen=True, slots=True)
class PanelExclusion:
    """One selected source row excluded from the panel with exact evidence."""

    observation_id: str
    reason_code: str
    evidence: BasisEvidenceBinding

    def __post_init__(self) -> None:
        if (
            not self.observation_id
            or not self.reason_code
            or self.observation_id != self.evidence.dataset_observation_id
        ):
            raise ValueError("s7-panel-exclusion-binding-invalid")


@dataclass(frozen=True, slots=True)
class ComparablePanel:
    """A single-grain, single-modality provenance-qualified native panel."""

    panel_kind: str
    entity_grain: str
    canonical_entity_id: str
    native_frequency: str
    basis_signature: BasisSignature
    rows: tuple[PanelRow, ...]
    row_ids: tuple[str, ...]
    excluded_row_ids: tuple[str, ...]
    receipt_id: str
    exclusions: tuple[PanelExclusion, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.canonical_entity_id
            or self.canonical_entity_id.split(":", 1)[0] != self.entity_grain
        ):
            raise ValueError("s7-panel-canonical-entity-invalid")


@dataclass(frozen=True, slots=True)
class ProvenanceRefusal:
    """A binding panel refusal plus every applicable controlled reason."""

    pointer: str
    reason_code: str
    reason_codes: tuple[str, ...]
    row_ids: tuple[str, ...]
    receipt_id: str


@dataclass(frozen=True, slots=True)
class PanelDecision:
    """Exactly one admitted panel or controlled refusal with a shared receipt."""

    panel: ComparablePanel | None
    refusal: ProvenanceRefusal | None
    receipt: ReconstructionReceipt

    def __post_init__(self) -> None:
        if (self.panel is None) == (self.refusal is None):
            raise ValueError("s7-panel-decision-shape-invalid")


_REASON_BY_FIELD = {
    "entity_grain": "entity-grain-mismatch",
    "frequency": "frequency-calendar-incomparable",
    "calendar_id": "frequency-calendar-incomparable",
    "return_kind": "comparison-kind-incompatible",
    "gross_net_fee_basis": "fee-basis-incomparable",
    "fee_schedule_version": "fee-basis-incomparable",
    "base_currency": "currency-basis-missing",
    "fx_treatment": "fx-rule-incompatible",
    "fx_series_id": "fx-series-missing",
    "fx_series_version": "fx-rule-incompatible",
    "benchmark_id": "benchmark-basis-incomparable",
    "benchmark_version": "benchmark-basis-incomparable",
    "benchmark_return_kind": "benchmark-basis-incomparable",
    "valuation_policy_id": "valuation-basis-incomparable",
    "cashflow_convention_id": "cashflow-convention-incomparable",
    "composite_definition_id": "silent-stitch-prohibited",
    "composite_membership_version": "silent-stitch-prohibited",
    "fx_rule_id": "fx-rule-incompatible",
}


def compare_basis(left: BasisSegment, right: BasisSegment) -> BasisBreak | None:
    """Return the exact changed fields and controlled refusal reasons, if any."""
    changed = tuple(
        field.name
        for field in fields(BasisSignature)
        if getattr(left.basis, field.name) != getattr(right.basis, field.name)
    )
    if not changed:
        return None
    reasons = tuple(
        dict.fromkeys(
            (*(_REASON_BY_FIELD[field_name] for field_name in changed), "silent-stitch-prohibited")
        )
    )
    return BasisBreak(
        left.segment_id,
        right.segment_id,
        changed,
        "refused",
        reasons,
    )


def _basis_payload(basis: BasisSignature) -> dict[str, str | None]:
    return {field.name: getattr(basis, field.name) for field in fields(BasisSignature)}


def _panel_value(panel: ComparablePanel) -> dict[str, object]:
    return {
        "panel_kind": panel.panel_kind,
        "entity_grain": panel.entity_grain,
        "canonical_entity_id": panel.canonical_entity_id,
        "native_frequency": panel.native_frequency,
        "basis_signature": _basis_payload(panel.basis_signature),
        "rows": tuple(
            {
                "observation_id": row.observation_id,
                "observed_at": row.observed_at.isoformat(),
                "source_value": format(row.source_value, "f"),
                "admitted_value": format(row.admitted_value, "f"),
                "fx_observation_id": row.fx_observation_id,
            }
            for row in panel.rows
        ),
        "row_ids": panel.row_ids,
        "excluded_row_ids": panel.excluded_row_ids,
        "exclusions": tuple(
            {
                "observation_id": exclusion.observation_id,
                "reason_code": exclusion.reason_code,
            }
            for exclusion in panel.exclusions
        ),
    }


def _binding_references(
    evidence: BasisEvidenceBinding,
    *,
    output_field: str,
    disposition: str,
    reason_code: str,
) -> tuple[ReceiptReference, ...]:
    common = {
        "output_field": output_field,
        "disposition": disposition,
        "reason_code": reason_code,
        "source_schema_id": evidence.source_schema_id,
    }
    references = [
        ReceiptReference(
            reference_type=reference_type,
            reference_id=reference_id,
            source_field=source_field,
            role=role,
            **common,
        )
        for reference_type, reference_id, source_field, role in (
            ("source-record", evidence.source_record_id, "/", "input"),
            ("evidence-item", evidence.evidence_item_id, evidence.source_value_pointer, "input"),
            ("dataset-observation", evidence.dataset_observation_id, "/", "input"),
            ("dataset-version", evidence.dataset_version_id, "/", "input"),
            ("evidence-right", evidence.evidence_right_id, "/", "filter"),
            ("snapshot", evidence.snapshot_digest, "/", "input"),
        )
    ]
    references.extend(
        ReceiptReference(
            reference_type=reference_type,
            reference_id=reference_id,
            source_field="/",
            role="input",
            **common,
        )
        for reference_type, identifiers in (
            ("entity-mapping", evidence.mapping_ids),
            (
                "observation-membership-link",
                evidence.observation_membership_link_ids,
            ),
            ("universe-membership", evidence.membership_ids),
            ("entity-relationship", evidence.relationship_ids),
        )
        for reference_id in identifiers
    )
    return tuple(references)


def _observation_references(
    observation: BasisObservation,
    *,
    output_field: str,
    disposition: str,
    reason_code: str,
) -> tuple[ReceiptReference, ...]:
    return _binding_references(
        observation.evidence,
        output_field=output_field,
        disposition=disposition,
        reason_code=reason_code,
    )


_REFUSAL_PRECEDENCE = (
    "entity-grain-mismatch",
    "fee-basis-missing",
    "fee-basis-incomparable",
    "currency-basis-missing",
    "fx-series-missing",
    "fx-rule-incompatible",
    "benchmark-version-missing",
    "benchmark-basis-incomparable",
    "frequency-calendar-incomparable",
    "valuation-basis-incomparable",
    "comparison-kind-incompatible",
    "cashflow-convention-incomparable",
    "silent-stitch-prohibited",
)


def _panel_refusal_reasons(
    observations: tuple[BasisObservation, ...],
    *,
    panel_kind: str,
    entity_grain: str,
    fx_observations: tuple[FxObservation, ...],
) -> tuple[str, ...]:
    bases = tuple(row.basis for row in observations)
    reasons: set[str] = set()
    if any(
        basis.entity_grain != entity_grain
        or row.canonical_entity_id.split(":", 1)[0] != entity_grain
        for row, basis in zip(observations, bases, strict=True)
    ) or len({row.canonical_entity_id for row in observations}) != 1:
        reasons.add("entity-grain-mismatch")
    is_cashflow_nav = panel_kind == "cashflow-nav-lineage"
    if not is_cashflow_nav:
        fee_bases = {
            (basis.gross_net_fee_basis, basis.fee_schedule_version) for basis in bases
        }
        if any(basis.fee_schedule_version is None for basis in bases) or len(fee_bases) > 1:
            reasons.add("fee-basis-incomparable")
    if len({basis.base_currency for basis in bases}) > 1:
        reasons.add("fx-series-missing")
    for observation in observations:
        _, fx_reason = _matching_fx_observation(observation, fx_observations)
        if fx_reason is not None:
            reasons.add(fx_reason)
    benchmark_bases = {
        (basis.benchmark_id, basis.benchmark_version, basis.benchmark_return_kind)
        for basis in bases
    }
    if panel_kind == "excess-return-series" and any(
        basis.benchmark_id is None
        or basis.benchmark_version is None
        or basis.benchmark_return_kind is None
        for basis in bases
    ):
        reasons.add("benchmark-version-missing")
    elif not is_cashflow_nav and len(benchmark_bases) > 1:
        reasons.add("benchmark-basis-incomparable")
    if len({(basis.frequency, basis.calendar_id) for basis in bases}) > 1:
        reasons.add("frequency-calendar-incomparable")
    if len({basis.valuation_policy_id for basis in bases}) > 1:
        reasons.add("valuation-basis-incomparable")
    if is_cashflow_nav:
        value_kinds = {row.value_kind for row in observations}
        if (
            not value_kinds <= {"cashflow", "nav"}
            or not {"cashflow", "nav"} <= value_kinds
            or any(basis.return_kind != "cashflow-nav-lineage" for basis in bases)
        ):
            reasons.add("comparison-kind-incompatible")
        if any(basis.valuation_policy_id is None for basis in bases):
            reasons.add("valuation-basis-incomparable")
        if any(basis.cashflow_convention_id is None for basis in bases):
            reasons.add("cashflow-convention-incomparable")
    elif (
        any(row.value_kind != "periodic-return" for row in observations)
        or len({basis.return_kind for basis in bases}) > 1
        or any(basis.return_kind != "total-return" for basis in bases)
    ):
        reasons.add("comparison-kind-incompatible")
    if len({basis.cashflow_convention_id for basis in bases}) > 1:
        reasons.add("cashflow-convention-incomparable")
    changed_fields = {
        field.name
        for field in fields(BasisSignature)
        if len({getattr(basis, field.name) for basis in bases}) > 1
    }
    if changed_fields:
        reasons.add("silent-stitch-prohibited")
    return tuple(code for code in _REFUSAL_PRECEDENCE if code in reasons)


def _receipt_references(
    observations: tuple[BasisObservation, ...],
    *,
    exclusions: tuple[PanelExclusion, ...] = (),
    fx_observations: tuple[FxObservation, ...] = (),
    output_field: str,
    disposition: str,
    reason_code: str,
) -> tuple[ReceiptReference, ...]:
    observation_references = tuple(
        reference
        for observation in observations
        for reference in _observation_references(
            observation,
            output_field=output_field,
            disposition=disposition,
            reason_code=reason_code,
        )
    )
    fx_references = tuple(
        reference
        for observation in fx_observations
        for reference in _binding_references(
            observation.evidence,
            output_field=output_field,
            disposition=disposition,
            reason_code=reason_code,
        )
    )
    exclusion_references = tuple(
        reference
        for exclusion in exclusions
        for reference in _binding_references(
            exclusion.evidence,
            output_field="/panel/exclusions",
            disposition="excluded",
            reason_code=exclusion.reason_code,
        )
    )
    return (*observation_references, *exclusion_references, *fx_references)


def _refusal_value(
    refusal: ProvenanceRefusal,
    exclusions: tuple[PanelExclusion, ...],
) -> dict[str, object]:
    return {
        "pointer": refusal.pointer,
        "reason_code": refusal.reason_code,
        "reason_codes": refusal.reason_codes,
        "row_ids": refusal.row_ids,
        "exclusions": tuple(
            {
                "observation_id": exclusion.observation_id,
                "reason_code": exclusion.reason_code,
            }
            for exclusion in exclusions
        ),
    }


def _matching_fx_observation(
    observation: BasisObservation,
    fx_observations: tuple[FxObservation, ...],
) -> tuple[FxObservation | None, str | None]:
    basis = observation.basis
    if observation.source_currency == basis.base_currency:
        if (
            basis.fx_treatment != "native-base"
            or basis.fx_series_id is not None
            or basis.fx_series_version is not None
            or basis.fx_rule_id is not None
        ):
            return None, "fx-rule-incompatible"
        return None, None
    if (
        basis.fx_treatment != "unhedged-converted"
        or basis.fx_series_id is None
        or basis.fx_series_version is None
        or basis.fx_rule_id is None
    ):
        return None, "fx-series-missing"
    version_candidates = tuple(
        fx
        for fx in fx_observations
        if fx.observed_at == observation.observed_at
        and fx.series_id == basis.fx_series_id
        and fx.version == basis.fx_series_version
    )
    if not version_candidates:
        return None, "fx-series-missing"
    exact = tuple(
        fx
        for fx in version_candidates
        if fx.source_currency == observation.source_currency
        and fx.target_currency == basis.base_currency
        and fx.quotation_direction == "base-per-quote"
        and fx.hedge_treatment == "unhedged"
        and fx.rule_id == basis.fx_rule_id
    )
    if len(exact) != 1:
        return None, "fx-rule-incompatible"
    return exact[0], None


def emit_comparable_panel(
    observations: tuple[BasisObservation, ...],
    *,
    panel_kind: str,
    entity_grain: str,
    bundle_digest: str,
    join_receipt_id: str,
    fx_observations: tuple[FxObservation, ...] = (),
    exclusions: tuple[PanelExclusion, ...] = (),
) -> PanelDecision:
    """Admit an exact native panel and bind every included row to a shared receipt."""
    if panel_kind not in {
        "total-return-series",
        "excess-return-series",
        "cashflow-nav-lineage",
    }:
        raise ValueError("s7-panel-kind-invalid")
    if not observations:
        raise ValueError("s7-panel-observations-required")
    ordered = tuple(sorted(observations, key=lambda row: (row.observed_at, row.observation_id)))
    if len({row.observation_id for row in ordered}) != len(ordered):
        raise ValueError("s7-panel-observation-reconciliation-invalid")
    ordered_exclusions = tuple(
        sorted(exclusions, key=lambda exclusion: exclusion.observation_id)
    )
    excluded_ids = tuple(
        exclusion.observation_id for exclusion in ordered_exclusions
    )
    row_ids = tuple(row.observation_id for row in ordered)
    canonical_entity_ids = tuple(
        sorted({row.canonical_entity_id for row in ordered})
    )
    if (
        len(set(excluded_ids)) != len(excluded_ids)
        or set(row_ids) & set(excluded_ids)
    ):
        raise ValueError("s7-panel-observation-reconciliation-invalid")
    basis = ordered[0].basis
    relevant_fx_observations = tuple(
        fx
        for fx in fx_observations
        if any(
            observation.source_currency != observation.basis.base_currency
            and fx.observed_at == observation.observed_at
            and (
                observation.basis.fx_series_id is None
                or fx.series_id == observation.basis.fx_series_id
            )
            for observation in ordered
        )
    )
    reasons = _panel_refusal_reasons(
        ordered,
        panel_kind=panel_kind,
        entity_grain=entity_grain,
        fx_observations=relevant_fx_observations,
    )
    base_parameters = {
        "panel_kind": panel_kind,
        "entity_grain": entity_grain,
        "canonical_entity_ids": canonical_entity_ids,
        "bundle_digest": bundle_digest,
        "join_receipt_id": join_receipt_id,
        "row_ids": row_ids,
        "excluded_row_ids": excluded_ids,
        "exclusions": tuple(
            {
                "observation_id": exclusion.observation_id,
                "reason_code": exclusion.reason_code,
            }
            for exclusion in ordered_exclusions
        ),
    }
    if reasons:
        draft_refusal = ProvenanceRefusal(
            "/panel",
            reasons[0],
            reasons,
            tuple(row.observation_id for row in ordered),
            "pending",
        )
        parameters = {
            **base_parameters,
            "reason_codes": reasons,
            "fx_observation_ids": tuple(
                observation.observation_id for observation in relevant_fx_observations
            ),
        }
        receipt = make_receipt(
            claim_id="s7_comparable_panel_refusal",
            output_locator="/panel/refusal",
            input_digest=sha256(canonical_bytes(parameters)),
            output_schema_id="s7-provenance-output/v1",
            current_attestation="D",
            live_attestation_ceiling="B",
            algorithm_id="s7-basis-panel/v1",
            algorithm_version="1",
            parameters=parameters,
            value=_refusal_value(draft_refusal, ordered_exclusions),
            references=_receipt_references(
                ordered,
                exclusions=ordered_exclusions,
                fx_observations=relevant_fx_observations,
                output_field="/panel/refusal",
                disposition="refused",
                reason_code=reasons[0],
            ),
        )
        refusal = replace(draft_refusal, receipt_id=receipt.receipt_id)
        return PanelDecision(None, refusal, receipt)
    matched_fx = tuple(
        _matching_fx_observation(observation, relevant_fx_observations)[0]
        for observation in ordered
    )
    rows = tuple(
        PanelRow(
            observation.observation_id,
            observation.observed_at,
            observation.value,
            (
                observation.value
                if fx is None
                else (Decimal(1) + observation.value) * (Decimal(1) + fx.value)
                - Decimal(1)
            ),
            None if fx is None else fx.observation_id,
        )
        for observation, fx in zip(ordered, matched_fx, strict=True)
    )
    used_fx = tuple(fx for fx in matched_fx if fx is not None)
    canonical_entity_id = canonical_entity_ids[0]
    draft = ComparablePanel(
        panel_kind,
        entity_grain,
        canonical_entity_id,
        basis.frequency,
        basis,
        rows,
        row_ids,
        excluded_ids,
        "pending",
        ordered_exclusions,
    )
    parameters = {
        **base_parameters,
        "canonical_entity_id": canonical_entity_id,
        "basis_signature": _basis_payload(basis),
        "fx_observation_ids": tuple(observation.observation_id for observation in used_fx),
    }
    receipt = make_receipt(
        claim_id="s7_comparable_panel",
        output_locator="/panel",
        input_digest=sha256(canonical_bytes(parameters)),
        output_schema_id="s7-provenance-output/v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="s7-basis-panel/v1",
        algorithm_version="1",
        parameters=parameters,
        value=_panel_value(draft),
        references=_receipt_references(
            ordered,
            exclusions=ordered_exclusions,
            fx_observations=used_fx,
            output_field="/panel/rows",
            disposition="included",
            reason_code="",
        ),
    )
    panel = replace(draft, receipt_id=receipt.receipt_id)
    return PanelDecision(panel, None, receipt)


def verify_s7_panel_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    bundle: SnapshotBundle,
    observations: tuple[BasisObservation, ...],
    exclusions: tuple[PanelExclusion, ...],
    panel_kind: str,
    entity_grain: str,
    fx_observations: tuple[FxObservation, ...] = (),
) -> None:
    """Re-derive exact admitted/excluded closure before shared receipt checks."""
    from quant_allocator.evidence.lineage import verify_receipt

    expected = emit_comparable_panel(
        observations,
        panel_kind=panel_kind,
        entity_grain=entity_grain,
        bundle_digest=bundle.bundle_digest,
        join_receipt_id=bundle.join_receipt_id,
        fx_observations=fx_observations,
        exclusions=exclusions,
    ).receipt
    persisted = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
        (receipt_id,),
    ).fetchone()
    expected_header = (
        expected.receipt_id,
        expected.claim_id,
        expected.output_locator,
        expected.input_digest,
        expected.output_schema_id,
        expected.current_attestation,
        expected.live_attestation_ceiling,
        expected.algorithm_id,
        expected.algorithm_version,
        expected.parameters_sha256,
        expected.value_sha256,
    )
    if persisted is None or tuple(persisted) != expected_header:
        raise ValueError("s7-panel-receipt-closure-mismatch")

    persisted_references = []
    for row in conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
        (receipt_id,),
    ):
        identifiers = [
            row[column]
            for column in row.keys()
            if column not in _RECEIPT_REFERENCE_HEADER_COLUMNS
            and row[column] is not None
        ]
        if len(identifiers) != 1:
            raise ValueError("s7-panel-receipt-closure-mismatch")
        persisted_references.append(
            ReceiptReference(
                row["output_field"],
                row["reference_type"],
                str(identifiers[0]),
                row["disposition"],
                row["reason_code"],
                row["source_schema_id"],
                row["source_field"],
                row["role"],
            )
        )
    if tuple(persisted_references) != expected.references:
        raise ValueError("s7-panel-receipt-closure-mismatch")
    verify_receipt(conn, receipt_id, bundle)


def _basis_evidence_binding(
    conn: sqlite3.Connection,
    *,
    row: Mapping[str, object],
    snapshot_digest: str,
    evidence_right_id: str,
    source_value_pointer: str,
    segment: object | None,
) -> BasisEvidenceBinding:
    observation_id = str(row["dataset_observation_id"])
    persisted = conn.execute(
        """SELECT observation.dataset_version_id AS observation_dataset_version_id,
                  observation.evidence_item_id,
                  item.source_record_id,
                  item.payload_schema_id,
                  source.dataset_id AS source_dataset_id,
                  version.dataset_id AS version_dataset_id
           FROM dataset_observation observation
           JOIN evidence_item item USING(evidence_item_id)
           JOIN source_record source USING(source_record_id)
           JOIN dataset_version version USING(dataset_version_id)
           WHERE observation.dataset_observation_id=?""",
        (observation_id,),
    ).fetchone()
    if persisted is None:
        raise ValueError("s7-basis-observation-missing")
    selected_version = conn.execute(
        "SELECT dataset_id FROM dataset_version WHERE dataset_version_id=?",
        (row["dataset_version_id"],),
    ).fetchone()
    dataset_id = str(persisted["source_dataset_id"])
    if (
        str(row["dataset_id"]) != dataset_id
        or str(row["evidence_item_id"]) != str(persisted["evidence_item_id"])
        or str(row["source_record_id"]) != str(persisted["source_record_id"])
        or str(persisted["version_dataset_id"]) != dataset_id
        or selected_version is None
        or str(selected_version["dataset_id"]) != dataset_id
    ):
        raise ValueError("s7-basis-evidence-binding-mismatch")
    if segment is None:
        mapping_ids: tuple[str, ...] = ()
        link_ids: tuple[str, ...] = ()
        membership_ids: tuple[str, ...] = ()
        relationship_ids: tuple[str, ...] = ()
    else:
        direct_mapping_ids = {
            str(record[0])
            for record in conn.execute(
                "SELECT entity_mapping_id FROM entity_mapping "
                "WHERE dataset_observation_id=? AND mapping_status='resolved'",
                (observation_id,),
            )
        }
        link_rows = tuple(
            conn.execute(
                "SELECT link.observation_membership_link_id,"
                "link.universe_membership_id,membership.entity_mapping_id "
                "FROM observation_membership_link link "
                "JOIN universe_membership membership USING(universe_membership_id) "
                "WHERE link.dataset_observation_id=? "
                "ORDER BY link.observation_membership_link_id",
                (observation_id,),
            )
        )
        common_mapping_ids = {
            str(mapping_id)
            for mapping_id in segment.mapping_ids
            if not str(
                conn.execute(
                    "SELECT source_key FROM entity_mapping WHERE entity_mapping_id=?",
                    (mapping_id,),
                ).fetchone()[0]
            ).startswith("s7-")
        }
        mapping_ids = tuple(
            sorted(
                {
                    *direct_mapping_ids,
                    *common_mapping_ids,
                    *(str(record[2]) for record in link_rows),
                }
            )
        )
        link_ids = tuple(str(record[0]) for record in link_rows)
        membership_ids = tuple(
            sorted({*(str(record[1]) for record in link_rows), *segment.membership_ids})
        )
        relationship_ids = tuple(segment.relationship_ids)
    return BasisEvidenceBinding(
        dataset_id=dataset_id,
        source_record_id=str(persisted["source_record_id"]),
        evidence_item_id=str(persisted["evidence_item_id"]),
        dataset_observation_id=observation_id,
        dataset_version_id=str(persisted["observation_dataset_version_id"]),
        evidence_right_id=evidence_right_id,
        snapshot_digest=snapshot_digest,
        source_schema_id=str(persisted["payload_schema_id"]),
        source_value_pointer=source_value_pointer,
        mapping_ids=mapping_ids,
        observation_membership_link_ids=link_ids,
        membership_ids=membership_ids,
        relationship_ids=relationship_ids,
    )


def _fx_observations_from_bundle(
    conn: sqlite3.Connection, bundle: object
) -> tuple[FxObservation, ...]:
    observations = []
    for snapshot_slice in bundle.slices:
        for row in snapshot_slice.rows:
            payload = row.get("payload")
            if not isinstance(payload, Mapping) or "fx_return" not in payload:
                continue
            observations.append(
                FxObservation(
                    observation_id=str(row["dataset_observation_id"]),
                    observed_at=date.fromisoformat(str(payload["period_end"])[:10]),
                    value=Decimal(str(payload["fx_return"])),
                    series_id=str(payload["series_id"]),
                    version=str(row["version"]),
                    source_currency=str(payload["base_currency"]),
                    target_currency=str(payload["quote_currency"]),
                    quotation_direction=str(payload["quotation_direction"]),
                    hedge_treatment=str(payload["hedge_treatment"]),
                    rule_id=str(payload["rule_id"]),
                    evidence=_basis_evidence_binding(
                        conn,
                        row=row,
                        snapshot_digest=snapshot_slice.digest,
                        evidence_right_id=snapshot_slice.request.evidence_right_id,
                        source_value_pointer="/fx_return",
                        segment=None,
                    ),
                )
            )
    return tuple(sorted(observations, key=lambda row: row.observation_id))


def _periodic_basis_signature(
    *,
    payload: Mapping[str, object],
    segment: object,
    base_currency: str,
    fx_observations: tuple[FxObservation, ...],
) -> BasisSignature:
    source_currency = str(payload["currency"])
    fx = next(
        (
            observation
            for observation in fx_observations
            if observation.source_currency == source_currency
            and observation.target_currency == base_currency
        ),
        None,
    )
    management_fee = str(payload.get("management_fee_basis") or "")
    incentive_fee = str(payload.get("incentive_fee_basis") or "")
    fee_schedule = (
        f"management={management_fee};incentive={incentive_fee}"
        if management_fee and incentive_fee
        else None
    )
    is_composite = str(segment.entity_grain) == "composite"
    return BasisSignature(
        entity_grain=str(segment.entity_grain),
        frequency=str(payload["frequency"]),
        calendar_id=str(payload["calendar"]),
        return_kind=str(payload["return_kind"]),
        gross_net_fee_basis=str(payload["gross_net"]),
        fee_schedule_version=fee_schedule,
        base_currency=base_currency,
        fx_treatment=("native-base" if source_currency == base_currency else "unhedged-converted"),
        fx_series_id=None if source_currency == base_currency or fx is None else fx.series_id,
        fx_series_version=None if source_currency == base_currency or fx is None else fx.version,
        benchmark_id=str(payload["benchmark_id"]) if payload.get("benchmark_id") else None,
        benchmark_version=(
            str(payload["benchmark_version"]) if payload.get("benchmark_version") else None
        ),
        benchmark_return_kind=(
            str(payload["benchmark_convention"])
            if payload.get("benchmark_convention")
            else None
        ),
        valuation_policy_id=(
            str(payload["valuation_policy_id"])
            if payload.get("valuation_policy_id")
            else None
        ),
        cashflow_convention_id=(
            str(payload["cashflow_convention"])
            if payload.get("cashflow_convention")
            else None
        ),
        composite_definition_id=(
            str(payload["source_product_key"]) if is_composite else None
        ),
        composite_membership_version=(
            sha256(canonical_bytes(segment.membership_ids)) if is_composite else None
        ),
        fx_rule_id=None if source_currency == base_currency or fx is None else fx.rule_id,
    )


def _cashflow_nav_basis_signature(
    *,
    payloads: tuple[Mapping[str, object], ...],
    segment: object,
    base_currency: str,
) -> BasisSignature:
    nav_payloads = tuple(payload for payload in payloads if "nav" in payload)
    cashflow_payloads = tuple(payload for payload in payloads if "amount" in payload)
    if not nav_payloads or not cashflow_payloads:
        raise ValueError("s7-cashflow-nav-source-shape-incomplete")
    currencies = {str(payload["currency"]) for payload in payloads}
    valuation_policies = {
        str(payload["valuation_policy_id"]) for payload in nav_payloads
    }
    cashflow_conventions = {
        str(payload["cashflow_convention"]) for payload in cashflow_payloads
    }
    if (
        currencies != {base_currency}
        or len(valuation_policies) != 1
        or len(cashflow_conventions) != 1
    ):
        raise ValueError("s7-cashflow-nav-source-basis-incomplete")
    return BasisSignature(
        entity_grain=str(segment.entity_grain),
        frequency="irregular-cashflow-plus-quarterly-nav",
        calendar_id="native-dated",
        return_kind="cashflow-nav-lineage",
        gross_net_fee_basis="not-applicable",
        fee_schedule_version=None,
        base_currency=base_currency,
        fx_treatment="native-base",
        fx_series_id=None,
        fx_series_version=None,
        benchmark_id=None,
        benchmark_version=None,
        benchmark_return_kind=None,
        valuation_policy_id=next(iter(valuation_policies)),
        cashflow_convention_id=next(iter(cashflow_conventions)),
        composite_definition_id=None,
        composite_membership_version=None,
    )


def build_basis_panel_from_s7_fixture(
    conn: sqlite3.Connection,
    manifest: object,
    *,
    scenario: str,
    cutoff_name: str,
    panel_kind: str,
    source_product_key: str | None,
    base_currency: str,
    source_record_keys: tuple[str, ...] = (),
) -> PanelDecision:
    """Build and verify one fixture-backed panel through Unit-A lineage closure."""
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        s7_source_requests,
    )
    from quant_allocator.evidence.lineage import store_receipt, verify_receipt
    from quant_allocator.evidence.model import SnapshotBundleRequest
    from quant_allocator.evidence.projections import project_entity_mappings
    from quant_allocator.evidence.snapshot import as_known_bundle

    from .lineage import build_lineage_from_s7_projections

    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS[cutoff_name],
            s7_source_requests(
                manifest,
                scenario=scenario,
                cutoff_name=cutoff_name,
                revision_mode="latest-known",
            ),
            ("field_dictionary_version",),
            "s7-track-lineage-v1",
        ),
    )
    contract = next(
        (
            candidate
            for candidate in manifest.bundle_contracts
            if candidate.scenario == scenario and candidate.cutoff_name == cutoff_name
        ),
        None,
    )
    if (
        contract is None
        or bundle.bundle_digest != contract.analytic_bundle_digest
        or bundle.join_receipt_id != contract.analytic_join_receipt_id
    ):
        raise ValueError("s7-basis-bundle-contract-mismatch")
    verify_receipt(conn, bundle.join_receipt_id, bundle)
    for snapshot_slice in bundle.slices:
        if snapshot_slice.receipt_id is None:
            raise ValueError("s7-basis-slice-receipt-missing")
        verify_receipt(conn, snapshot_slice.receipt_id, bundle)

    lineage = build_lineage_from_s7_projections(
        conn, manifest, scenario=scenario, cutoff_name=cutoff_name
    )
    segment_by_observation = {
        observation_id: segment
        for segment in lineage.segments
        for observation_id in segment.observation_ids
    }
    exclusion_by_observation: dict[str, object] = {}
    for exclusion in lineage.unmatched_exclusions:
        if exclusion.observation_id in exclusion_by_observation:
            raise ValueError("s7-basis-selection-reconciliation-invalid")
        exclusion_by_observation[exclusion.observation_id] = exclusion
    if set(segment_by_observation) & set(exclusion_by_observation):
        raise ValueError("s7-basis-selection-reconciliation-invalid")
    if source_product_key is None and not source_record_keys:
        raise ValueError("s7-basis-selection-required")
    selected_record_keys = set(source_record_keys)
    source_keys = {
        str(row[0]): str(row[1])
        for row in conn.execute(
            "SELECT source_record_id,source_record_key FROM source_record"
        )
    }
    selected: list[tuple[Mapping[str, object], object, object]] = []
    selected_exclusions: list[PanelExclusion] = []
    for snapshot_slice in bundle.slices:
        mapping_ids_by_observation: dict[str, list[str]] = {}
        for projected_mapping in project_entity_mappings(conn, snapshot_slice):
            projected_observation_id = projected_mapping.get("dataset_observation_id")
            mapping_id = projected_mapping.get("entity_mapping_id")
            if isinstance(projected_observation_id, str) and isinstance(mapping_id, str):
                mapping_ids_by_observation.setdefault(
                    projected_observation_id, []
                ).append(mapping_id)
        for row in snapshot_slice.rows:
            payload = row.get("payload")
            observation_id = str(row.get("dataset_observation_id") or "")
            source_record_key = source_keys.get(str(row.get("source_record_id") or ""))
            selected_by_key = bool(selected_record_keys) and source_record_key in selected_record_keys
            selected_by_product = (
                source_product_key is not None
                and isinstance(payload, Mapping)
                and payload.get("source_product_key") == source_product_key
            )
            if (
                not isinstance(payload, Mapping)
                or not (selected_by_key or selected_by_product)
                or not ({"return_value", "amount", "nav"} & set(payload))
            ):
                continue
            segment = segment_by_observation.get(observation_id)
            exclusion = exclusion_by_observation.get(observation_id)
            if (segment is None) == (exclusion is None):
                raise ValueError("s7-basis-selection-reconciliation-invalid")
            if segment is not None:
                selected.append((row, snapshot_slice, segment))
                continue
            source_value_pointer = (
                "/return_value"
                if "return_value" in payload
                else "/amount"
                if "amount" in payload
                else "/nav"
            )
            mapping_ids = tuple(
                sorted(set(mapping_ids_by_observation.get(observation_id, ())))
            )
            if (
                exclusion.reason_code == "entity-mapping-ambiguous"
                and not mapping_ids
            ):
                raise ValueError("s7-basis-exclusion-mapping-missing")
            selected_exclusions.append(
                PanelExclusion(
                    observation_id,
                    str(exclusion.reason_code),
                    replace(
                        _basis_evidence_binding(
                            conn,
                            row=row,
                            snapshot_digest=snapshot_slice.digest,
                            evidence_right_id=snapshot_slice.request.evidence_right_id,
                            source_value_pointer=source_value_pointer,
                            segment=None,
                        ),
                        mapping_ids=mapping_ids,
                    ),
                )
            )
    if not selected:
        raise ValueError("s7-basis-selected-observation-missing")

    fx_observations = _fx_observations_from_bundle(conn, bundle)
    if panel_kind == "cashflow-nav-lineage":
        payloads = tuple(row["payload"] for row, _, _ in selected)
        segments = {segment.segment_id: segment for _, _, segment in selected}
        if len(segments) != 1:
            raise ValueError("s7-cashflow-nav-lineage-segment-mismatch")
        private_basis = _cashflow_nav_basis_signature(
            payloads=payloads,
            segment=next(iter(segments.values())),
            base_currency=base_currency,
        )
        observations = tuple(
            BasisObservation(
                observation_id=str(row["dataset_observation_id"]),
                segment_id=str(segment.segment_id),
                canonical_entity_id=str(segment.canonical_entity_id),
                observed_at=date.fromisoformat(
                    str(
                        payload.get("event_date")
                        or payload.get("valuation_date")
                    )[:10]
                ),
                value=Decimal(str(payload.get("amount") or payload.get("nav"))),
                value_kind="cashflow" if "amount" in payload else "nav",
                basis=private_basis,
                source_currency=str(payload["currency"]),
                evidence=_basis_evidence_binding(
                    conn,
                    row=row,
                    snapshot_digest=snapshot_slice.digest,
                    evidence_right_id=snapshot_slice.request.evidence_right_id,
                    source_value_pointer="/amount" if "amount" in payload else "/nav",
                    segment=segment,
                ),
            )
            for row, snapshot_slice, segment in selected
            for payload in (row["payload"],)
        )
    else:
        observations = tuple(
            BasisObservation(
                observation_id=str(row["dataset_observation_id"]),
                segment_id=str(segment.segment_id),
                canonical_entity_id=str(segment.canonical_entity_id),
                observed_at=date.fromisoformat(str(payload["period_end"])[:10]),
                value=Decimal(str(payload["return_value"])),
                value_kind="periodic-return",
                basis=_periodic_basis_signature(
                    payload=payload,
                    segment=segment,
                    base_currency=base_currency,
                    fx_observations=fx_observations,
                ),
                source_currency=str(payload["currency"]),
                evidence=_basis_evidence_binding(
                    conn,
                    row=row,
                    snapshot_digest=snapshot_slice.digest,
                    evidence_right_id=snapshot_slice.request.evidence_right_id,
                    source_value_pointer="/return_value",
                    segment=segment,
                ),
            )
            for row, snapshot_slice, segment in selected
            for payload in (row["payload"],)
        )
    entity_grain = str(selected[0][2].entity_grain)
    exclusions = tuple(selected_exclusions)
    decision = emit_comparable_panel(
        observations,
        panel_kind=panel_kind,
        entity_grain=entity_grain,
        bundle_digest=bundle.bundle_digest,
        join_receipt_id=bundle.join_receipt_id,
        fx_observations=fx_observations,
        exclusions=exclusions,
    )
    store_receipt(conn, decision.receipt)
    verify_s7_panel_receipt(
        conn,
        receipt_id=decision.receipt.receipt_id,
        bundle=bundle,
        observations=observations,
        exclusions=exclusions,
        panel_kind=panel_kind,
        entity_grain=entity_grain,
        fx_observations=fx_observations,
    )
    return decision
