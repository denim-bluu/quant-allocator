from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Mapping

from .checks import refuse
from .model import (
    ReceiptReference,
    ReconstructionReceipt,
    SnapshotBundle,
    canonical_bytes,
    digest_id,
    sha256,
)


def make_receipt(
    *,
    claim_id: str,
    output_locator: str,
    input_digest: str,
    output_schema_id: str,
    current_attestation: str,
    live_attestation_ceiling: str,
    algorithm_id: str,
    algorithm_version: str,
    parameters: Mapping[str, Any],
    value: Any,
    references: Iterable[ReceiptReference],
) -> ReconstructionReceipt:
    order = {"A": 4, "B": 3, "C": 2, "D": 1}
    if order[current_attestation] > order[live_attestation_ceiling]:
        refuse("attestation-exceeds-ceiling")
    refs = tuple(
        sorted(
            set(references),
            key=lambda r: (
                r.output_field,
                r.role,
                r.disposition,
                r.reference_type,
                r.reference_id,
                r.source_schema_id,
                r.source_field,
                r.reason_code,
            ),
        )
    )
    header = {
        "claim_id": claim_id,
        "output_locator": output_locator,
        "input_digest": input_digest,
        "output_schema_id": output_schema_id,
        "current_attestation": current_attestation,
        "live_attestation_ceiling": live_attestation_ceiling,
        "algorithm_id": algorithm_id,
        "algorithm_version": algorithm_version,
        "parameters_sha256": sha256(canonical_bytes(parameters)),
        "value_sha256": sha256(canonical_bytes(value)),
        "references": refs,
    }
    return ReconstructionReceipt(
        digest_id("receipt", header),
        claim_id,
        output_locator,
        input_digest,
        output_schema_id,
        current_attestation,
        live_attestation_ceiling,
        algorithm_id,
        algorithm_version,
        header["parameters_sha256"],
        header["value_sha256"],
        refs,
    )


def store_receipt(conn: sqlite3.Connection, receipt: ReconstructionReceipt) -> str:
    existing = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt.receipt_id,)
    ).fetchone()
    if existing is not None:
        if (
            conn.execute(
                "SELECT 1 FROM receipt_seal WHERE receipt_id=?", (receipt.receipt_id,)
            ).fetchone()
            is None
        ):
            refuse("receipt-incomplete")
        return receipt.receipt_id
    conn.execute("SAVEPOINT store_evidence_receipt")
    try:
        _store_new_receipt(conn, receipt)
    except Exception:
        conn.execute("ROLLBACK TO store_evidence_receipt")
        conn.execute("RELEASE store_evidence_receipt")
        raise
    conn.execute("RELEASE store_evidence_receipt")
    return receipt.receipt_id


def _store_new_receipt(conn: sqlite3.Connection, receipt: ReconstructionReceipt) -> None:
    conn.execute(
        "INSERT INTO reconstruction_receipt VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            receipt.receipt_id,
            receipt.claim_id,
            receipt.output_locator,
            receipt.input_digest,
            receipt.output_schema_id,
            receipt.current_attestation,
            receipt.live_attestation_ceiling,
            receipt.algorithm_id,
            receipt.algorithm_version,
            receipt.parameters_sha256,
            receipt.value_sha256,
        ),
    )
    for ordinal, ref in enumerate(receipt.references):
        typed_column = _REFERENCE_COLUMNS.get(ref.reference_type)
        if typed_column is None:
            refuse("receipt-reference-invalid", reference_type=ref.reference_type)
        columns = (
            "receipt_id",
            "ordinal",
            "output_field",
            "reference_type",
            "disposition",
            "reason_code",
            "source_schema_id",
            "source_field",
            "role",
            typed_column,
        )
        conn.execute(
            f"INSERT INTO receipt_reference({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            (
                receipt.receipt_id,
                ordinal,
                ref.output_field,
                ref.reference_type,
                ref.disposition,
                ref.reason_code,
                ref.source_schema_id,
                ref.source_field,
                ref.role,
                ref.reference_id,
            ),
        )
    conn.execute(
        "INSERT INTO receipt_seal VALUES (?,?,?)",
        (
            receipt.receipt_id,
            len(receipt.references),
            sha256(canonical_bytes(receipt.references)),
        ),
    )


def resolve_span(conn: sqlite3.Connection, evidence_span_id: str) -> Mapping[str, Any]:
    row = conn.execute(
        "SELECT s.*,i.payload_json FROM evidence_span s JOIN evidence_item i USING(evidence_item_id) WHERE evidence_span_id=?",
        (evidence_span_id,),
    ).fetchone()
    if row is None:
        refuse("invalid-json-pointer")
    payload = json.loads(row["payload_json"])
    value: Any = payload
    for token in row["json_pointer"].lstrip("/").split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, str):
        refuse("payload-schema-mismatch")
    text = value[row["start_char"] : row["end_char"]]
    if sha256(text.encode()) != row["span_sha256"]:
        refuse("content-hash-mismatch")
    return {
        "text": text,
        "evidence_item_id": row["evidence_item_id"],
        "json_pointer": row["json_pointer"],
    }


def verify_receipt(conn: sqlite3.Connection, receipt_id: str, bundle: SnapshotBundle) -> None:
    receipt = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
    ).fetchone()
    if receipt is None:
        refuse("receipt-incomplete")
    refs = conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal", (receipt_id,)
    ).fetchall()
    if not refs:
        refuse("receipt-incomplete")
    persisted_refs = tuple(
        ReceiptReference(
            row["output_field"],
            row["reference_type"],
            row[_REFERENCE_COLUMNS[row["reference_type"]]],
            row["disposition"],
            row["reason_code"],
            row["source_schema_id"],
            row["source_field"],
            row["role"],
        )
        for row in refs
    )
    seal = conn.execute("SELECT * FROM receipt_seal WHERE receipt_id=?", (receipt_id,)).fetchone()
    if (
        seal is None
        or seal["reference_count"] != len(persisted_refs)
        or seal["references_sha256"] != sha256(canonical_bytes(persisted_refs))
    ):
        refuse("receipt-incomplete")
    expected_id = digest_id(
        "receipt",
        {
            "claim_id": receipt["claim_id"],
            "output_locator": receipt["output_locator"],
            "input_digest": receipt["input_digest"],
            "output_schema_id": receipt["output_schema_id"],
            "current_attestation": receipt["current_attestation"],
            "live_attestation_ceiling": receipt["live_attestation_ceiling"],
            "algorithm_id": receipt["algorithm_id"],
            "algorithm_version": receipt["algorithm_version"],
            "parameters_sha256": receipt["parameters_sha256"],
            "value_sha256": receipt["value_sha256"],
            "references": persisted_refs,
        },
    )
    if expected_id != receipt_id:
        refuse("receipt-incomplete")
    allowed_items = {row.get("evidence_item_id") for slice_ in bundle.slices for row in slice_.rows}
    allowed_snapshots = {slice_.digest for slice_ in bundle.slices}
    allowed_datasets = {slice_.request.dataset_id for slice_ in bundle.slices}
    version_ids = {ref["dataset_version_id"] for ref in refs if ref["dataset_version_id"]}
    if version_ids:
        placeholders = ",".join("?" for _ in version_ids)
        denominator_items = {
            row[0]
            for row in conn.execute(
                f"SELECT evidence_item_id FROM dataset_observation WHERE dataset_version_id IN ({placeholders})",
                tuple(sorted(version_ids)),
            )
        }
        denominator_sources = {
            row[0]
            for row in conn.execute(
                f"""SELECT DISTINCT i.source_record_id FROM dataset_observation o
                    JOIN evidence_item i USING(evidence_item_id)
                    WHERE o.dataset_version_id IN ({placeholders})""",
                tuple(sorted(version_ids)),
            )
        }
    else:
        denominator_items = set()
        denominator_sources = set()
    for ref in refs:
        if not ref["output_field"].startswith("/") or not ref["source_field"].startswith("/"):
            refuse("receipt-reference-invalid")
        if ref["source_field"] != "/":
            schema_row = conn.execute(
                "SELECT schema_json FROM payload_schema WHERE payload_schema_id=?",
                (ref["source_schema_id"],),
            ).fetchone()
            if schema_row is None:
                refuse("unknown-payload-schema")
            schema = json.loads(schema_row[0])
            tokens = [
                token.replace("~1", "/").replace("~0", "~")
                for token in ref["source_field"].lstrip("/").split("/")
            ]
            current = schema
            for index, token in enumerate(tokens):
                properties = current.get("properties", {})
                if token in properties:
                    current = properties[token]
                elif index == 0 and token in current.get("required", ()) and len(tokens) == 1:
                    current = {}
                else:
                    refuse("invalid-json-pointer")
        if ref["reference_type"] == "evidence-item":
            identifier = ref["evidence_item_id"]
            allowed = (
                allowed_items | denominator_items
                if ref["disposition"] == "included"
                else denominator_items
            )
            if identifier not in allowed:
                refuse("receipt-incomplete")
        elif ref["reference_type"] == "source-record":
            if ref["source_record_id"] not in denominator_sources:
                refuse("receipt-incomplete")
        elif ref["reference_type"] == "dataset-version":
            dataset = conn.execute(
                "SELECT dataset_id FROM dataset_version WHERE dataset_version_id=?",
                (ref["dataset_version_id"],),
            ).fetchone()
            if dataset is None or dataset[0] not in allowed_datasets:
                refuse("receipt-incomplete")
        elif (
            ref["reference_type"] == "snapshot" and ref["snapshot_digest"] not in allowed_snapshots
        ):
            refuse("receipt-incomplete")
    if receipt["claim_id"] == "claim:snapshot-slice":
        if receipt["output_locator"] != "/rows" or any(
            ref["output_field"] != "/rows" for ref in refs
        ):
            refuse("invalid-json-pointer")
        required = {"evidence-right", "dataset-version", "dataset-delivery-partition"}
        if not required.issubset({ref["reference_type"] for ref in refs}):
            refuse("receipt-incomplete")
        if version_ids:
            placeholders = ",".join("?" for _ in version_ids)
            expected_rows = conn.execute(
                f"""SELECT o.dataset_observation_id,o.evidence_item_id,i.source_record_id,
                            l.dataset_observation_partition_link_id
                     FROM dataset_observation o JOIN evidence_item i USING(evidence_item_id)
                     JOIN dataset_observation_partition_link l USING(dataset_observation_id)
                     WHERE o.dataset_version_id IN ({placeholders})""",
                tuple(sorted(version_ids)),
            ).fetchall()
            expected = {
                "dataset-observation": {row[0] for row in expected_rows},
                "evidence-item": {row[1] for row in expected_rows},
                "source-record": {row[2] for row in expected_rows},
                "dataset-observation-partition-link": {row[3] for row in expected_rows},
            }
            for reference_type, identifiers in expected.items():
                column = _REFERENCE_COLUMNS[reference_type]
                actual = {
                    ref[column]
                    for ref in refs
                    if ref["reference_type"] == reference_type and ref[column] is not None
                }
                if not identifiers.issubset(actual):
                    refuse("receipt-incomplete")
    elif receipt["claim_id"] == "claim:snapshot-join":
        if receipt["output_locator"] != "/slices" or any(
            ref["output_field"] != "/slices" for ref in refs
        ):
            refuse("invalid-json-pointer")


_REFERENCE_COLUMNS = {
    "evidence-item": "evidence_item_id",
    "source-record": "source_record_id",
    "dataset-observation": "dataset_observation_id",
    "evidence-span": "evidence_span_id",
    "evidence-right": "evidence_right_id",
    "dataset-version": "dataset_version_id",
    "universe-membership": "universe_membership_id",
    "entity-mapping": "entity_mapping_id",
    "observation-membership-link": "observation_membership_link_id",
    "entity-relationship": "entity_relationship_id",
    "target-grid-cell": "target_grid_cell_id",
    "funnel-opportunity": "funnel_opportunity_id",
    "funnel-schema": "funnel_schema_id",
    "funnel-cohort": "funnel_cohort_id",
    "funnel-event": "funnel_event_id",
    "funnel-cohort-event-link": "funnel_cohort_event_link_id",
    "dataset-delivery-partition": "dataset_delivery_partition_id",
    "dataset-observation-partition-link": "dataset_observation_partition_link_id",
    "snapshot": "snapshot_digest",
}
