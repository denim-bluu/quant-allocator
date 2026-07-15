from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .checks import refuse
from .entitlements import require_item_access, resolve_query_right
from .ingest import (
    expected_partition_manifest,
    received_partition_manifest,
    reconstruct_dataset_version,
)
from .lineage import make_receipt, store_receipt
from .model import (
    DatasetSliceRequest,
    ReceiptReference,
    SnapshotBundle,
    SnapshotBundleRequest,
    SnapshotSlice,
    canonical_bytes,
    digest_id,
    normalize_utc,
    sha256,
)

_SNAPSHOT_DOMAIN = b"quant-allocator-evidence-snapshot-v1\n"
_BUNDLE_DOMAIN = b"quant-allocator-evidence-bundle-v1\n"


def as_known_slice(
    conn: sqlite3.Connection, *, decision_at: datetime, request: DatasetSliceRequest
) -> SnapshotSlice:
    cutoff = normalize_utc(decision_at)
    right = resolve_query_right(
        conn,
        evidence_right_id=request.evidence_right_id,
        decision_at=decision_at,
        access_context=request.access_context,
        licence_purpose=request.licence_purpose,
    )
    if right.dataset_id != request.dataset_id:
        refuse("access-context-mismatch")
    versions = _accessible_versions(conn, request.dataset_id, cutoff, request)
    if not versions:
        return _persist_slice(conn, request, cutoff, (), right.evidence_right_id, (), (), (), ())
    if request.revision_mode == "all-known-versions":
        partition_ids = tuple(
            identifier for version in versions for identifier in _validate_partitions(conn, version)
        )
        rows = _audit_rows(conn, versions, request, cutoff, right)
        observation_ids = tuple(row["dataset_observation_id"] for row in rows)
        version_ids = tuple(version["dataset_version_id"] for version in versions)
        delivery_refs = tuple(
            ref
            for version in versions
            for ref in _delivery_references(conn, version, (version["dataset_version_id"],))
        )
    else:
        selected = versions[-1]
        partition_ids = _validate_partitions(conn, selected)
        reconstructed = reconstruct_dataset_version(conn, selected["dataset_version_id"])
        accessible_ids = {version["dataset_version_id"] for version in versions}
        if not set(reconstructed.contributing_dataset_version_ids).issubset(accessible_ids):
            refuse("incomplete-revision-chain")
        rows = []
        observation_ids = []
        for materialized in reconstructed.rows:
            envelope = conn.execute(
                """SELECT e.*,i.payload_json FROM evidence_envelope e
                   JOIN evidence_item i USING(evidence_item_id)
                   WHERE e.evidence_item_id=? AND e.available_at<=?
                   ORDER BY e.available_at DESC LIMIT 1""",
                (materialized["evidence_item_id"], cutoff),
            ).fetchone()
            if envelope is None:
                continue
            require_item_access(envelope, right, conn)
            row = _public_row(envelope, selected, json.loads(envelope["payload_json"]))
            if _valid(row, request):
                rows.append(row)
                observation_ids.append(envelope["dataset_observation_id"])
        rows = tuple(sorted(rows, key=_row_key))
        observation_ids = tuple(observation_ids)
        version_ids = reconstructed.contributing_dataset_version_ids
        if (
            selected["delivery_mode"] == "full-snapshot"
            and selected["absence_semantics"] == "full-snapshot-means-removed"
            and selected["predecessor_dataset_version_id"]
        ):
            version_ids = (selected["predecessor_dataset_version_id"],) + version_ids
        delivery_refs = _delivery_references(conn, selected, version_ids)
    return _persist_slice(
        conn,
        request,
        cutoff,
        tuple(rows),
        right.evidence_right_id,
        observation_ids,
        version_ids,
        partition_ids,
        delivery_refs,
    )


def _validate_partitions(conn: sqlite3.Connection, version: sqlite3.Row) -> tuple[str, ...]:
    rows = conn.execute(
        "SELECT * FROM dataset_delivery_partition WHERE dataset_version_id=? ORDER BY partition_key",
        (version["dataset_version_id"],),
    ).fetchall()
    if version["completeness_status"] != "complete":
        refuse("incomplete-dataset-version")
    if (
        len(rows) != version["expected_partition_count"]
        or sum(
            row["received_record_count"] > 0 or row["partition_status"] == "expected-received"
            for row in rows
        )
        != version["received_partition_count"]
        or any(row["partition_status"] != "expected-received" for row in rows)
    ):
        refuse("incomplete-dataset-version")
    if (
        expected_partition_manifest(rows) != version["expected_partition_manifest_sha256"]
        or received_partition_manifest(rows) != version["received_partition_manifest_sha256"]
    ):
        refuse("partition-manifest-mismatch")
    observations = conn.execute(
        "SELECT count(*) FROM dataset_observation WHERE dataset_version_id=?",
        (version["dataset_version_id"],),
    ).fetchone()[0]
    links = conn.execute(
        """SELECT l.dataset_delivery_partition_id,o.observation_status
           FROM dataset_observation_partition_link l
           JOIN dataset_observation o USING(dataset_observation_id)
           WHERE o.dataset_version_id=?""",
        (version["dataset_version_id"],),
    ).fetchall()
    if len(links) != observations:
        refuse("partition-manifest-mismatch")
    for partition in rows:
        linked = [
            row
            for row in links
            if row["dataset_delivery_partition_id"] == partition["dataset_delivery_partition_id"]
        ]
        received_count = (
            len(linked)
            if version["delivery_mode"] == "delta"
            else sum(row["observation_status"] == "present" for row in linked)
        )
        if received_count != partition["received_record_count"]:
            refuse("partition-manifest-mismatch")
    return tuple(row["dataset_delivery_partition_id"] for row in rows)


def _delivery_references(
    conn: sqlite3.Connection, selected: sqlite3.Row, version_ids: tuple[str, ...]
) -> tuple[ReceiptReference, ...]:
    refs: list[ReceiptReference] = []
    for version_id in dict.fromkeys(version_ids):
        version = conn.execute(
            "SELECT * FROM dataset_version WHERE dataset_version_id=?", (version_id,)
        ).fetchone()
        if version is None:
            refuse("delta-predecessor-invalid")
        partition_ids = _validate_partitions(conn, version)
        refs.append(
            ReceiptReference(
                "/rows",
                "dataset-version",
                version_id,
                "included",
                "",
                "schema:generic-v1",
                "/",
                "input",
            )
        )
        refs.extend(
            ReceiptReference(
                "/rows",
                "dataset-delivery-partition",
                identifier,
                "included",
                "",
                "schema:generic-v1",
                "/",
                "denominator",
            )
            for identifier in partition_ids
        )
        observations = conn.execute(
            """SELECT o.*,i.source_record_id FROM dataset_observation o
               JOIN evidence_item i USING(evidence_item_id)
               WHERE dataset_version_id=? ORDER BY dataset_observation_id""",
            (version_id,),
        )
        for observation in observations:
            removed = observation["observation_status"] == "explicitly-removed"
            disposition = "excluded" if removed else "included"
            reason = observation["disappearance_reason"] or "" if removed else ""
            refs.extend(
                (
                    ReceiptReference(
                        "/rows",
                        "dataset-observation",
                        observation["dataset_observation_id"],
                        disposition,
                        reason,
                        "schema:generic-v1",
                        "/",
                        "input",
                    ),
                    ReceiptReference(
                        "/rows",
                        "evidence-item",
                        observation["evidence_item_id"],
                        disposition,
                        reason,
                        "schema:generic-v1",
                        "/",
                        "input",
                    ),
                    ReceiptReference(
                        "/rows",
                        "source-record",
                        observation["source_record_id"],
                        disposition,
                        reason,
                        "schema:generic-v1",
                        "/",
                        "input",
                    ),
                )
            )
            link = conn.execute(
                """SELECT dataset_observation_partition_link_id
                   FROM dataset_observation_partition_link WHERE dataset_observation_id=?""",
                (observation["dataset_observation_id"],),
            ).fetchone()
            if link is None:
                refuse("partition-manifest-mismatch")
            refs.append(
                ReceiptReference(
                    "/rows",
                    "dataset-observation-partition-link",
                    link[0],
                    disposition,
                    reason,
                    "schema:generic-v1",
                    "/",
                    "denominator",
                )
            )
    return tuple(refs)


def _accessible_versions(
    conn: sqlite3.Connection, dataset_id: str, cutoff: str, request: DatasetSliceRequest
):
    rows = conn.execute(
        """SELECT v.* FROM dataset_version v JOIN dataset d USING(dataset_id)
           JOIN evidence_right vr ON vr.evidence_right_id=v.acquisition_right_id
           JOIN evidence_right qr ON qr.evidence_right_id=?
           WHERE v.dataset_id=? AND
             CASE d.availability_policy
               WHEN 'public-publication' THEN coalesce(v.published_at,v.first_observed_at_utc)
               ELSE v.received_at_utc END <= ?
             AND coalesce(v.embargo_until,'0001-01-01T00:00:00.000000Z') <= ?
             AND vr.dataset_id=v.dataset_id AND vr.received_at_utc<=?
             AND vr.entitlement_from<=coalesce(v.received_at_utc,v.published_at,v.first_observed_at_utc)
             AND (vr.entitlement_to IS NULL OR
                  coalesce(v.received_at_utc,v.published_at,v.first_observed_at_utc)<vr.entitlement_to)
             AND vr.status!='revoked' AND vr.access_context=? AND vr.licence_purpose=?
             AND vr.right_series_id=qr.right_series_id
             AND (vr.evidence_right_id=qr.evidence_right_id OR
                  (vr.retention_policy='retain-after-expiry' AND
                   qr.retention_policy='retain-after-expiry'))
           ORDER BY v.dataset_version_id""",
        (
            request.evidence_right_id,
            dataset_id,
            cutoff,
            cutoff,
            cutoff,
            request.access_context,
            request.licence_purpose,
        ),
    ).fetchall()
    if not rows:
        return []
    by_id = {row["dataset_version_id"]: row for row in rows}
    children: dict[str, list[str]] = {identifier: [] for identifier in by_id}
    roots = []
    for identifier, row in by_id.items():
        parent = row["predecessor_dataset_version_id"]
        if parent in by_id:
            children[parent].append(identifier)
        elif parent is None:
            roots.append(identifier)
        else:
            refuse("incomplete-revision-chain")
    if len(roots) != 1 or any(len(value) > 1 for value in children.values()):
        refuse("delta-predecessor-invalid")
    ordered = []
    current: str | None = roots[0]
    while current is not None:
        ordered.append(by_id[current])
        current = children[current][0] if children[current] else None
    if len(ordered) != len(rows):
        refuse("delta-predecessor-invalid")
    return ordered


def _audit_rows(conn, versions, request, cutoff, right):
    out = []
    for version in versions:
        for row in conn.execute(
            """SELECT e.*,i.payload_json FROM evidence_envelope e JOIN evidence_item i USING(evidence_item_id)
               WHERE e.dataset_version_id=? AND e.available_at<=? ORDER BY e.source_record_id,e.version""",
            (version["dataset_version_id"], cutoff),
        ):
            require_item_access(row, right, conn)
            public = _public_row(row, version, json.loads(row["payload_json"]))
            if _valid(public, request):
                out.append(public)
    return tuple(sorted(out, key=_row_key))


def _public_row(row, version, payload):
    return {
        "dataset_id": row["dataset_id"],
        "dataset_version_id": version["dataset_version_id"],
        "delivery_mode": version["delivery_mode"],
        "absence_semantics": version["absence_semantics"],
        "completeness_status": version["completeness_status"],
        "expected_partition_manifest_sha256": version["expected_partition_manifest_sha256"],
        "received_partition_manifest_sha256": version["received_partition_manifest_sha256"],
        "expected_partition_count": version["expected_partition_count"],
        "received_partition_count": version["received_partition_count"],
        "predecessor_dataset_version_id": version["predecessor_dataset_version_id"],
        "base_dataset_version_id": version["base_dataset_version_id"],
        "reconstruction_manifest_sha256": version["reconstruction_manifest_sha256"],
        "reconstruction_row_count": version["reconstruction_row_count"],
        "dataset_observation_id": row["dataset_observation_id"],
        "source_record_id": row["source_record_id"],
        "evidence_item_id": row["evidence_item_id"],
        "canonical_entity_id": row["canonical_entity_id"],
        "field_dictionary_version": row["field_dictionary_version"],
        "temporal_type": row["temporal_type"],
        "effective_at": row["effective_at"],
        "effective_from": row["effective_from"],
        "effective_to": row["effective_to"],
        "available_at": row["available_at"],
        "version": row["version"],
        "observation_status": row["observation_status"],
        "payload": payload,
    }


def _valid(row: Mapping[str, Any], request: DatasetSliceRequest) -> bool:
    if (
        request.canonical_entity_ids
        and row["canonical_entity_id"] not in request.canonical_entity_ids
    ):
        return False
    if row["canonical_entity_id"] is None and not request.include_unresolved:
        return False
    if request.valid_at is not None:
        instant = normalize_utc(request.valid_at)
        if row["temporal_type"] == "point":
            return row["effective_at"] == instant
        return row["effective_from"] <= instant and (
            row["effective_to"] is None or instant < row["effective_to"]
        )
    if request.valid_window is not None:
        start, end = map(normalize_utc, request.valid_window)
        if row["temporal_type"] == "point":
            return start <= row["effective_at"] < end
        return row["effective_from"] < end and (
            row["effective_to"] is None or start < row["effective_to"]
        )
    return True


def _row_key(row: Mapping[str, Any]):
    return (
        row["dataset_id"],
        row["dataset_version_id"],
        row["source_record_id"],
        row["canonical_entity_id"] is None,
        row["canonical_entity_id"] or "",
        row["effective_at"] is None,
        row["effective_at"] or "",
        row["version"],
        row["evidence_item_id"],
    )


def _persist_slice(
    conn, request, cutoff, rows, right_id, observation_ids, version_ids, partition_ids, extra_refs
):
    request_payload = {"request": request, "decision_at": cutoff}
    body = _SNAPSHOT_DOMAIN + canonical_bytes(request_payload) + b"\n"
    for row in rows:
        body += canonical_bytes(row) + b"\n"
    digest = digest_id("snapshot", {"bytes_sha256": sha256(body)})
    references = [
        ReceiptReference(
            "/rows", "evidence-right", right_id, "included", "", "schema:generic-v1", "/", "filter"
        )
    ]
    references.extend(
        ReceiptReference(
            "/rows",
            "dataset-observation",
            identifier,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "input",
        )
        for identifier in observation_ids
    )
    references.extend(extra_refs)
    references.extend(
        ReceiptReference(
            "/rows",
            "dataset-version",
            identifier,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "input",
        )
        for identifier in version_ids
    )
    references.extend(
        ReceiptReference(
            "/rows",
            "dataset-delivery-partition",
            identifier,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "denominator",
        )
        for identifier in partition_ids
    )
    receipt = make_receipt(
        claim_id="claim:snapshot-slice",
        output_locator="/rows",
        input_digest=digest,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="as-known-slice",
        algorithm_version="1",
        parameters=request_payload,
        value=rows,
        references=references,
    )
    store_receipt(conn, receipt)
    conn.execute(
        "INSERT OR IGNORE INTO snapshot_manifest VALUES (?,?,?,?)",
        (
            digest,
            canonical_bytes(request_payload).decode(),
            len(rows),
            sha256(b"".join(canonical_bytes(row) + b"\n" for row in rows)),
        ),
    )
    return SnapshotSlice(request, rows, digest, receipt.receipt_id, cutoff)


def as_known_bundle(conn: sqlite3.Connection, request: SnapshotBundleRequest) -> SnapshotBundle:
    if not request.sources:
        refuse("bundle-source-duplicate")
    ids = [source.dataset_id for source in request.sources]
    if len(ids) != len(set(ids)):
        refuse("bundle-source-duplicate")
    if not request.join_keys:
        refuse("join-key-undefined")
    canonical_request = SnapshotBundleRequest(
        request.decision_at,
        tuple(sorted(request.sources, key=lambda source: source.dataset_id)),
        tuple(request.join_keys),
        request.join_policy,
    )
    slices = tuple(
        as_known_slice(conn, decision_at=canonical_request.decision_at, request=source)
        for source in canonical_request.sources
    )
    key_sets: list[set[tuple[Any, ...]]] = []
    for slice_ in slices:
        keys = set()
        for row in slice_.rows:
            if any(key not in row for key in canonical_request.join_keys):
                refuse("join-key-undefined")
            keys.add(tuple(row[key] for key in canonical_request.join_keys))
        key_sets.append(keys)
    matched_keys = set.intersection(*key_sets) if key_sets else set()
    pairs = tuple((s.request.dataset_id, s.digest) for s in slices)
    composite = sha256(
        _BUNDLE_DOMAIN + canonical_bytes({"request": canonical_request, "slices": pairs})
    )
    refs = tuple(
        ReceiptReference(
            "/slices", "snapshot", s.digest, "included", "", "schema:generic-v1", "/", "join"
        )
        for s in slices
    )
    row_refs = []
    for slice_ in slices:
        for row in slice_.rows:
            key = tuple(row[name] for name in canonical_request.join_keys)
            included = len(slices) == 1 or key in matched_keys
            row_refs.append(
                ReceiptReference(
                    "/slices",
                    "evidence-item",
                    row["evidence_item_id"],
                    "included" if included else "excluded",
                    "" if included else "unmatched-join-key",
                    "schema:generic-v1",
                    "/",
                    "join",
                )
            )
    receipt = make_receipt(
        claim_id="claim:snapshot-join",
        output_locator="/slices",
        input_digest=composite,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id=canonical_request.join_policy,
        algorithm_version="1",
        parameters={"join_keys": canonical_request.join_keys},
        value=pairs,
        references=refs + tuple(row_refs),
    )
    store_receipt(conn, receipt)
    bundle_digest = digest_id(
        "bundle",
        {"request": canonical_request, "slices": pairs, "join_receipt_id": receipt.receipt_id},
    )
    conn.execute(
        "INSERT OR IGNORE INTO snapshot_bundle_manifest VALUES (?,?,?,?,?,?,?)",
        (
            bundle_digest,
            canonical_bytes(canonical_request).decode(),
            canonical_bytes(pairs).decode(),
            composite,
            receipt.receipt_id,
            sum(len(s.rows) for s in slices),
            sha256(b"".join(snapshot_bytes(s) for s in slices)),
        ),
    )
    return SnapshotBundle(canonical_request, slices, composite, receipt.receipt_id, bundle_digest)


def snapshot_bytes(snapshot_slice: SnapshotSlice) -> bytes:
    body = (
        _SNAPSHOT_DOMAIN
        + canonical_bytes(
            {"request": snapshot_slice.request, "decision_at": snapshot_slice.decision_at}
        )
        + b"\n"
    )
    return body + b"".join(canonical_bytes(row) + b"\n" for row in snapshot_slice.rows)


def bundle_bytes(bundle: SnapshotBundle) -> bytes:
    return _BUNDLE_DOMAIN + canonical_bytes(bundle) + b"\n"


def export_snapshot(bundle: SnapshotBundle, receipts: Iterable[Mapping[str, Any]], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "snapshot.json": canonical_bytes(bundle) + b"\n",
        "records.jsonl": b"".join(
            canonical_bytes(row) + b"\n" for s in bundle.slices for row in s.rows
        ),
        "receipts.jsonl": b"".join(
            canonical_bytes(row) + b"\n"
            for row in sorted(receipts, key=lambda row: str(row.get("receipt_id", "")))
        ),
    }
    paths = []
    for name, content in files.items():
        path = out_dir / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(path)
        paths.append(path)
    return tuple(paths)
