"""Point-in-time vintage findings over authenticated paired S7 bundles."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from quant_allocator.evidence.fixtures.s7 import (
    S7_CUTOFFS,
    S7BundleContract,
    S7FixtureManifest,
    s7_source_requests,
    verify_s7_manifest,
)
from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
from quant_allocator.evidence.lineage import (
    make_receipt,
    store_receipt,
    verify_receipt,
)
from quant_allocator.evidence.model import (
    ReceiptReference,
    ReconstructionReceipt,
    DatasetSliceRequest,
    SnapshotBundle,
    SnapshotBundleRequest,
    canonical_bytes,
    digest_id,
    sha256,
)
from quant_allocator.evidence.projections import (
    project_entity_mappings,
    project_universe_memberships,
)
from quant_allocator.evidence.snapshot import as_known_bundle, as_known_slice


_RECORD_FINDING_TYPES = frozenset(
    {
        "return-backfill",
        "retroactive-membership",
        "later-dead-product",
        "return-restatement",
        "membership-restatement",
        "withdrawal-or-tombstone",
    }
)


@dataclass(frozen=True, slots=True)
class RecordVintageFinding:
    """One record-level change that became knowable after its effective date."""

    finding_id: str
    finding_type: str
    dataset_id: str
    source_record_id: str
    effective_at: datetime
    first_known_at: datetime
    affected_observation_ids: tuple[str, ...]
    prior_value: Decimal | None
    later_value: Decimal | None
    reason_code: str
    receipt_id: str
    mapping_ids: tuple[str, ...] = ()
    membership_ids: tuple[str, ...] = ()
    observation_membership_link_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.finding_type not in _RECORD_FINDING_TYPES:
            raise ValueError("s7-vintage-finding-type-invalid")
        if not all(
            (
                self.finding_id,
                self.dataset_id,
                self.source_record_id,
                self.affected_observation_ids,
                self.reason_code,
                self.receipt_id,
            )
        ):
            raise ValueError("s7-vintage-finding-identity-incomplete")
        if len(self.affected_observation_ids) != len(
            set(self.affected_observation_ids)
        ):
            raise ValueError("s7-vintage-observation-identity-duplicate")
        has_values = self.prior_value is not None and self.later_value is not None
        if (self.finding_type == "return-restatement") != has_values:
            raise ValueError("s7-vintage-restatement-values-invalid")
        if any(
            value is not None and not isinstance(value, Decimal)
            for value in (self.prior_value, self.later_value)
        ):
            raise ValueError("s7-vintage-decimal-required")


@dataclass(frozen=True, slots=True)
class CoverageVintageFinding:
    """Dataset-level evidence that row absence cannot identify disappearance."""

    finding_id: str
    finding_type: str
    dataset_id: str
    dataset_version_ids: tuple[str, ...]
    first_known_at: datetime
    reason_code: str
    receipt_id: str

    def __post_init__(self) -> None:
        if self.finding_type != "absence-not-inferable":
            raise ValueError("s7-vintage-coverage-type-invalid")
        if not all(
            (
                self.finding_id,
                self.dataset_id,
                self.dataset_version_ids,
                self.reason_code,
                self.receipt_id,
            )
        ):
            raise ValueError("s7-vintage-coverage-identity-incomplete")


VintageFinding = RecordVintageFinding | CoverageVintageFinding


@dataclass(frozen=True, slots=True)
class HistoricalSelectionRefusal:
    """A dataset-scoped refusal to claim a complete historical selection set."""

    refusal_id: str
    pointer: str
    dataset_id: str
    reason_code: str
    reason_codes: tuple[str, ...]
    receipt_id: str


@dataclass(frozen=True, slots=True)
class VintageAuditResult:
    """Authenticated bundle identities and deterministic vintage outputs."""

    scenario: str
    cutoff_name: str
    analytic_bundle_digest: str
    audit_bundle_digest: str
    analytic_join_receipt_id: str
    audit_join_receipt_id: str
    findings: tuple[VintageFinding, ...]
    historical_selection_refusals: tuple[HistoricalSelectionRefusal, ...]
    receipt_ids: tuple[str, ...]


def vintage_result_bytes(result: VintageAuditResult) -> bytes:
    """Serialize a vintage result with exact decimal strings and canonical ordering."""
    if not isinstance(result, VintageAuditResult):
        raise TypeError("s7-vintage-result-required")
    findings = tuple(
        _finding_payload(finding)
        if isinstance(finding, RecordVintageFinding)
        else _coverage_payload(finding)
        for finding in result.findings
    )
    return canonical_bytes(
        {
            "scenario": result.scenario,
            "cutoff_name": result.cutoff_name,
            "analytic_bundle_digest": result.analytic_bundle_digest,
            "audit_bundle_digest": result.audit_bundle_digest,
            "analytic_join_receipt_id": result.analytic_join_receipt_id,
            "audit_join_receipt_id": result.audit_join_receipt_id,
            "findings": findings,
            "historical_selection_refusals": tuple(
                _refusal_payload(refusal)
                for refusal in result.historical_selection_refusals
            ),
            "receipt_ids": result.receipt_ids,
        }
    )


@dataclass(frozen=True, slots=True)
class _BundlePair:
    contract: S7BundleContract
    analytic: SnapshotBundle
    audit: SnapshotBundle


@dataclass(frozen=True, slots=True)
class _PreparedFinding:
    finding: VintageFinding
    receipt: ReconstructionReceipt
    death_span_closure: tuple[tuple[str, str, str], ...] = ()
    x3_closure: tuple["_X3Closure", ...] = ()


@dataclass(frozen=True, slots=True)
class _PreparedRefusal:
    refusal: HistoricalSelectionRefusal
    receipt: ReconstructionReceipt


@dataclass(frozen=True, slots=True)
class _X3Closure:
    dataset_id: str
    snapshot_digest: str
    slice_receipt_id: str
    mapping_id: str
    membership_id: str
    link_id: str
    affected_observation_id: str


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("s7-vintage-time-missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("s7-vintage-time-invalid")
    return parsed


def _require_pair_contract(
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> None:
    analytic = pair.analytic
    audit = pair.audit
    contract = pair.contract
    analytic_slices = tuple(
        (slice_.request.dataset_id, slice_.digest) for slice_ in analytic.slices
    )
    audit_slices = tuple(
        (slice_.request.dataset_id, slice_.digest) for slice_ in audit.slices
    )
    analytic_receipts = tuple(
        (slice_.request.dataset_id, slice_.receipt_id) for slice_ in analytic.slices
    )
    audit_receipts = tuple(
        (slice_.request.dataset_id, slice_.receipt_id) for slice_ in audit.slices
    )
    if (
        contract.scenario != scenario
        or contract.cutoff_name != cutoff_name
        or analytic.bundle_digest != contract.analytic_bundle_digest
        or audit.bundle_digest != contract.audit_bundle_digest
        or analytic.join_receipt_id != contract.analytic_join_receipt_id
        or audit.join_receipt_id != contract.audit_join_receipt_id
        or analytic_slices != contract.analytic_slice_digests
        or audit_slices != contract.audit_slice_digests
        or analytic_receipts != contract.analytic_slice_receipt_ids
        or audit_receipts != contract.audit_slice_receipt_ids
        or analytic.request.decision_at != audit.request.decision_at
        or analytic.request.join_keys != ("field_dictionary_version",)
        or audit.request.join_keys != ("field_dictionary_version",)
        or analytic.request.join_policy != "s7-track-lineage-v1"
        or audit.request.join_policy != "s7-track-lineage-v1"
        or len(analytic.request.sources) != len(audit.request.sources)
    ):
        raise ValueError("s7-vintage-bundle-contract-mismatch")
    for analytic_source, audit_source in zip(
        analytic.request.sources, audit.request.sources, strict=True
    ):
        if (
            analytic_source.revision_mode != "latest-known"
            or audit_source.revision_mode != "all-known-versions"
            or replace(analytic_source, revision_mode="all-known-versions")
            != audit_source
        ):
            raise ValueError("s7-vintage-pair-scope-mismatch")


def _materialize_pair(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
) -> _BundlePair:
    contract = next(
        (
            candidate
            for candidate in manifest.bundle_contracts
            if candidate.scenario == scenario and candidate.cutoff_name == cutoff_name
        ),
        None,
    )
    if contract is None:
        raise ValueError("s7-vintage-bundle-contract-missing")
    bundles = []
    for revision_mode in ("latest-known", "all-known-versions"):
        bundle = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS[cutoff_name],
                s7_source_requests(
                    manifest,
                    scenario=scenario,
                    cutoff_name=cutoff_name,
                    revision_mode=revision_mode,
                ),
                ("field_dictionary_version",),
                "s7-track-lineage-v1",
            ),
        )
        verify_receipt(conn, bundle.join_receipt_id, bundle)
        for slice_ in bundle.slices:
            if slice_.receipt_id is None:
                raise ValueError("s7-vintage-slice-receipt-missing")
            verify_receipt(conn, slice_.receipt_id, bundle)
        bundles.append(bundle)
    pair = _BundlePair(contract, bundles[0], bundles[1])
    _require_pair_contract(pair, scenario=scenario, cutoff_name=cutoff_name)
    return pair


def _pair_parameters(
    pair: _BundlePair, *, scenario: str, cutoff_name: str
) -> dict[str, object]:
    return {
        "scenario": scenario,
        "cutoff_name": cutoff_name,
        "analytic_bundle_digest": pair.analytic.bundle_digest,
        "audit_bundle_digest": pair.audit.bundle_digest,
        "analytic_join_receipt_id": pair.analytic.join_receipt_id,
        "audit_join_receipt_id": pair.audit.join_receipt_id,
        "analytic_slices": tuple(
            (slice_.request.dataset_id, slice_.digest, slice_.receipt_id)
            for slice_ in pair.analytic.slices
        ),
        "audit_slices": tuple(
            (slice_.request.dataset_id, slice_.digest, slice_.receipt_id)
            for slice_ in pair.audit.slices
        ),
    }


def _return_rows(pair: _BundlePair) -> tuple[tuple[Mapping[str, object], object], ...]:
    return tuple(
        (row, slice_)
        for slice_ in pair.audit.slices
        for row in slice_.rows
        if isinstance(row.get("payload"), Mapping)
        and "return_value" in row["payload"]
    )


def _row_metadata(
    conn: sqlite3.Connection, row: Mapping[str, object]
) -> sqlite3.Row:
    metadata = conn.execute(
        "SELECT i.revision_of,i.payload_schema_id,o.disappearance_reason "
        "FROM evidence_item i JOIN dataset_observation o USING(evidence_item_id) "
        "WHERE i.evidence_item_id=? AND o.dataset_observation_id=?",
        (row["evidence_item_id"], row["dataset_observation_id"]),
    ).fetchone()
    if metadata is None:
        raise ValueError("s7-vintage-row-closure-missing")
    return metadata


def _row_references(
    conn: sqlite3.Connection,
    row: Mapping[str, object],
    slice_: object,
    *,
    output_field: str,
    disposition: str = "included",
    reason_code: str = "",
) -> tuple[ReceiptReference, ...]:
    metadata = _row_metadata(conn, row)
    schema = str(metadata["payload_schema_id"])
    source_pointer = (
        "/return_value"
        if isinstance(row.get("payload"), Mapping)
        and "return_value" in row["payload"]
        else "/"
    )
    return tuple(
        ReceiptReference(
            output_field,
            reference_type,
            str(reference_id),
            disposition,
            reason_code,
            schema,
            source_field,
            role,
        )
        for reference_type, reference_id, source_field, role in (
            ("source-record", row["source_record_id"], "/", "input"),
            ("evidence-item", row["evidence_item_id"], source_pointer, "input"),
            ("dataset-observation", row["dataset_observation_id"], "/", "input"),
            ("dataset-version", row["dataset_version_id"], "/", "input"),
            ("evidence-right", slice_.request.evidence_right_id, "/", "filter"),
            ("snapshot", slice_.digest, "/", "input"),
        )
    )


def _finding_payload(finding: RecordVintageFinding) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "finding_type": finding.finding_type,
        "dataset_id": finding.dataset_id,
        "source_record_id": finding.source_record_id,
        "effective_at": finding.effective_at,
        "first_known_at": finding.first_known_at,
        "affected_observation_ids": finding.affected_observation_ids,
        "prior_value": (
            None if finding.prior_value is None else format(finding.prior_value, "f")
        ),
        "later_value": (
            None if finding.later_value is None else format(finding.later_value, "f")
        ),
        "reason_code": finding.reason_code,
        "mapping_ids": finding.mapping_ids,
        "membership_ids": finding.membership_ids,
        "observation_membership_link_ids": finding.observation_membership_link_ids,
    }


def _coverage_payload(finding: CoverageVintageFinding) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "finding_type": finding.finding_type,
        "dataset_id": finding.dataset_id,
        "dataset_version_ids": finding.dataset_version_ids,
        "first_known_at": finding.first_known_at,
        "reason_code": finding.reason_code,
    }


def _refusal_payload(refusal: HistoricalSelectionRefusal) -> dict[str, object]:
    return {
        "refusal_id": refusal.refusal_id,
        "pointer": refusal.pointer,
        "dataset_id": refusal.dataset_id,
        "reason_code": refusal.reason_code,
        "reason_codes": refusal.reason_codes,
    }


def _make_output_receipt(
    *,
    pair_parameters: Mapping[str, object],
    claim_id: str,
    output_locator: str,
    value: Mapping[str, object],
    references: tuple[ReceiptReference, ...],
) -> ReconstructionReceipt:
    parameters = {**pair_parameters, "output": dict(value)}
    return make_receipt(
        claim_id=claim_id,
        output_locator=output_locator,
        input_digest=sha256(canonical_bytes({"s7-vintage-input": parameters})),
        output_schema_id="s7-provenance-output/v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="s7-vintage-audit/v1",
        algorithm_version="1",
        parameters=parameters,
        value=dict(value),
        references=references,
    )


def _prepare_record_finding(
    *,
    pair_parameters: Mapping[str, object],
    draft: RecordVintageFinding,
    references: tuple[ReceiptReference, ...],
    death_span_closure: tuple[tuple[str, str, str], ...] = (),
    x3_closure: tuple[_X3Closure, ...] = (),
) -> _PreparedFinding:
    output = f"/vintage_findings/{draft.finding_id}"
    receipt = _make_output_receipt(
        pair_parameters=pair_parameters,
        claim_id="s7_vintage_finding",
        output_locator=output,
        value=_finding_payload(draft),
        references=references,
    )
    return _PreparedFinding(
        replace(draft, receipt_id=receipt.receipt_id),
        receipt,
        death_span_closure,
        x3_closure,
    )


def _prepare_restatements(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    rows = _return_rows(pair)
    by_item = {str(row["evidence_item_id"]): (row, slice_) for row, slice_ in rows}
    prepared = []
    pair_parameters = _pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name)
    for later, later_slice in rows:
        metadata = _row_metadata(conn, later)
        parent_id = metadata["revision_of"]
        if not isinstance(parent_id, str) or parent_id not in by_item:
            continue
        prior, prior_slice = by_item[parent_id]
        if (
            prior["source_record_id"] != later["source_record_id"]
            or prior["effective_at"] != later["effective_at"]
            or prior["observation_status"] != "present"
            or later["observation_status"] != "present"
        ):
            raise ValueError("s7-vintage-revision-chain-invalid")
        prior_payload = prior["payload"]
        later_payload = later["payload"]
        if not isinstance(prior_payload, Mapping) or not isinstance(
            later_payload, Mapping
        ):
            raise ValueError("s7-vintage-return-payload-invalid")
        prior_value = Decimal(str(prior_payload["return_value"]))
        later_value = Decimal(str(later_payload["return_value"]))
        identity = {
            **pair_parameters,
            "finding_type": "return-restatement",
            "dataset_id": later["dataset_id"],
            "source_record_id": later["source_record_id"],
            "effective_at": later["effective_at"],
            "first_known_at": later["available_at"],
            "affected_observation_ids": (
                prior["dataset_observation_id"],
                later["dataset_observation_id"],
            ),
            "prior_value": format(prior_value, "f"),
            "later_value": format(later_value, "f"),
            "reason_code": "return-restatement",
        }
        finding_id = digest_id("vintage-finding", identity)
        draft = RecordVintageFinding(
            finding_id,
            "return-restatement",
            str(later["dataset_id"]),
            str(later["source_record_id"]),
            _parse_time(later["effective_at"]),
            _parse_time(later["available_at"]),
            (
                str(prior["dataset_observation_id"]),
                str(later["dataset_observation_id"]),
            ),
            prior_value,
            later_value,
            "return-restatement",
            "pending",
        )
        output = f"/vintage_findings/{finding_id}"
        prepared.append(
            _prepare_record_finding(
                pair_parameters=pair_parameters,
                draft=draft,
                references=(
                *_row_references(conn, prior, prior_slice, output_field=output),
                *_row_references(conn, later, later_slice, output_field=output),
                ),
            )
        )
    return tuple(sorted(prepared, key=lambda item: item.finding.finding_id))


def _prepare_backfills(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    prepared = []
    pair_parameters = _pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name)
    for row, slice_ in _return_rows(pair):
        metadata = _row_metadata(conn, row)
        if (
            row["observation_status"] != "present"
            or row["predecessor_dataset_version_id"] is None
            or metadata["revision_of"] is not None
        ):
            continue
        affected = (str(row["dataset_observation_id"]),)
        identity = {
            **pair_parameters,
            "finding_type": "return-backfill",
            "dataset_id": row["dataset_id"],
            "source_record_id": row["source_record_id"],
            "effective_at": row["effective_at"],
            "first_known_at": row["available_at"],
            "affected_observation_ids": affected,
            "reason_code": "return-backfill",
        }
        finding_id = digest_id("vintage-finding", identity)
        draft = RecordVintageFinding(
            finding_id,
            "return-backfill",
            str(row["dataset_id"]),
            str(row["source_record_id"]),
            _parse_time(row["effective_at"]),
            _parse_time(row["available_at"]),
            affected,
            None,
            None,
            "return-backfill",
            "pending",
        )
        output = f"/vintage_findings/{finding_id}"
        prepared.append(
            _prepare_record_finding(
                pair_parameters=pair_parameters,
                draft=draft,
                references=_row_references(
                    conn, row, slice_, output_field=output
                ),
            )
        )
    return tuple(sorted(prepared, key=lambda item: item.finding.finding_id))


def _prepare_death_findings(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    audit_rows = tuple(
        (row, slice_) for slice_ in pair.audit.slices for row in slice_.rows
    )
    returns_by_observation = {
        str(row["dataset_observation_id"]): (row, slice_)
        for row, slice_ in audit_rows
        if isinstance(row.get("payload"), Mapping)
        and "return_value" in row["payload"]
    }
    pair_parameters = _pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name)
    prepared = []
    for evidence_row, evidence_slice in audit_rows:
        payload = evidence_row.get("payload")
        if not isinstance(payload, Mapping) or payload.get("finding_type") != "later-dead-product":
            continue
        affected_id = payload.get("affected_observation_ids")
        affected = returns_by_observation.get(str(affected_id))
        if affected is None:
            raise ValueError("s7-vintage-death-observation-missing")
        return_row, return_slice = affected
        if payload.get("reason_code") != "later-dead-product":
            raise ValueError("s7-vintage-death-reason-invalid")
        span = conn.execute(
            "SELECT evidence_span_id,evidence_item_id FROM evidence_span "
            "WHERE evidence_item_id=? AND json_pointer='/reason_code'",
            (evidence_row["evidence_item_id"],),
        ).fetchone()
        if span is None:
            raise ValueError("s7-vintage-death-span-missing")
        metadata = _row_metadata(conn, evidence_row)
        affected_ids = (str(affected_id),)
        identity = {
            **pair_parameters,
            "finding_type": "later-dead-product",
            "dataset_id": return_row["dataset_id"],
            "source_record_id": return_row["source_record_id"],
            "effective_at": payload["effective_at"],
            "first_known_at": payload["first_known_at"],
            "affected_observation_ids": affected_ids,
            "death_evidence_item_id": evidence_row["evidence_item_id"],
            "death_evidence_span_id": span["evidence_span_id"],
            "reason_code": payload["reason_code"],
        }
        finding_id = digest_id("vintage-finding", identity)
        draft = RecordVintageFinding(
            finding_id,
            "later-dead-product",
            str(return_row["dataset_id"]),
            str(return_row["source_record_id"]),
            _parse_time(payload["effective_at"]),
            _parse_time(payload["first_known_at"]),
            affected_ids,
            None,
            None,
            "later-dead-product",
            "pending",
        )
        output = f"/vintage_findings/{finding_id}"
        span_reference = ReceiptReference(
            output,
            "evidence-span",
            str(span["evidence_span_id"]),
            "included",
            "",
            str(metadata["payload_schema_id"]),
            "/reason_code",
            "input",
        )
        prepared.append(
            _prepare_record_finding(
                pair_parameters=pair_parameters,
                draft=draft,
                references=(
                    *_row_references(
                        conn, return_row, return_slice, output_field=output
                    ),
                    *_row_references(
                        conn, evidence_row, evidence_slice, output_field=output
                    ),
                    span_reference,
                ),
                death_span_closure=(
                    (
                        str(span["evidence_span_id"]),
                        str(evidence_row["evidence_item_id"]),
                        "later-dead-product",
                    ),
                ),
            )
        )
    return tuple(sorted(prepared, key=lambda item: item.finding.finding_id))


def _prepare_tombstones(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    rows = _return_rows(pair)
    present_by_item = {
        str(row["evidence_item_id"]): (row, slice_)
        for row, slice_ in rows
        if row["observation_status"] == "present"
    }
    pair_parameters = _pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name)
    prepared = []
    for removed, removed_slice in rows:
        if removed["observation_status"] != "explicitly-removed":
            continue
        present = present_by_item.get(str(removed["evidence_item_id"]))
        if present is None:
            raise ValueError("s7-vintage-tombstone-base-missing")
        prior, prior_slice = present
        metadata = _row_metadata(conn, removed)
        reason = metadata["disappearance_reason"]
        if not isinstance(reason, str) or not reason:
            raise ValueError("s7-vintage-tombstone-reason-missing")
        affected = (
            str(prior["dataset_observation_id"]),
            str(removed["dataset_observation_id"]),
        )
        identity = {
            **pair_parameters,
            "finding_type": "withdrawal-or-tombstone",
            "dataset_id": removed["dataset_id"],
            "source_record_id": removed["source_record_id"],
            "effective_at": removed["effective_at"],
            "first_known_at": removed["available_at"],
            "affected_observation_ids": affected,
            "reason_code": reason,
        }
        finding_id = digest_id("vintage-finding", identity)
        draft = RecordVintageFinding(
            finding_id,
            "withdrawal-or-tombstone",
            str(removed["dataset_id"]),
            str(removed["source_record_id"]),
            _parse_time(removed["effective_at"]),
            _parse_time(removed["available_at"]),
            affected,
            None,
            None,
            reason,
            "pending",
        )
        output = f"/vintage_findings/{finding_id}"
        prepared.append(
            _prepare_record_finding(
                pair_parameters=pair_parameters,
                draft=draft,
                references=(
                    *_row_references(
                        conn, prior, prior_slice, output_field=output
                    ),
                    *_row_references(
                        conn,
                        removed,
                        removed_slice,
                        output_field=output,
                        disposition="excluded",
                        reason_code=reason,
                    ),
                ),
            )
        )
    return tuple(sorted(prepared, key=lambda item: item.finding.finding_id))


def _prepare_retroactive_memberships(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    conn.execute("SAVEPOINT s7_vintage_x3_projection")
    try:
        return _prepare_retroactive_memberships_unpersisted(
            conn,
            pair,
            scenario=scenario,
            cutoff_name=cutoff_name,
        )
    finally:
        conn.execute("ROLLBACK TO s7_vintage_x3_projection")
        conn.execute("RELEASE s7_vintage_x3_projection")


def _prepare_retroactive_memberships_unpersisted(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_PreparedFinding, ...]:
    x3_manifest = build_x3_fixture(conn)
    cutoff = S7_CUTOFFS[cutoff_name]
    visible_memberships: dict[str, tuple[Mapping[str, object], object, Mapping[str, object]]] = {}
    visible_mappings: dict[str, Mapping[str, object]] = {}
    x3_slice_parameters = []
    for dataset_id in (
        "dataset:x3-registered-fund",
        "dataset:x3-strategy-export",
        "dataset:x3-rfi-ddq",
    ):
        snapshot = as_known_slice(
            conn,
            decision_at=cutoff,
            request=DatasetSliceRequest(
                dataset_id,
                x3_manifest.access_contexts[dataset_id],
                x3_manifest.right_ids[dataset_id],
                "x3-research",
                revision_mode="latest-known",
            ),
        )
        if snapshot.receipt_id is None:
            raise ValueError("s7-vintage-x3-slice-receipt-missing")
        mappings = {
            str(mapping["entity_mapping_id"]): mapping
            for mapping in project_entity_mappings(conn, snapshot)
        }
        visible_mappings.update(mappings)
        rows_by_item = {
            str(row["evidence_item_id"]): row for row in snapshot.rows
        }
        for membership in project_universe_memberships(conn, snapshot):
            source_row = rows_by_item.get(str(membership["source_evidence_item_id"]))
            if source_row is None:
                raise ValueError("s7-vintage-x3-membership-source-missing")
            visible_memberships[str(membership["universe_membership_id"])] = (
                membership,
                snapshot,
                source_row,
            )
        x3_slice_parameters.append(
            (dataset_id, snapshot.digest, snapshot.receipt_id)
        )

    pair_parameters = {
        **_pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name),
        "x3_membership_slices": tuple(sorted(x3_slice_parameters)),
    }
    prepared = []
    seen_links: set[str] = set()
    for return_row, return_slice in _return_rows(pair):
        if return_row["observation_status"] != "present":
            continue
        observation_id = str(return_row["dataset_observation_id"])
        links = conn.execute(
            "SELECT observation_membership_link_id,universe_membership_id "
            "FROM observation_membership_link WHERE dataset_observation_id=? "
            "ORDER BY observation_membership_link_id",
            (observation_id,),
        ).fetchall()
        for link in links:
            link_id = str(link["observation_membership_link_id"])
            membership_id = str(link["universe_membership_id"])
            visible = visible_memberships.get(membership_id)
            if visible is None or link_id in seen_links:
                continue
            membership, snapshot, source_row = visible
            mapping_id = str(membership["entity_mapping_id"])
            mapping = visible_mappings.get(mapping_id)
            if mapping is None:
                raise ValueError("s7-vintage-x3-mapping-missing")
            effective = _parse_time(membership["effective_from"])
            first_known = _parse_time(source_row["available_at"])
            if first_known <= _parse_time(return_row["available_at"]):
                continue
            source_record_id = str(source_row["source_record_id"])
            affected = (observation_id,)
            identity = {
                **pair_parameters,
                "finding_type": "retroactive-membership",
                "dataset_id": snapshot.request.dataset_id,
                "source_record_id": source_record_id,
                "effective_at": membership["effective_from"],
                "first_known_at": source_row["available_at"],
                "affected_observation_ids": affected,
                "mapping_ids": (mapping_id,),
                "membership_ids": (membership_id,),
                "observation_membership_link_ids": (link_id,),
                "reason_code": "retroactive-membership",
            }
            finding_id = digest_id("vintage-finding", identity)
            draft = RecordVintageFinding(
                finding_id,
                "retroactive-membership",
                snapshot.request.dataset_id,
                source_record_id,
                effective,
                first_known,
                affected,
                None,
                None,
                "retroactive-membership",
                "pending",
                (mapping_id,),
                (membership_id,),
                (link_id,),
            )
            output = f"/vintage_findings/{finding_id}"
            prepared.append(
                _prepare_record_finding(
                    pair_parameters=pair_parameters,
                    draft=draft,
                    references=_row_references(
                        conn,
                        return_row,
                        return_slice,
                        output_field=output,
                    ),
                    x3_closure=(
                        _X3Closure(
                            snapshot.request.dataset_id,
                            snapshot.digest,
                            snapshot.receipt_id,
                            mapping_id,
                            membership_id,
                            link_id,
                            observation_id,
                        ),
                    ),
                )
            )
            seen_links.add(link_id)
    return tuple(sorted(prepared, key=lambda item: item.finding.finding_id))


def _coverage_references(
    *,
    output_field: str,
    slice_: object,
    version_ids: tuple[str, ...],
    disposition: str,
    reason_code: str,
) -> tuple[ReceiptReference, ...]:
    common = {
        "output_field": output_field,
        "disposition": disposition,
        "reason_code": reason_code,
        "source_schema_id": "schema:generic-v1",
        "source_field": "/",
    }
    return (
        *(
            ReceiptReference(
                reference_type="dataset-version",
                reference_id=version_id,
                role="denominator",
                **common,
            )
            for version_id in version_ids
        ),
        ReceiptReference(
            reference_type="evidence-right",
            reference_id=slice_.request.evidence_right_id,
            role="filter",
            **common,
        ),
        ReceiptReference(
            reference_type="snapshot",
            reference_id=slice_.digest,
            role="input",
            **common,
        ),
    )


def _prepare_coverage(
    conn: sqlite3.Connection,
    pair: _BundlePair,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[tuple[_PreparedFinding, ...], tuple[_PreparedRefusal, ...]]:
    pair_parameters = _pair_parameters(pair, scenario=scenario, cutoff_name=cutoff_name)
    findings = []
    refusals = []
    for slice_ in pair.audit.slices:
        if not any(
            isinstance(row.get("payload"), Mapping)
            and "return_value" in row["payload"]
            for row in slice_.rows
        ):
            continue
        version_ids = tuple(
            sorted(
                {
                    str(row["dataset_version_id"])
                    for row in slice_.rows
                    if row["absence_semantics"] == "not-inferable"
                    and row["completeness_status"] == "complete"
                }
            )
        )
        if not version_ids:
            continue
        placeholders = ",".join("?" for _ in version_ids)
        version_rows = conn.execute(
            f"SELECT dataset_version_id,coalesce(published_at,first_observed_at_utc,received_at_utc) "
            f"AS first_known_at FROM dataset_version WHERE dataset_version_id IN ({placeholders}) "
            "ORDER BY dataset_version_id",
            version_ids,
        ).fetchall()
        if len(version_rows) != len(version_ids):
            raise ValueError("s7-vintage-coverage-version-missing")
        first_known = min(_parse_time(row["first_known_at"]) for row in version_rows)
        identity = {
            **pair_parameters,
            "finding_type": "absence-not-inferable",
            "dataset_id": slice_.request.dataset_id,
            "dataset_version_ids": version_ids,
            "first_known_at": first_known,
            "reason_code": "absence-not-inferable",
        }
        finding_id = digest_id("vintage-finding", identity)
        finding_draft = CoverageVintageFinding(
            finding_id,
            "absence-not-inferable",
            slice_.request.dataset_id,
            version_ids,
            first_known,
            "absence-not-inferable",
            "pending",
        )
        finding_output = f"/vintage_findings/{finding_id}"
        finding_receipt = _make_output_receipt(
            pair_parameters=pair_parameters,
            claim_id="s7_vintage_finding",
            output_locator=finding_output,
            value=_coverage_payload(finding_draft),
            references=_coverage_references(
                output_field=finding_output,
                slice_=slice_,
                version_ids=version_ids,
                disposition="included",
                reason_code="absence-not-inferable",
            ),
        )
        findings.append(
            _PreparedFinding(
                replace(finding_draft, receipt_id=finding_receipt.receipt_id),
                finding_receipt,
            )
        )

        availability = conn.execute(
            "SELECT availability_policy FROM dataset WHERE dataset_id=?",
            (slice_.request.dataset_id,),
        ).fetchone()
        if availability is None:
            raise ValueError("s7-vintage-coverage-dataset-missing")
        reason = (
            "dead-product-vintage-missing"
            if availability[0] == "public-publication"
            else "membership-absence-not-inferable"
        )
        refusal_identity = {
            **pair_parameters,
            "pointer": "/historical_selection",
            "dataset_id": slice_.request.dataset_id,
            "dataset_version_ids": version_ids,
            "reason_code": reason,
        }
        refusal_id = digest_id("vintage-refusal", refusal_identity)
        refusal_draft = HistoricalSelectionRefusal(
            refusal_id,
            "/historical_selection",
            slice_.request.dataset_id,
            reason,
            (reason,),
            "pending",
        )
        refusal_output = f"/historical_selection/refusals/{refusal_id}"
        refusal_receipt = _make_output_receipt(
            pair_parameters=pair_parameters,
            claim_id="s7_historical_selection_refusal",
            output_locator=refusal_output,
            value=_refusal_payload(refusal_draft),
            references=_coverage_references(
                output_field=refusal_output,
                slice_=slice_,
                version_ids=version_ids,
                disposition="refused",
                reason_code=reason,
            ),
        )
        refusals.append(
            _PreparedRefusal(
                replace(refusal_draft, receipt_id=refusal_receipt.receipt_id),
                refusal_receipt,
            )
        )
    return (
        tuple(sorted(findings, key=lambda item: item.finding.finding_id)),
        tuple(sorted(refusals, key=lambda item: item.refusal.refusal_id)),
    )


def _prepare_audit(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
) -> tuple[_BundlePair, tuple[_PreparedFinding, ...], tuple[_PreparedRefusal, ...]]:
    if not verify_s7_manifest(conn, manifest):
        raise ValueError("s7-substrate-conflict")
    pair = _materialize_pair(
        conn, manifest, scenario=scenario, cutoff_name=cutoff_name
    )
    coverage, prepared_refusals = _prepare_coverage(
        conn, pair, scenario=scenario, cutoff_name=cutoff_name
    )
    prepared = tuple(
        sorted(
            (
                *_prepare_restatements(
                    conn, pair, scenario=scenario, cutoff_name=cutoff_name
                ),
                *_prepare_backfills(
                    conn, pair, scenario=scenario, cutoff_name=cutoff_name
                ),
                *_prepare_death_findings(
                    conn, pair, scenario=scenario, cutoff_name=cutoff_name
                ),
                *_prepare_tombstones(
                    conn, pair, scenario=scenario, cutoff_name=cutoff_name
                ),
                *_prepare_retroactive_memberships(
                    conn, pair, scenario=scenario, cutoff_name=cutoff_name
                ),
                *coverage,
            ),
            key=lambda item: item.finding.finding_id,
        )
    )
    return pair, prepared, prepared_refusals


def _verify_prepared_finding(
    conn: sqlite3.Connection,
    *,
    item: _PreparedFinding,
    pair: _BundlePair,
    cutoff_name: str,
) -> None:
    verify_receipt(conn, item.receipt.receipt_id, pair.audit)
    for span_id, item_id, expected_text in item.death_span_closure:
        span = conn.execute(
            "SELECT evidence_item_id,json_pointer,start_char,end_char,span_sha256 "
            "FROM evidence_span WHERE evidence_span_id=?",
            (span_id,),
        ).fetchone()
        if (
            span is None
            or span["evidence_item_id"] != item_id
            or span["json_pointer"] != "/reason_code"
            or span["start_char"] != 0
            or span["end_char"] != len(expected_text)
            or span["span_sha256"] != sha256(expected_text.encode())
        ):
            raise ValueError("s7-vintage-receipt-closure-invalid")
    for closure in item.x3_closure:
        conn.execute("SAVEPOINT verify_s7_vintage_x3_projection")
        try:
            x3_manifest = build_x3_fixture(conn)
            snapshot_slice = as_known_slice(
                conn,
                decision_at=S7_CUTOFFS[cutoff_name],
                request=DatasetSliceRequest(
                    closure.dataset_id,
                    x3_manifest.access_contexts[closure.dataset_id],
                    x3_manifest.right_ids[closure.dataset_id],
                    "x3-research",
                    revision_mode="latest-known",
                ),
            )
            projected_mapping_ids = {
                str(row["entity_mapping_id"])
                for row in project_entity_mappings(conn, snapshot_slice)
            }
            projected_membership_ids = {
                str(row["universe_membership_id"])
                for row in project_universe_memberships(conn, snapshot_slice)
            }
            projection_valid = (
                snapshot_slice.digest == closure.snapshot_digest
                and snapshot_slice.receipt_id == closure.slice_receipt_id
                and closure.mapping_id in projected_mapping_ids
                and closure.membership_id in projected_membership_ids
            )
        finally:
            conn.execute("ROLLBACK TO verify_s7_vintage_x3_projection")
            conn.execute("RELEASE verify_s7_vintage_x3_projection")
        mapping = conn.execute(
            "SELECT dataset_observation_id,dataset_version_id,source_evidence_item_id "
            "FROM entity_mapping WHERE entity_mapping_id=?",
            (closure.mapping_id,),
        ).fetchone()
        membership = conn.execute(
            "SELECT dataset_observation_id,dataset_version_id,source_evidence_item_id,"
            "entity_mapping_id FROM universe_membership WHERE universe_membership_id=?",
            (closure.membership_id,),
        ).fetchone()
        link = conn.execute(
            "SELECT dataset_observation_id,universe_membership_id "
            "FROM observation_membership_link WHERE observation_membership_link_id=?",
            (closure.link_id,),
        ).fetchone()
        if (
            not projection_valid
            or mapping is None
            or membership is None
            or link is None
            or membership["entity_mapping_id"] != closure.mapping_id
            or link["dataset_observation_id"] != closure.affected_observation_id
            or link["universe_membership_id"] != closure.membership_id
            or mapping["dataset_observation_id"] != membership["dataset_observation_id"]
            or mapping["dataset_version_id"] != membership["dataset_version_id"]
            or mapping["source_evidence_item_id"]
            != membership["source_evidence_item_id"]
        ):
            raise ValueError("s7-vintage-receipt-closure-invalid")


def verify_s7_vintage_receipt(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
    receipt_id: str,
) -> None:
    """Rebuild the reviewed closure and verify one exact finding/refusal receipt."""
    pair, findings, refusals = _prepare_audit(
        conn, manifest, scenario=scenario, cutoff_name=cutoff_name
    )
    finding = next(
        (item for item in findings if item.receipt.receipt_id == receipt_id), None
    )
    if finding is not None:
        _verify_prepared_finding(
            conn, item=finding, pair=pair, cutoff_name=cutoff_name
        )
        return
    refusal = next(
        (item for item in refusals if item.receipt.receipt_id == receipt_id), None
    )
    if refusal is None:
        raise ValueError("s7-vintage-receipt-closure-invalid")
    verify_receipt(conn, refusal.receipt.receipt_id, pair.audit)


def audit_s7_vintages(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
) -> VintageAuditResult:
    """Audit one reviewed S7 scenario without accepting caller-authored time state."""
    pair, prepared, prepared_refusals = _prepare_audit(
        conn, manifest, scenario=scenario, cutoff_name=cutoff_name
    )
    for item in prepared:
        store_receipt(conn, item.receipt)
        _verify_prepared_finding(
            conn, item=item, pair=pair, cutoff_name=cutoff_name
        )
    for item in prepared_refusals:
        store_receipt(conn, item.receipt)
        verify_receipt(conn, item.receipt.receipt_id, pair.audit)
    findings = tuple(item.finding for item in prepared)
    refusals = tuple(item.refusal for item in prepared_refusals)
    receipt_ids = tuple(
        sorted(
            (
                *(item.receipt.receipt_id for item in prepared),
                *(item.receipt.receipt_id for item in prepared_refusals),
            )
        )
    )
    return VintageAuditResult(
        scenario,
        cutoff_name,
        pair.analytic.bundle_digest,
        pair.audit.bundle_digest,
        pair.analytic.join_receipt_id,
        pair.audit.join_receipt_id,
        findings,
        refusals,
        receipt_ids,
    )
