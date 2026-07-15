"""Pointer-exact X3 claim receipts over ruled verification envelopes."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from quant_allocator.evidence.lineage import make_receipt, store_receipt, verify_receipt
from quant_allocator.evidence.model import (
    ReceiptReference,
    SnapshotBundle,
    SnapshotBundleRequest,
    SnapshotSlice,
    canonical_bytes,
    digest_id,
    normalize_utc,
    sha256,
)


@dataclass(frozen=True, slots=True)
class X3ClaimReceiptContract:
    claim_id: str
    output_pointer: str
    state_key: str
    access_contexts: tuple[str, ...]
    live_attestation_ceiling: str
    value: Any
    refusal_code: str
    evaluation_receipt_ids: tuple[str, ...] = ()


def _verify_slice_closure(conn: sqlite3.Connection, bundle: SnapshotBundle) -> None:
    if bundle.request.sources != tuple(row.request for row in bundle.slices):
        raise ValueError("x3-verification-envelope-request-mismatch")
    for snapshot_slice in bundle.slices:
        request_payload = {
            "request": snapshot_slice.request,
            "decision_at": normalize_utc(bundle.request.decision_at),
        }
        manifest = conn.execute(
            "SELECT * FROM snapshot_manifest WHERE snapshot_digest=?",
            (snapshot_slice.digest,),
        ).fetchone()
        receipt = conn.execute(
            "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
            (snapshot_slice.receipt_id,),
        ).fetchone()
        row_bytes = b"".join(canonical_bytes(row) + b"\n" for row in snapshot_slice.rows)
        right_ids = {
            row[0]
            for row in conn.execute(
                "SELECT evidence_right_id FROM receipt_reference "
                "WHERE receipt_id=? AND reference_type='evidence-right'",
                (snapshot_slice.receipt_id,),
            )
        }
        if (
            manifest is None
            or receipt is None
            or not snapshot_slice.receipt_id
            or snapshot_slice.decision_at != normalize_utc(bundle.request.decision_at)
            or manifest["request_json"] != canonical_bytes(request_payload).decode()
            or manifest["row_count"] != len(snapshot_slice.rows)
            or manifest["records_sha256"] != sha256(row_bytes)
            or receipt["claim_id"] != "claim:snapshot-slice"
            or receipt["input_digest"] != snapshot_slice.digest
            or receipt["parameters_sha256"] != sha256(canonical_bytes(request_payload))
            or receipt["value_sha256"] != sha256(canonical_bytes(snapshot_slice.rows))
            or right_ids != {snapshot_slice.request.evidence_right_id}
        ):
            raise ValueError("x3-snapshot-slice-closure-mismatch")
        single_slice_bundle = SnapshotBundle(
            SnapshotBundleRequest(
                bundle.request.decision_at,
                (snapshot_slice.request,),
                ("evidence_item_id",),
                "x3-snapshot-slice-verification-v1",
            ),
            (snapshot_slice,),
            snapshot_slice.digest,
            snapshot_slice.receipt_id,
            snapshot_slice.digest,
        )
        verify_receipt(conn, snapshot_slice.receipt_id, single_slice_bundle)


def _evaluation_receipt_ids(value: Any) -> tuple[str, ...]:
    rows = value.get("stage_counts", ()) if isinstance(value, dict) else value
    if not isinstance(rows, (list, tuple)):
        return ()
    return tuple(
        sorted(
            {
                str(receipt_id)
                for row in rows
                if isinstance(row, dict)
                for receipt_id in row.get("evaluation_receipt_ids", ())
            }
        )
    )


def _evaluation_rows(value: Any) -> tuple[Any, ...]:
    rows = value.get("stage_counts", ()) if isinstance(value, dict) else value
    return tuple(rows) if isinstance(rows, (list, tuple)) else ()


def _verify_evaluation_receipts(
    conn: sqlite3.Connection,
    *,
    bundle: SnapshotBundle,
    contract: X3ClaimReceiptContract,
) -> None:
    if contract.claim_id not in {"funnel_stage_counts", "funnel_conversion"}:
        if contract.evaluation_receipt_ids:
            raise ValueError("x3-evaluation-receipt-surplus")
        return
    expected = _evaluation_receipt_ids(contract.value)
    supplied = contract.evaluation_receipt_ids
    state_parts = contract.state_key.split("|")
    if len(state_parts) != 3:
        raise ValueError("x3-evaluation-receipt-state-key-invalid")
    applicable = (
        state_parts[0] == "latest" and state_parts[1] == "full-synthetic-funnel"
    )
    if (applicable and len(expected) != 168) or (
        not applicable and (expected or supplied)
    ):
        raise ValueError("x3-evaluation-receipt-applicability-mismatch")
    if len(supplied) != len(set(supplied)) or tuple(sorted(supplied)) != expected:
        raise ValueError("x3-evaluation-receipt-set-mismatch")
    if _evaluation_rows(contract.value) and not expected:
        raise ValueError("x3-evaluation-receipt-set-empty")
    for receipt_id in expected:
        row = conn.execute(
            "SELECT claim_id FROM reconstruction_receipt WHERE receipt_id=?",
            (receipt_id,),
        ).fetchone()
        if row is None or row["claim_id"] != "claim:funnel-cohort-evaluation":
            raise ValueError("x3-evaluation-receipt-invalid")
        verify_receipt(conn, receipt_id, bundle)


def _verify_contract_closure(
    conn: sqlite3.Connection,
    *,
    bundle: SnapshotBundle,
    contract: X3ClaimReceiptContract,
) -> None:
    _verify_slice_closure(conn, bundle)
    allowed_contexts = set(contract.access_contexts)
    if not allowed_contexts or any(
        snapshot_slice.request.access_context not in allowed_contexts
        for snapshot_slice in bundle.slices
    ):
        raise ValueError("x3-claim-access-context-mismatch")
    _verify_evaluation_receipts(conn, bundle=bundle, contract=contract)


def build_verification_envelope(
    conn: sqlite3.Connection,
    *,
    state_key: str,
    decision_at,
    slices: tuple[SnapshotSlice, ...],
) -> SnapshotBundle:
    ordered = tuple(sorted(slices, key=lambda row: row.request.dataset_id))
    slice_identity = tuple((row.request.dataset_id, row.digest, row.receipt_id) for row in ordered)
    composite_digest = sha256(canonical_bytes(slice_identity))
    references = tuple(
        ReceiptReference(
            "/slices",
            "snapshot",
            row.digest,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "join",
        )
        for row in ordered
    )
    receipt = make_receipt(
        claim_id="claim:x3-verification-envelope",
        output_locator=f"/states/{state_key}/verification-envelope",
        input_digest=composite_digest,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="D",
        algorithm_id="x3-claim-verification-envelope",
        algorithm_version="1",
        parameters={"state_key": state_key, "slice_identity": slice_identity},
        value=slice_identity,
        references=references,
    )
    store_receipt(conn, receipt)
    bundle_digest = digest_id(
        "bundle",
        {
            "policy": "x3-claim-verification-envelope-v1",
            "state_key": state_key,
            "slice_identity": slice_identity,
            "composite_digest": composite_digest,
            "join_receipt_id": receipt.receipt_id,
        },
    )
    bundle = SnapshotBundle(
        SnapshotBundleRequest(
            decision_at,
            tuple(row.request for row in ordered),
            ("evidence_item_id",),
            "x3-claim-verification-envelope-v1",
        ),
        ordered,
        composite_digest,
        receipt.receipt_id,
        bundle_digest,
    )
    _verify_slice_closure(conn, bundle)
    verify_receipt(conn, receipt.receipt_id, bundle)
    return bundle


def _parameters(bundle: SnapshotBundle, contract: X3ClaimReceiptContract) -> dict[str, Any]:
    return {
        "state_key": contract.state_key,
        "access_contexts": contract.access_contexts,
        "verification_envelope_composite_input_digest": bundle.composite_input_digest,
        "verification_envelope_join_receipt_id": bundle.join_receipt_id,
        "verification_envelope_bundle_digest": bundle.bundle_digest,
        "slice_receipt_ids": tuple(row.receipt_id for row in bundle.slices),
        "evaluation_receipt_ids": contract.evaluation_receipt_ids,
        "refusal_code": contract.refusal_code,
    }


def _receipt(bundle: SnapshotBundle, contract: X3ClaimReceiptContract):
    parameters = _parameters(bundle, contract)
    available_references = tuple(
        ReceiptReference(
            contract.output_pointer,
            "snapshot",
            row.digest,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "input",
        )
        for row in bundle.slices
    )
    refusal_references = (
        tuple(
            ReceiptReference(
                contract.output_pointer,
                "snapshot",
                row.digest,
                "refused",
                contract.refusal_code,
                "schema:generic-v1",
                "/",
                "refusal",
            )
            for row in bundle.slices
        )
        if contract.refusal_code
        else ()
    )
    return make_receipt(
        claim_id=contract.claim_id,
        output_locator=contract.output_pointer,
        input_digest=sha256(canonical_bytes(parameters)),
        output_schema_id="schema:x3-claim-v1",
        current_attestation="D",
        live_attestation_ceiling=contract.live_attestation_ceiling,
        algorithm_id="x3-source-conditioned-claim",
        algorithm_version="1",
        parameters=parameters,
        value=contract.value,
        references=available_references + refusal_references,
    )


def persist_x3_claim_receipt(
    conn: sqlite3.Connection,
    *,
    bundle: SnapshotBundle,
    contract: X3ClaimReceiptContract,
) -> str:
    receipt = _receipt(bundle, contract)
    store_receipt(conn, receipt)
    verify_x3_claim_receipt(conn, receipt_id=receipt.receipt_id, bundle=bundle, contract=contract)
    return receipt.receipt_id


def verify_x3_claim_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    bundle: SnapshotBundle,
    contract: X3ClaimReceiptContract,
) -> None:
    _verify_contract_closure(conn, bundle=bundle, contract=contract)
    if _receipt(bundle, contract).receipt_id != receipt_id:
        raise ValueError("x3-claim-receipt-contract-mismatch")
    verify_receipt(conn, receipt_id, bundle)
