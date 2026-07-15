"""Evidence-only predecessor and team portability classifications for S7."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from quant_allocator.evidence.fixtures.s7 import (
    S7_CUTOFFS,
    S7BundleContract,
    S7FixtureManifest,
    s7_source_requests,
    verify_s7_manifest,
)
from quant_allocator.evidence.lineage import (
    make_receipt,
    resolve_span,
    store_receipt,
    verify_receipt,
)
from quant_allocator.evidence.model import (
    ReceiptReference,
    ReconstructionReceipt,
    SnapshotBundle,
    SnapshotBundleRequest,
    SnapshotSlice,
    canonical_bytes,
    digest_id,
    sha256,
)
from quant_allocator.evidence.projections import project_entity_relationships
from quant_allocator.evidence.snapshot import as_known_bundle


PORTABILITY_CAVEAT = (
    "Documented lineage is not evidence that historical skill transferred."
)
_TERMS_DATASET_ID = "dataset:s7-lineage-terms"
_RELATIONSHIP_SCHEMA_ID = "schema:s7-relationship-evidence-v1"
_PORTABILITY_RELATION_TYPES = frozenset(
    {"predecessor_claim", "employed_by", "transfer_scope", "contradicts_transfer"}
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


class PortabilityState(StrEnum):
    """The five ruled S7 portability evidence states."""

    DOCUMENTED_CLAIM = "documented-claim"
    PARTIAL_SUPPORT = "partial-support"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class PortabilityEvidenceFinding:
    """One evidence-status finding; it never carries historical observations."""

    finding_id: str
    state: PortabilityState
    predecessor_entity_id: str | None
    current_entity_id: str | None
    claimed_scope: str | None
    person_entity_id: str | None
    boundary_at: datetime | None
    relationship_ids: tuple[str, ...]
    evidence_item_ids: tuple[str, ...]
    evidence_span_ids: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    reason_codes: tuple[str, ...]
    caveat: str
    current_attestation: str
    live_attestation_ceiling: str
    receipt_id: str

    def __post_init__(self) -> None:
        if (
            self.caveat != PORTABILITY_CAVEAT
            or self.current_attestation != "D"
            or self.live_attestation_ceiling != "C"
        ):
            raise ValueError("s7-portability-attestation-contract-invalid")


@dataclass(frozen=True, slots=True)
class PortabilitySegmentRefusal:
    """Receipt-backed refusal to join a segment outside the authenticated bundle."""

    refusal_id: str
    pointer: str
    reason_code: str
    caveat: str
    current_attestation: str
    live_attestation_ceiling: str
    receipt_id: str

    def __post_init__(self) -> None:
        if (
            self.reason_code != "predecessor-segment-not-authenticated-in-bundle"
            or self.caveat != PORTABILITY_CAVEAT
            or self.current_attestation != "D"
            or self.live_attestation_ceiling != "C"
        ):
            raise ValueError("s7-portability-segment-refusal-invalid")


@dataclass(frozen=True, slots=True)
class PortabilityEvidenceResult:
    """Evidence-only portability result over the reviewed hedge-fund terms bundle."""

    cutoff_name: str
    bundle_digest: str
    join_receipt_id: str
    terms_snapshot_digest: str
    terms_slice_receipt_id: str
    findings: tuple[PortabilityEvidenceFinding, ...]
    segment_link_refusal: PortabilitySegmentRefusal
    receipt_ids: tuple[str, ...]


def _finding_payload(finding: PortabilityEvidenceFinding) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "state": finding.state.value,
        "predecessor_entity_id": finding.predecessor_entity_id,
        "current_entity_id": finding.current_entity_id,
        "claimed_scope": finding.claimed_scope,
        "person_entity_id": finding.person_entity_id,
        "boundary_at": finding.boundary_at,
        "relationship_ids": finding.relationship_ids,
        "evidence_item_ids": finding.evidence_item_ids,
        "evidence_span_ids": finding.evidence_span_ids,
        "missing_evidence": finding.missing_evidence,
        "reason_codes": finding.reason_codes,
        "caveat": finding.caveat,
        "current_attestation": finding.current_attestation,
        "live_attestation_ceiling": finding.live_attestation_ceiling,
    }


def _segment_refusal_payload(
    refusal: PortabilitySegmentRefusal,
) -> dict[str, object]:
    return {
        "refusal_id": refusal.refusal_id,
        "pointer": refusal.pointer,
        "reason_code": refusal.reason_code,
        "caveat": refusal.caveat,
        "current_attestation": refusal.current_attestation,
        "live_attestation_ceiling": refusal.live_attestation_ceiling,
    }


def portability_evidence_result_bytes(result: PortabilityEvidenceResult) -> bytes:
    """Serialize one portability result in deterministic canonical JSON."""
    if not isinstance(result, PortabilityEvidenceResult):
        raise TypeError("s7-portability-result-required")
    return canonical_bytes(
        {
            "cutoff_name": result.cutoff_name,
            "bundle_digest": result.bundle_digest,
            "join_receipt_id": result.join_receipt_id,
            "terms_snapshot_digest": result.terms_snapshot_digest,
            "terms_slice_receipt_id": result.terms_slice_receipt_id,
            "findings": tuple(
                _finding_payload(finding)
                for finding in sorted(
                    result.findings, key=lambda finding: finding.finding_id
                )
            ),
            "segment_link_refusal": _segment_refusal_payload(
                result.segment_link_refusal
            ),
            "receipt_ids": tuple(sorted(result.receipt_ids)),
        }
    )


@dataclass(frozen=True, slots=True)
class _RelationshipEvidence:
    relationship_id: str
    evidence_item_id: str
    evidence_span_id: str
    observation_id: str
    version_id: str
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    temporal_type: str
    effective_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    scope: str


def _finding(
    *,
    state: PortabilityState,
    predecessor_entity_id: str | None,
    current_entity_id: str | None,
    claimed_scope: str | None,
    person_entity_id: str | None,
    boundary_at: datetime | None,
    relationships: tuple[_RelationshipEvidence, ...],
    missing_evidence: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> PortabilityEvidenceFinding:
    ordered = tuple(sorted(relationships, key=lambda row: row.relationship_id))
    identity = {
        "state": state.value,
        "predecessor_entity_id": predecessor_entity_id,
        "current_entity_id": current_entity_id,
        "claimed_scope": claimed_scope,
        "person_entity_id": person_entity_id,
        "boundary_at": boundary_at,
        "relationship_ids": tuple(row.relationship_id for row in ordered),
        "missing_evidence": tuple(sorted(missing_evidence)),
        "reason_codes": tuple(sorted(reason_codes)),
    }
    return PortabilityEvidenceFinding(
        digest_id("s7-portability-finding", identity),
        state,
        predecessor_entity_id,
        current_entity_id,
        claimed_scope,
        person_entity_id,
        boundary_at,
        identity["relationship_ids"],
        tuple(sorted({row.evidence_item_id for row in ordered})),
        tuple(sorted({row.evidence_span_id for row in ordered})),
        identity["missing_evidence"],
        identity["reason_codes"],
        PORTABILITY_CAVEAT,
        "D",
        "C",
        "pending",
    )


def _visible_by(
    relationship: _RelationshipEvidence, cutoff: datetime
) -> bool:
    if relationship.temporal_type == "point":
        return (
            relationship.effective_at is not None
            and relationship.effective_from is None
            and relationship.effective_to is None
            and relationship.effective_at <= cutoff
        )
    return (
        relationship.temporal_type == "interval"
        and relationship.effective_at is None
        and relationship.effective_from is not None
        and relationship.effective_from <= cutoff
        and (
            relationship.effective_to is None
            or relationship.effective_from < relationship.effective_to
        )
    )


def _intervals_overlap(
    left: _RelationshipEvidence, right: _RelationshipEvidence
) -> bool:
    if left.effective_from is None or right.effective_from is None:
        return False
    start = max(left.effective_from, right.effective_from)
    ends = tuple(
        end for end in (left.effective_to, right.effective_to) if end is not None
    )
    return not ends or start < min(ends)


def _intervals_abut(
    left: _RelationshipEvidence, right: _RelationshipEvidence
) -> bool:
    return (
        left.effective_to is not None
        and left.effective_to == right.effective_from
    ) or (
        right.effective_to is not None
        and right.effective_to == left.effective_from
    )


def _classify_relationships(
    relationships: tuple[_RelationshipEvidence, ...], *, cutoff: datetime
) -> tuple[PortabilityEvidenceFinding, ...]:
    """Classify already-authenticated relationship evidence at one decision cutoff."""
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("s7-portability-cutoff-timezone-required")
    if len({row.relationship_id for row in relationships}) != len(relationships):
        raise ValueError("s7-portability-relationship-identity-duplicate")
    visible = tuple(
        sorted(
            (row for row in relationships if _visible_by(row, cutoff)),
            key=lambda row: row.relationship_id,
        )
    )
    claims = tuple(
        row
        for row in visible
        if row.relation_type == "predecessor_claim"
        and row.temporal_type == "point"
        and row.scope == "identity-claim"
        and row.source_entity_id.startswith("manager:")
        and row.target_entity_id.startswith("manager:")
    )
    if not claims:
        evidence = tuple(
            row
            for row in visible
            if row.relation_type
            in {"employed_by", "transfer_scope", "contradicts_transfer"}
        )
        return (
            _finding(
                state=PortabilityState.REFUSED,
                predecessor_entity_id=None,
                current_entity_id=None,
                claimed_scope=None,
                person_entity_id=None,
                boundary_at=None,
                relationships=evidence,
                missing_evidence=("predecessor-identity-edge",),
                reason_codes=("predecessor-identity-edge-missing",),
            ),
        )

    findings: list[PortabilityEvidenceFinding] = []
    for claim in claims:
        predecessor = claim.source_entity_id
        current = claim.target_entity_id
        findings.append(
            _finding(
                state=PortabilityState.DOCUMENTED_CLAIM,
                predecessor_entity_id=predecessor,
                current_entity_id=current,
                claimed_scope="identity-claim",
                person_entity_id=None,
                boundary_at=claim.effective_at,
                relationships=(claim,),
                missing_evidence=(
                    "team-transfer-evidence",
                    "process-continuity-evidence",
                    "historical-skill-transfer-evidence",
                ),
                reason_codes=("explicit-versioned-predecessor-identity-claim",),
            )
        )
        predecessor_employment = tuple(
            row
            for row in visible
            if row.relation_type == "employed_by"
            and row.source_entity_id.startswith("person:")
            and row.target_entity_id == predecessor
        )
        current_employment = tuple(
            row
            for row in visible
            if row.relation_type == "employed_by"
            and row.source_entity_id.startswith("person:")
            and row.target_entity_id == current
        )
        scopes = tuple(
            row
            for row in visible
            if row.relation_type == "transfer_scope"
            and row.source_entity_id.startswith("person:")
        )
        contradictions = tuple(
            row
            for row in visible
            if row.relation_type == "contradicts_transfer"
            and row.source_entity_id.startswith("person:")
        )

        for prior in predecessor_employment:
            same_person_current = tuple(
                row
                for row in current_employment
                if row.source_entity_id == prior.source_entity_id
            )
            same_person_scopes = tuple(
                row for row in scopes if row.source_entity_id == prior.source_entity_id
            )
            same_person_contradictions = tuple(
                row
                for row in contradictions
                if row.source_entity_id == prior.source_entity_id
            )

            for contradiction in same_person_contradictions:
                exact_positive = tuple(
                    scope
                    for scope in same_person_scopes
                    if scope.target_entity_id == contradiction.target_entity_id
                )
                findings.append(
                    _finding(
                        state=PortabilityState.CONTRADICTED,
                        predecessor_entity_id=predecessor,
                        current_entity_id=current,
                        claimed_scope=contradiction.target_entity_id,
                        person_entity_id=prior.source_entity_id,
                        boundary_at=contradiction.effective_at,
                        relationships=(
                            claim,
                            prior,
                            contradiction,
                            *exact_positive,
                        ),
                        missing_evidence=(),
                        reason_codes=("sourced-same-person-same-scope-contradiction",),
                    )
                )

            for scope in same_person_scopes:
                if any(
                    contradiction.target_entity_id == scope.target_entity_id
                    for contradiction in same_person_contradictions
                ):
                    continue
                if same_person_current:
                    continue
                findings.append(
                    _finding(
                        state=PortabilityState.UNRESOLVED,
                        predecessor_entity_id=predecessor,
                        current_entity_id=current,
                        claimed_scope=scope.target_entity_id,
                        person_entity_id=prior.source_entity_id,
                        boundary_at=claim.effective_at,
                        relationships=(claim, prior, scope),
                        missing_evidence=("current-team-employment-evidence",),
                        reason_codes=("scope-evidence-without-current-team-chronology",),
                    )
                )

            if not same_person_scopes:
                for current_row in same_person_current:
                    reason_codes = ["person-chronology-without-transfer-scope"]
                    missing = ["transfer-scope-evidence", "process-continuity-evidence"]
                    if _intervals_abut(prior, current_row):
                        reason_codes.append("employment-intervals-abut-no-overlap")
                        missing.append("employment-overlap-evidence")
                    elif not _intervals_overlap(prior, current_row):
                        reason_codes.append("employment-intervals-do-not-overlap")
                        missing.append("employment-overlap-evidence")
                    findings.append(
                        _finding(
                            state=PortabilityState.PARTIAL_SUPPORT,
                            predecessor_entity_id=predecessor,
                            current_entity_id=current,
                            claimed_scope="employment-chronology",
                            person_entity_id=prior.source_entity_id,
                            boundary_at=claim.effective_at,
                            relationships=(claim, prior, current_row),
                            missing_evidence=tuple(missing),
                            reason_codes=tuple(reason_codes),
                        )
                    )

    unique = {finding.finding_id: finding for finding in findings}
    return tuple(sorted(unique.values(), key=lambda finding: finding.finding_id))


@dataclass(frozen=True, slots=True)
class _PreparedPortabilityOutput:
    value: PortabilityEvidenceFinding | PortabilitySegmentRefusal
    receipt: ReconstructionReceipt


@dataclass(frozen=True, slots=True)
class _PreparedPortabilityEvidence:
    bundle: SnapshotBundle
    terms_slice: SnapshotSlice
    relationships: tuple[_RelationshipEvidence, ...]
    outputs: tuple[_PreparedPortabilityOutput, ...]


def _parse_time(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("s7-portability-time-invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("s7-portability-time-invalid")
    return parsed


def _require_hedge_bundle_contract(
    bundle: SnapshotBundle,
    contract: S7BundleContract,
    *,
    cutoff_name: str,
) -> SnapshotSlice:
    slice_digests = tuple(
        (slice_.request.dataset_id, slice_.digest) for slice_ in bundle.slices
    )
    slice_receipts = tuple(
        (slice_.request.dataset_id, slice_.receipt_id) for slice_ in bundle.slices
    )
    if (
        contract.scenario != "hedge-fund"
        or contract.cutoff_name != cutoff_name
        or bundle.bundle_digest != contract.analytic_bundle_digest
        or bundle.join_receipt_id != contract.analytic_join_receipt_id
        or slice_digests != contract.analytic_slice_digests
        or slice_receipts != contract.analytic_slice_receipt_ids
        or bundle.request.decision_at != S7_CUTOFFS[cutoff_name]
        or bundle.request.join_keys != ("field_dictionary_version",)
        or bundle.request.join_policy != "s7-track-lineage-v1"
        or any(
            source.revision_mode != "latest-known"
            for source in bundle.request.sources
        )
    ):
        raise ValueError("s7-portability-bundle-contract-mismatch")
    terms_slices = tuple(
        slice_
        for slice_ in bundle.slices
        if slice_.request.dataset_id == _TERMS_DATASET_ID
    )
    if len(terms_slices) != 1:
        raise ValueError("s7-portability-terms-slice-missing")
    terms_slice = terms_slices[0]
    if (
        terms_slice.request.access_context != "shortlisted-nda"
        or terms_slice.request.licence_purpose != "s7-research"
        or terms_slice.request.include_unresolved is not True
        or terms_slice.receipt_id is None
    ):
        raise ValueError("s7-portability-terms-right-mismatch")
    return terms_slice


def _materialize_hedge_bundle(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    cutoff_name: str,
) -> tuple[SnapshotBundle, SnapshotSlice]:
    if cutoff_name not in S7_CUTOFFS:
        raise ValueError("s7-unknown-cutoff")
    if not verify_s7_manifest(conn, manifest):
        raise ValueError("s7-substrate-conflict")
    contract = next(
        (
            candidate
            for candidate in manifest.bundle_contracts
            if candidate.scenario == "hedge-fund"
            and candidate.cutoff_name == cutoff_name
        ),
        None,
    )
    if contract is None:
        raise ValueError("s7-portability-bundle-contract-missing")
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS[cutoff_name],
            s7_source_requests(
                manifest,
                scenario="hedge-fund",
                cutoff_name=cutoff_name,
                revision_mode="latest-known",
            ),
            ("field_dictionary_version",),
            "s7-track-lineage-v1",
        ),
    )
    terms_slice = _require_hedge_bundle_contract(
        bundle, contract, cutoff_name=cutoff_name
    )
    verify_receipt(conn, bundle.join_receipt_id, bundle)
    for slice_ in bundle.slices:
        if slice_.receipt_id is None:
            raise ValueError("s7-portability-slice-receipt-missing")
        verify_receipt(conn, slice_.receipt_id, bundle)
    return bundle, terms_slice


def _relationship_evidence(
    conn: sqlite3.Connection,
    terms_slice: SnapshotSlice,
    relationship: Mapping[str, object],
) -> _RelationshipEvidence:
    relationship_id = relationship.get("entity_relationship_id")
    item_id = relationship.get("source_evidence_item_id")
    span_id = relationship.get("evidence_span_id")
    observation_id = relationship.get("dataset_observation_id")
    version_id = relationship.get("dataset_version_id")
    identifiers = (relationship_id, item_id, span_id, observation_id, version_id)
    if not all(isinstance(identifier, str) and identifier for identifier in identifiers):
        raise ValueError("s7-portability-relationship-closure-invalid")
    item = conn.execute(
        "SELECT i.*,s.dataset_id FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) WHERE i.evidence_item_id=?",
        (item_id,),
    ).fetchone()
    span = conn.execute(
        "SELECT * FROM evidence_span WHERE evidence_span_id=?", (span_id,)
    ).fetchone()
    observation = conn.execute(
        "SELECT * FROM dataset_observation WHERE dataset_observation_id=?",
        (observation_id,),
    ).fetchone()
    version = conn.execute(
        "SELECT * FROM dataset_version WHERE dataset_version_id=?", (version_id,)
    ).fetchone()
    slice_rows = {
        (str(row["evidence_item_id"]), str(row["dataset_observation_id"])): row
        for row in terms_slice.rows
    }
    if (
        item is None
        or span is None
        or observation is None
        or version is None
        or item["dataset_id"] != _TERMS_DATASET_ID
        or item["record_kind"] != "s7-relationship-evidence"
        or item["payload_schema_id"] != _RELATIONSHIP_SCHEMA_ID
        or span["evidence_item_id"] != item_id
        or span["json_pointer"] != "/assertion"
        or observation["evidence_item_id"] != item_id
        or observation["dataset_version_id"] != version_id
        or observation["observation_status"] != "present"
        or version["dataset_id"] != _TERMS_DATASET_ID
        or (str(item_id), str(observation_id)) not in slice_rows
    ):
        raise ValueError("s7-portability-relationship-closure-invalid")
    payload = json.loads(item["payload_json"])
    if not isinstance(payload, dict):
        raise ValueError("s7-portability-relationship-closure-invalid")
    payload_from = _parse_time(payload.get("effective_from"))
    payload_to = _parse_time(payload.get("effective_to") or None)
    projected_temporal_type = relationship.get("temporal_type")
    projected_at = _parse_time(relationship.get("effective_at"))
    projected_from = _parse_time(relationship.get("effective_from"))
    projected_to = _parse_time(relationship.get("effective_to"))
    point_shape_valid = (
        projected_temporal_type == "point"
        and projected_at == payload_from
        and projected_from is None
        and projected_to is None
        and payload_to is None
    )
    interval_shape_valid = (
        projected_temporal_type == "interval"
        and projected_at is None
        and projected_from == payload_from
        and projected_to == payload_to
    )
    if (
        item["content_sha256"] != sha256(canonical_bytes(payload))
        or resolve_span(conn, str(span_id))["text"] != payload.get("assertion")
        or span["start_char"] != 0
        or span["end_char"] != len(str(payload.get("assertion", "")))
        or relationship.get("relation_type") != payload.get("relation_type")
        or relationship.get("source_entity_id") != payload.get("source_entity_id")
        or relationship.get("target_entity_id") != payload.get("target_entity_id")
        or relationship.get("version") != item["version"]
        or not (point_shape_valid or interval_shape_valid)
    ):
        raise ValueError("s7-portability-relationship-closure-invalid")
    relation_type = str(payload.get("relation_type"))
    scope = payload.get("scope")
    if (
        relation_type not in _PORTABILITY_RELATION_TYPES
        or not isinstance(scope, str)
        or not scope
        or relation_type == "predecessor_claim"
        and scope != "identity-claim"
        or relation_type == "employed_by"
        and scope != "employment"
        or relation_type in {"transfer_scope", "contradicts_transfer"}
        and scope != relationship.get("target_entity_id")
    ):
        raise ValueError("s7-portability-relationship-scope-invalid")
    return _RelationshipEvidence(
        str(relationship_id),
        str(item_id),
        str(span_id),
        str(observation_id),
        str(version_id),
        relation_type,
        str(relationship["source_entity_id"]),
        str(relationship["target_entity_id"]),
        str(relationship["temporal_type"]),
        projected_at,
        projected_from,
        projected_to,
        scope,
    )


def _portability_relationships(
    conn: sqlite3.Connection, terms_slice: SnapshotSlice
) -> tuple[_RelationshipEvidence, ...]:
    relationships = tuple(
        _relationship_evidence(conn, terms_slice, row)
        for row in project_entity_relationships(conn, terms_slice)
        if row.get("relation_type") in _PORTABILITY_RELATION_TYPES
    )
    if len({row.relationship_id for row in relationships}) != len(relationships):
        raise ValueError("s7-portability-relationship-identity-duplicate")
    return tuple(sorted(relationships, key=lambda row: row.relationship_id))


def _bundle_parameters(
    bundle: SnapshotBundle,
    terms_slice: SnapshotSlice,
    *,
    cutoff_name: str,
) -> dict[str, object]:
    return {
        "cutoff_name": cutoff_name,
        "decision_at": S7_CUTOFFS[cutoff_name],
        "bundle_digest": bundle.bundle_digest,
        "join_receipt_id": bundle.join_receipt_id,
        "bundle_datasets": tuple(
            source.dataset_id for source in bundle.request.sources
        ),
        "terms_dataset_id": _TERMS_DATASET_ID,
        "terms_access_context": terms_slice.request.access_context,
        "terms_licence_purpose": terms_slice.request.licence_purpose,
        "terms_right_id": terms_slice.request.evidence_right_id,
        "terms_snapshot_digest": terms_slice.digest,
        "terms_slice_receipt_id": terms_slice.receipt_id,
        "terms_revision_mode": terms_slice.request.revision_mode,
    }


def _relationship_references(
    finding: PortabilityEvidenceFinding,
    relationships: tuple[_RelationshipEvidence, ...],
    terms_slice: SnapshotSlice,
) -> tuple[ReceiptReference, ...]:
    by_id = {row.relationship_id: row for row in relationships}
    output = f"/portability/findings/{finding.finding_id}"
    common = {
        "output_field": output,
        "disposition": (
            "refused" if finding.state is PortabilityState.REFUSED else "included"
        ),
        "reason_code": (
            finding.reason_codes[0]
            if finding.state is PortabilityState.REFUSED
            else ""
        ),
        "source_schema_id": _RELATIONSHIP_SCHEMA_ID,
    }
    references: list[ReceiptReference] = []
    for relationship_id in finding.relationship_ids:
        row = by_id.get(relationship_id)
        if row is None:
            raise ValueError("s7-portability-finding-relationship-missing")
        references.extend(
            (
                ReceiptReference(
                    reference_type="entity-relationship",
                    reference_id=row.relationship_id,
                    source_field="/",
                    role="input",
                    **common,
                ),
                ReceiptReference(
                    reference_type="evidence-item",
                    reference_id=row.evidence_item_id,
                    source_field="/assertion",
                    role="input",
                    **common,
                ),
                ReceiptReference(
                    reference_type="evidence-span",
                    reference_id=row.evidence_span_id,
                    source_field="/assertion",
                    role="input",
                    **common,
                ),
                ReceiptReference(
                    reference_type="dataset-observation",
                    reference_id=row.observation_id,
                    source_field="/",
                    role="input",
                    **common,
                ),
                ReceiptReference(
                    reference_type="dataset-version",
                    reference_id=row.version_id,
                    source_field="/",
                    role="input",
                    **common,
                ),
            )
        )
    references.extend(
        (
            ReceiptReference(
                reference_type="evidence-right",
                reference_id=terms_slice.request.evidence_right_id,
                source_field="/",
                role="filter",
                **common,
            ),
            ReceiptReference(
                reference_type="snapshot",
                reference_id=terms_slice.digest,
                source_field="/",
                role="input",
                **common,
            ),
        )
    )
    return tuple(references)


def _segment_refusal_references(
    terms_slice: SnapshotSlice,
    *,
    refusal: PortabilitySegmentRefusal,
) -> tuple[ReceiptReference, ...]:
    common = {
        "output_field": refusal.pointer,
        "disposition": "refused",
        "reason_code": refusal.reason_code,
        "source_schema_id": "schema:generic-v1",
        "source_field": "/",
    }
    version_ids = tuple(
        sorted({str(row["dataset_version_id"]) for row in terms_slice.rows})
    )
    return (
        *(
            ReceiptReference(
                reference_type="dataset-version",
                reference_id=version_id,
                role="input",
                **common,
            )
            for version_id in version_ids
        ),
        ReceiptReference(
            reference_type="evidence-right",
            reference_id=terms_slice.request.evidence_right_id,
            role="filter",
            **common,
        ),
        ReceiptReference(
            reference_type="snapshot",
            reference_id=terms_slice.digest,
            role="input",
            **common,
        ),
    )


def _make_portability_receipt(
    *,
    claim_id: str,
    output_locator: str,
    parameters: Mapping[str, object],
    value: Mapping[str, object],
    references: tuple[ReceiptReference, ...],
) -> ReconstructionReceipt:
    return make_receipt(
        claim_id=claim_id,
        output_locator=output_locator,
        input_digest=sha256(
            canonical_bytes({"s7-portability-input": dict(parameters)})
        ),
        output_schema_id="s7-portability-finding/v1",
        current_attestation="D",
        live_attestation_ceiling="C",
        algorithm_id="s7-portability/v1",
        algorithm_version="1",
        parameters=parameters,
        value=value,
        references=references,
    )


def _prepare_portability_evidence(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    cutoff_name: str,
) -> _PreparedPortabilityEvidence:
    bundle, terms_slice = _materialize_hedge_bundle(
        conn, manifest, cutoff_name=cutoff_name
    )
    relationships = _portability_relationships(conn, terms_slice)
    findings = _classify_relationships(
        relationships, cutoff=S7_CUTOFFS[cutoff_name]
    )
    parameters = _bundle_parameters(
        bundle, terms_slice, cutoff_name=cutoff_name
    )
    prepared: list[_PreparedPortabilityOutput] = []
    for draft in findings:
        output = f"/portability/findings/{draft.finding_id}"
        finding_parameters = {
            **parameters,
            "finding_id": draft.finding_id,
            "relationship_ids": draft.relationship_ids,
            "evidence_tuples": tuple(
                (
                    row.relationship_id,
                    row.evidence_item_id,
                    row.evidence_span_id,
                    row.observation_id,
                    row.version_id,
                )
                for row in relationships
                if row.relationship_id in draft.relationship_ids
            ),
            "state": draft.state.value,
        }
        receipt = _make_portability_receipt(
            claim_id="predecessor_portability_evidence",
            output_locator=output,
            parameters=finding_parameters,
            value=_finding_payload(draft),
            references=_relationship_references(
                draft, relationships, terms_slice
            ),
        )
        prepared.append(
            _PreparedPortabilityOutput(
                replace(draft, receipt_id=receipt.receipt_id), receipt
            )
        )
    refusal_id = digest_id(
        "s7-portability-refusal",
        {
            "cutoff_name": cutoff_name,
            "bundle_digest": bundle.bundle_digest,
            "reason_code": "predecessor-segment-not-authenticated-in-bundle",
        },
    )
    refusal_draft = PortabilitySegmentRefusal(
        refusal_id,
        "/portability/segment-link-refusal",
        "predecessor-segment-not-authenticated-in-bundle",
        PORTABILITY_CAVEAT,
        "D",
        "C",
        "pending",
    )
    refusal_parameters = {
        **parameters,
        "refusal_id": refusal_id,
        "reason_code": refusal_draft.reason_code,
    }
    refusal_receipt = _make_portability_receipt(
        claim_id="predecessor_portability_segment_refusal",
        output_locator=refusal_draft.pointer,
        parameters=refusal_parameters,
        value=_segment_refusal_payload(refusal_draft),
        references=_segment_refusal_references(
            terms_slice, refusal=refusal_draft
        ),
    )
    prepared.append(
        _PreparedPortabilityOutput(
            replace(refusal_draft, receipt_id=refusal_receipt.receipt_id),
            refusal_receipt,
        )
    )
    return _PreparedPortabilityEvidence(
        bundle,
        terms_slice,
        relationships,
        tuple(
            sorted(
                prepared,
                key=lambda item: item.receipt.output_locator,
            )
        ),
    )


def _persisted_references(
    conn: sqlite3.Connection, receipt_id: str
) -> tuple[ReceiptReference, ...]:
    references = []
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
            raise ValueError("s7-portability-receipt-closure-invalid")
        references.append(
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
    return tuple(references)


def _verify_prepared_output(
    conn: sqlite3.Connection,
    *,
    prepared: _PreparedPortabilityOutput,
    bundle: SnapshotBundle,
) -> None:
    persisted = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
        (prepared.receipt.receipt_id,),
    ).fetchone()
    expected = prepared.receipt
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
    if (
        persisted is None
        or tuple(persisted) != expected_header
        or _persisted_references(conn, expected.receipt_id) != expected.references
    ):
        raise ValueError("s7-portability-receipt-closure-invalid")
    verify_receipt(conn, expected.receipt_id, bundle)


def verify_s7_portability_evidence_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    manifest: S7FixtureManifest,
    cutoff_name: str,
) -> None:
    """Reclassify exact terms evidence before applying the shared receipt seal."""
    prepared = _prepare_portability_evidence(
        conn, manifest, cutoff_name=cutoff_name
    )
    expected = next(
        (
            output
            for output in prepared.outputs
            if output.receipt.receipt_id == receipt_id
        ),
        None,
    )
    if expected is None:
        raise ValueError("s7-portability-receipt-closure-invalid")
    _verify_prepared_output(conn, prepared=expected, bundle=prepared.bundle)


def assess_s7_portability_evidence(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    cutoff_name: str,
) -> PortabilityEvidenceResult:
    """Assess only authenticated hedge-fund terms evidence at a reviewed cutoff."""
    prepared = _prepare_portability_evidence(
        conn, manifest, cutoff_name=cutoff_name
    )
    for output in prepared.outputs:
        store_receipt(conn, output.receipt)
        _verify_prepared_output(
            conn, prepared=output, bundle=prepared.bundle
        )
    findings = tuple(
        output.value
        for output in prepared.outputs
        if isinstance(output.value, PortabilityEvidenceFinding)
    )
    refusals = tuple(
        output.value
        for output in prepared.outputs
        if isinstance(output.value, PortabilitySegmentRefusal)
    )
    if len(refusals) != 1:
        raise ValueError("s7-portability-segment-refusal-missing")
    receipt_ids = tuple(
        sorted(output.receipt.receipt_id for output in prepared.outputs)
    )
    return PortabilityEvidenceResult(
        cutoff_name,
        prepared.bundle.bundle_digest,
        prepared.bundle.join_receipt_id,
        prepared.terms_slice.digest,
        str(prepared.terms_slice.receipt_id),
        tuple(sorted(findings, key=lambda finding: finding.finding_id)),
        refusals[0],
        receipt_ids,
    )
