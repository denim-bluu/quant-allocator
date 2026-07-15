"""Receipt closure checks for S7's unconditional estimator-refusal claim."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping

from quant_allocator.evidence.checks import refuse
from quant_allocator.evidence.fixtures.s7 import S7MethodPolicyEvidence
from quant_allocator.evidence.lineage import (
    make_receipt,
    store_receipt,
    verify_receipt,
)
from quant_allocator.evidence.model import (
    ReceiptReference,
    ReconstructionReceipt,
    SnapshotBundle,
    canonical_bytes,
    sha256,
)


_POLICY_DATASET_ID = "dataset:s7-method-boundary"
_POLICY_ID = "s7-method-boundary/v1"
_OUTPUT_POINTER = "/refusals/performance-estimator"
_OUTPUT_SCHEMA_ID = "s7-provenance-output/v1"
_ALGORITHM_ID = "s7-method-boundary/v1"
_ALGORITHM_VERSION = "1"
_POLICY_STATEMENT = (
    "S7 reconstructs lineage and basis-qualified panels; it does not estimate alpha, "
    "Sharpe, IRR, PME, skill, or manager ranking."
)
_REFERENCE_COLUMNS = {
    "evidence-item": "evidence_item_id",
    "evidence-span": "evidence_span_id",
    "dataset-observation": "dataset_observation_id",
    "dataset-version": "dataset_version_id",
    "evidence-right": "evidence_right_id",
    "snapshot": "snapshot_digest",
}


def _refuse_if(condition: bool) -> None:
    if condition:
        refuse("s7-policy-refusal-closure-invalid")


def _expected_parameters(
    policy: S7MethodPolicyEvidence, policy_bundle: SnapshotBundle
) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "policy_item_id": policy.item_id,
        "policy_span_id": policy.span_id,
        "policy_observation_id": policy.observation_id,
        "policy_version_id": policy.version_id,
        "policy_right_id": policy.right_id,
        "policy_snapshot_digest": policy.snapshot_digest,
        "policy_bundle_digest": policy_bundle.bundle_digest,
        "policy_join_receipt_id": policy_bundle.join_receipt_id,
        "policy_payload_schema_id": policy.payload_schema_id,
        "policy_payload_schema_sha256": policy.payload_schema_sha256,
        "policy_payload_sha256": policy.payload_sha256,
    }


def _expected_input_digest(parameters: Mapping[str, object]) -> str:
    return sha256(canonical_bytes({"policy-refusal-input": dict(parameters)}))


def _require_bundle_closure(
    conn: sqlite3.Connection,
    *,
    policy_bundle: SnapshotBundle,
    policy: S7MethodPolicyEvidence,
) -> None:
    _refuse_if(
        policy.policy_id != _POLICY_ID
        or policy.dataset_id != _POLICY_DATASET_ID
        or policy_bundle.bundle_digest != policy.bundle_digest
        or policy_bundle.join_receipt_id != policy.join_receipt_id
        or len(policy_bundle.request.sources) != 1
        or len(policy_bundle.slices) != 1
    )
    source = policy_bundle.request.sources[0]
    slice_ = policy_bundle.slices[0]
    _refuse_if(
        source.dataset_id != policy.dataset_id
        or source.evidence_right_id != policy.right_id
        or source.licence_purpose != "s7-research"
        or source.access_context != "public"
        or slice_.request != source
        or slice_.digest != policy.snapshot_digest
        or slice_.receipt_id != policy.slice_receipt_id
    )
    manifest = conn.execute(
        "SELECT request_json,slice_digests_json,composite_input_digest,join_receipt_id "
        "FROM snapshot_bundle_manifest WHERE bundle_digest=?",
        (policy_bundle.bundle_digest,),
    ).fetchone()
    snapshot = conn.execute(
        "SELECT request_json FROM snapshot_manifest WHERE snapshot_digest=?",
        (slice_.digest,),
    ).fetchone()
    slice_pairs = tuple(
        (bundle_slice.request.dataset_id, bundle_slice.digest)
        for bundle_slice in policy_bundle.slices
    )
    _refuse_if(
        manifest is None
        or manifest["join_receipt_id"] != policy_bundle.join_receipt_id
        or manifest["request_json"] != canonical_bytes(policy_bundle.request).decode()
        or manifest["slice_digests_json"] != canonical_bytes(slice_pairs).decode()
        or manifest["composite_input_digest"] != policy_bundle.composite_input_digest
        or snapshot is None
        or snapshot["request_json"]
        != canonical_bytes({"request": slice_.request, "decision_at": slice_.decision_at}).decode()
    )


def _require_immutable_policy_closure(
    conn: sqlite3.Connection, policy: S7MethodPolicyEvidence
) -> None:
    version = conn.execute(
        "SELECT dataset_id,acquisition_right_id,delivery_mode FROM dataset_version "
        "WHERE dataset_version_id=?",
        (policy.version_id,),
    ).fetchone()
    right = conn.execute(
        "SELECT dataset_id,access_context,licence_purpose FROM evidence_right "
        "WHERE evidence_right_id=?",
        (policy.right_id,),
    ).fetchone()
    item = conn.execute(
        "SELECT sr.dataset_id,i.acquisition_right_id,i.access_context,i.licence_purpose,"
        "i.payload_schema_id,i.content_sha256,i.payload_json "
        "FROM evidence_item i JOIN source_record sr USING(source_record_id) "
        "WHERE i.evidence_item_id=?",
        (policy.item_id,),
    ).fetchone()
    span = conn.execute(
        "SELECT evidence_item_id,json_pointer,start_char,end_char,span_sha256 "
        "FROM evidence_span WHERE evidence_span_id=?",
        (policy.span_id,),
    ).fetchone()
    observation = conn.execute(
        "SELECT evidence_item_id,dataset_version_id FROM dataset_observation "
        "WHERE dataset_observation_id=?",
        (policy.observation_id,),
    ).fetchone()
    _refuse_if(
        version is None
        or right is None
        or item is None
        or span is None
        or observation is None
        or version["dataset_id"] != policy.dataset_id
        or version["acquisition_right_id"] != policy.right_id
        or version["delivery_mode"] != "full-snapshot"
        or right["dataset_id"] != policy.dataset_id
        or right["access_context"] != "public"
        or right["licence_purpose"] != "s7-research"
        or item["dataset_id"] != policy.dataset_id
        or item["acquisition_right_id"] != policy.right_id
        or item["access_context"] != "public"
        or item["licence_purpose"] != "s7-research"
        or item["payload_schema_id"] != policy.payload_schema_id
        or item["content_sha256"] != policy.payload_sha256
        or span["evidence_item_id"] != policy.item_id
        or span["json_pointer"] != "/statement"
        or observation["evidence_item_id"] != policy.item_id
        or observation["dataset_version_id"] != policy.version_id
    )
    schema = conn.execute(
        "SELECT schema_sha256 FROM payload_schema WHERE payload_schema_id=?",
        (policy.payload_schema_id,),
    ).fetchone()
    try:
        payload = json.loads(item["payload_json"])
    except (TypeError, json.JSONDecodeError):
        refuse("s7-policy-refusal-closure-invalid")
    statement = payload.get("statement") if isinstance(payload, dict) else None
    expected_payload = {
        "policy_id": policy.policy_id,
        "output_pointer": _OUTPUT_POINTER,
        "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
        "statement": _POLICY_STATEMENT,
    }
    _refuse_if(
        schema is None
        or schema["schema_sha256"] != policy.payload_schema_sha256
        or item["content_sha256"] != sha256(canonical_bytes(payload))
        or payload != expected_payload
        or span["start_char"] != 0
        or span["end_char"] != len(_POLICY_STATEMENT)
        or span["span_sha256"] != sha256(_POLICY_STATEMENT.encode())
        or statement != _POLICY_STATEMENT
        or statement[span["start_char"] : span["end_char"]] != _POLICY_STATEMENT
    )


def _require_receipt_header_and_references(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    policy_bundle: SnapshotBundle,
    policy: S7MethodPolicyEvidence,
) -> None:
    header = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
    ).fetchone()
    _refuse_if(
        header is None
        or header["claim_id"] != "performance_estimator_refusal"
        or header["output_locator"] != _OUTPUT_POINTER
        or header["output_schema_id"] != _OUTPUT_SCHEMA_ID
        or header["current_attestation"] != "D"
        or header["live_attestation_ceiling"] != "D"
        or header["algorithm_id"] != _ALGORITHM_ID
        or header["algorithm_version"] != _ALGORITHM_VERSION
    )
    expected_parameters = _expected_parameters(policy, policy_bundle)
    _refuse_if(
        header["parameters_sha256"] != sha256(canonical_bytes(expected_parameters))
        or header["input_digest"] != _expected_input_digest(expected_parameters)
    )
    rows = conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal", (receipt_id,)
    ).fetchall()
    expected = {
        ("evidence-item", policy.item_id, "included", "input", "/"),
        ("evidence-span", policy.span_id, "included", "input", "/statement"),
        ("dataset-observation", policy.observation_id, "included", "input", "/"),
        ("dataset-version", policy.version_id, "included", "input", "/"),
        ("evidence-right", policy.right_id, "included", "filter", "/"),
        ("snapshot", policy.snapshot_digest, "included", "input", "/"),
    }
    actual: set[tuple[str, str, str, str, str]] = set()
    for row in rows:
        reference_type = row["reference_type"]
        column = _REFERENCE_COLUMNS.get(reference_type)
        _refuse_if(
            column is None
            or row["output_field"] != _OUTPUT_POINTER
            or row["reason_code"] != ""
            or row["source_schema_id"] != policy.payload_schema_id
            or column is None
            or row[column] is None
        )
        actual.add(
            (
                reference_type,
                row[column],
                row["disposition"],
                row["role"],
                row["source_field"],
            )
        )
    _refuse_if(len(rows) != 6 or actual != expected)


def verify_s7_policy_refusal_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    policy_bundle: SnapshotBundle,
    policy: S7MethodPolicyEvidence,
) -> None:
    """Check S7 policy closure, then delegate to the shared receipt verifier."""
    _require_bundle_closure(conn, policy_bundle=policy_bundle, policy=policy)
    _require_immutable_policy_closure(conn, policy)
    _require_receipt_header_and_references(
        conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
    )
    verify_receipt(conn, receipt_id, policy_bundle)


def emit_s7_policy_refusal_receipt(
    conn: sqlite3.Connection,
    *,
    policy_bundle: SnapshotBundle,
    policy: S7MethodPolicyEvidence,
) -> ReconstructionReceipt:
    """Persist and verify the unconditional S7 estimator-boundary refusal."""
    parameters = _expected_parameters(policy, policy_bundle)
    references = (
        ReceiptReference(
            _OUTPUT_POINTER,
            "evidence-item",
            policy.item_id,
            "included",
            "",
            policy.payload_schema_id,
            "/",
            "input",
        ),
        ReceiptReference(
            _OUTPUT_POINTER,
            "evidence-span",
            policy.span_id,
            "included",
            "",
            policy.payload_schema_id,
            "/statement",
            "input",
        ),
        ReceiptReference(
            _OUTPUT_POINTER,
            "dataset-observation",
            policy.observation_id,
            "included",
            "",
            policy.payload_schema_id,
            "/",
            "input",
        ),
        ReceiptReference(
            _OUTPUT_POINTER,
            "dataset-version",
            policy.version_id,
            "included",
            "",
            policy.payload_schema_id,
            "/",
            "input",
        ),
        ReceiptReference(
            _OUTPUT_POINTER,
            "evidence-right",
            policy.right_id,
            "included",
            "",
            policy.payload_schema_id,
            "/",
            "filter",
        ),
        ReceiptReference(
            _OUTPUT_POINTER,
            "snapshot",
            policy.snapshot_digest,
            "included",
            "",
            policy.payload_schema_id,
            "/",
            "input",
        ),
    )
    receipt = make_receipt(
        claim_id="performance_estimator_refusal",
        output_locator=_OUTPUT_POINTER,
        input_digest=_expected_input_digest(parameters),
        output_schema_id=_OUTPUT_SCHEMA_ID,
        current_attestation="D",
        live_attestation_ceiling="D",
        algorithm_id=_ALGORITHM_ID,
        algorithm_version=_ALGORITHM_VERSION,
        parameters=parameters,
        value={"policy_id": policy.policy_id, "output_pointer": _OUTPUT_POINTER},
        references=references,
    )
    store_receipt(conn, receipt)
    verify_s7_policy_refusal_receipt(
        conn,
        receipt_id=receipt.receipt_id,
        policy_bundle=policy_bundle,
        policy=policy,
    )
    return receipt
