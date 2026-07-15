from __future__ import annotations

import sqlite3

from .checks import refuse
from .lineage import make_receipt, store_receipt
from .model import (
    ReceiptReference,
    SnapshotSlice,
    canonical_bytes,
    digest_id,
    machine_id,
    sha256,
)

_SNAPSHOT_DOMAIN = b"quant-allocator-evidence-snapshot-v1\n"
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


def _authorized_projection_version_ids(
    conn: sqlite3.Connection,
    snapshot_slice: SnapshotSlice,
) -> set[str]:
    if snapshot_slice.receipt_id is None or snapshot_slice.decision_at is None:
        refuse("receipt-incomplete")

    request_payload = {
        "request": snapshot_slice.request,
        "decision_at": snapshot_slice.decision_at,
    }
    encoded_request = canonical_bytes(request_payload)
    encoded_rows = b"".join(canonical_bytes(row) + b"\n" for row in snapshot_slice.rows)
    expected_digest = digest_id(
        "snapshot",
        {
            "bytes_sha256": sha256(
                _SNAPSHOT_DOMAIN + encoded_request + b"\n" + encoded_rows
            )
        },
    )
    manifest = conn.execute(
        "SELECT * FROM snapshot_manifest WHERE snapshot_digest=?",
        (snapshot_slice.digest,),
    ).fetchone()
    if (
        snapshot_slice.digest != expected_digest
        or manifest is None
        or manifest["request_json"] != encoded_request.decode()
        or manifest["row_count"] != len(snapshot_slice.rows)
        or manifest["records_sha256"] != sha256(encoded_rows)
    ):
        refuse("receipt-incomplete")

    receipt = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
        (snapshot_slice.receipt_id,),
    ).fetchone()
    reference_rows = conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
        (snapshot_slice.receipt_id,),
    ).fetchall()
    persisted_references = []
    for row in reference_rows:
        identifiers = [
            row[column]
            for column in row.keys()
            if column not in _RECEIPT_REFERENCE_HEADER_COLUMNS and row[column] is not None
        ]
        if len(identifiers) != 1:
            refuse("receipt-incomplete")
        persisted_references.append(
            ReceiptReference(
                row["output_field"],
                row["reference_type"],
                identifiers[0],
                row["disposition"],
                row["reason_code"],
                row["source_schema_id"],
                row["source_field"],
                row["role"],
            )
        )
    persisted_references = tuple(persisted_references)
    seal = conn.execute(
        "SELECT * FROM receipt_seal WHERE receipt_id=?",
        (snapshot_slice.receipt_id,),
    ).fetchone()
    if (
        receipt is None
        or not persisted_references
        or seal is None
        or seal["reference_count"] != len(persisted_references)
        or seal["references_sha256"] != sha256(canonical_bytes(persisted_references))
        or any(
            reference.output_field != "/rows"
            or reference.source_schema_id != "schema:generic-v1"
            or reference.source_field != "/"
            for reference in persisted_references
        )
    ):
        refuse("receipt-incomplete")

    expected_receipt = make_receipt(
        claim_id="claim:snapshot-slice",
        output_locator="/rows",
        input_digest=snapshot_slice.digest,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="as-known-slice",
        algorithm_version="1",
        parameters=request_payload,
        value=snapshot_slice.rows,
        references=persisted_references,
    )
    expected_header = (
        expected_receipt.receipt_id,
        expected_receipt.claim_id,
        expected_receipt.output_locator,
        expected_receipt.input_digest,
        expected_receipt.output_schema_id,
        expected_receipt.current_attestation,
        expected_receipt.live_attestation_ceiling,
        expected_receipt.algorithm_id,
        expected_receipt.algorithm_version,
        expected_receipt.parameters_sha256,
        expected_receipt.value_sha256,
    )
    if (
        tuple(receipt) != expected_header
        or persisted_references != expected_receipt.references
    ):
        refuse("receipt-incomplete")

    authorized = {
        reference.reference_id
        for reference in persisted_references
        if reference.reference_type == "dataset-version"
        and reference.disposition == "included"
        and reference.role == "input"
        and not reference.reason_code
    }
    if not {row["dataset_version_id"] for row in snapshot_slice.rows}.issubset(authorized):
        refuse("receipt-incomplete")
    if authorized:
        placeholders = ",".join("?" for _ in authorized)
        datasets = {
            row[0]
            for row in conn.execute(
                f"SELECT dataset_id FROM dataset_version WHERE dataset_version_id IN ({placeholders})",
                tuple(sorted(authorized)),
            )
        }
        if datasets != {snapshot_slice.request.dataset_id}:
            refuse("receipt-incomplete")
    return authorized


def _project(conn: sqlite3.Connection, table: str, snapshot_slice: SnapshotSlice):
    authorized_version_ids = _authorized_projection_version_ids(conn, snapshot_slice)
    included = {
        (row["evidence_item_id"], row["dataset_observation_id"])
        for row in snapshot_slice.rows
    }
    item_ids = {key[0] for key in included}
    if not item_ids:
        return ()
    placeholders = ",".join("?" for _ in item_ids)
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE source_evidence_item_id IN ({placeholders}) ORDER BY 1",
        tuple(sorted(item_ids)),
    ).fetchall()
    visible = [
        dict(row)
        for row in rows
        if (
            row["source_evidence_item_id"],
            row["dataset_observation_id"],
        )
        in included
        and row["dataset_version_id"] in authorized_version_ids
    ]
    if snapshot_slice.request.revision_mode == "latest-known":
        parent_ids = {row["revision_of"] for row in visible if row.get("revision_of")}
        identifier_column = f"{table}_id"
        visible = [row for row in visible if row[identifier_column] not in parent_ids]
    return tuple(row for row in visible if _projection_valid(row, snapshot_slice))


def _projection_valid(row, snapshot_slice: SnapshotSlice) -> bool:
    if (
        "temporal_type" not in row
        or snapshot_slice.request.valid_at is None
        and snapshot_slice.request.valid_window is None
    ):
        return True
    from .model import normalize_utc

    if snapshot_slice.request.valid_at is not None:
        instant = normalize_utc(snapshot_slice.request.valid_at)
        if row["temporal_type"] == "point":
            return row["effective_at"] == instant
        return row["effective_from"] <= instant and (
            row["effective_to"] is None or instant < row["effective_to"]
        )
    start, end = map(normalize_utc, snapshot_slice.request.valid_window)
    if row["temporal_type"] == "point":
        return start <= row["effective_at"] < end
    return row["effective_from"] < end and (
        row["effective_to"] is None or start < row["effective_to"]
    )


def project_entity_mappings(conn, snapshot_slice):
    return _project(conn, "entity_mapping", snapshot_slice)


def project_entity_relationships(conn, snapshot_slice):
    return _project(conn, "entity_relationship", snapshot_slice)


def project_universe_memberships(conn, snapshot_slice):
    return _project(conn, "universe_membership", snapshot_slice)


def project_target_grids(conn, snapshot_slice):
    return _project(conn, "target_grid", snapshot_slice)


def project_funnel_opportunities(conn, snapshot_slice):
    return _project(conn, "funnel_opportunity", snapshot_slice)


def project_funnel_schemas(conn, snapshot_slice):
    return _project(conn, "funnel_schema", snapshot_slice)


def project_funnel_cohorts(conn, snapshot_slice):
    return _project(conn, "funnel_cohort", snapshot_slice)


def project_funnel_events(conn, snapshot_slice):
    return _project(conn, "funnel_event", snapshot_slice)


def project_funnel_cohort_event_links(conn, snapshot_slice, *, funnel_cohort_id: str):
    event_ids = {row["funnel_event_id"] for row in project_funnel_events(conn, snapshot_slice)}
    rows = conn.execute(
        "SELECT * FROM funnel_cohort_event_link WHERE funnel_cohort_id=? ORDER BY funnel_event_id",
        (funnel_cohort_id,),
    )
    return tuple(dict(row) for row in rows if row["funnel_event_id"] in event_ids)


def evaluate_funnel_cohort(conn, snapshot_slice, *, funnel_cohort_id: str):
    cohorts = {row["funnel_cohort_id"]: row for row in project_funnel_cohorts(conn, snapshot_slice)}
    cohort = cohorts.get(funnel_cohort_id)
    if cohort is None:
        refuse("missing-funnel-cohort")
    if cohort["completeness_status"] != "complete":
        refuse("incomplete-funnel-cohort")
    if not (
        cohort["entry_window_from"] < cohort["entry_window_to"]
        and cohort["entry_window_to"] <= cohort["observation_window_end"]
    ):
        refuse("incomplete-funnel-window")
    if cohort["absence_rule"] == "undefined" or cohort["censor_policy"] == "undefined":
        refuse("undefined-censor-policy")
    events = project_funnel_events(conn, snapshot_slice)
    schemas = {row["funnel_schema_id"]: row for row in project_funnel_schemas(conn, snapshot_slice)}
    if cohort["funnel_schema_id"] not in schemas:
        refuse("missing-funnel-schema")
    opportunities = {
        row["funnel_opportunity_id"]: row
        for row in project_funnel_opportunities(conn, snapshot_slice)
    }
    links = []
    for event in events:
        if event["funnel_schema_id"] != cohort["funnel_schema_id"]:
            continue
        opportunity = opportunities.get(event["funnel_opportunity_id"])
        if opportunity is None:
            refuse("missing-opportunity-id")
        in_window = cohort["entry_window_from"] <= event["effective_at"] < cohort["entry_window_to"]
        accepted = event["event_status"] == "accepted"
        mapping = (
            conn.execute(
                "SELECT mapping_status FROM entity_mapping WHERE entity_mapping_id=?",
                (event["entity_mapping_id"],),
            ).fetchone()
            if event["entity_mapping_id"]
            else None
        )
        resolved = mapping is not None and mapping[0] == "resolved"
        cell = (
            conn.execute(
                "SELECT eligibility_status,exclusion_reason FROM target_grid_cell WHERE target_grid_cell_id=?",
                (event["target_grid_cell_id"],),
            ).fetchone()
            if event["target_grid_cell_id"]
            else None
        )
        eligible = cell is None or cell[0] == "eligible"
        included = in_window and (not cohort["accepted_only"] or accepted) and resolved and eligible
        disposition = "included" if included else "excluded"
        if included:
            reason = ""
        elif not resolved:
            reason = "unresolved-entity"
        elif not eligible:
            reason = cell[1] or "outside-target-grid"
        elif not accepted:
            reason = "not-accepted"
        else:
            reason = "out-of-window"
        censor_status = (
            "right-censored" if event["effective_at"] > cohort["right_censor_at"] else "observed"
        )
        link_id = machine_id(
            "funnel-cohort-event",
            {
                "funnel_cohort_id": funnel_cohort_id,
                "funnel_event_id": event["funnel_event_id"],
                "funnel_opportunity_id": event["funnel_opportunity_id"],
                "inclusion_disposition": disposition,
                "inclusion_reason_code": reason,
                "evaluation_status": "evaluated",
                "censor_status": censor_status,
            },
        )
        refs = [
            ReceiptReference(
                "/disposition",
                "funnel-schema",
                cohort["funnel_schema_id"],
                "included",
                "",
                "schema:generic-v1",
                "/",
                "filter",
            ),
            ReceiptReference(
                "/disposition",
                "funnel-cohort",
                funnel_cohort_id,
                "included",
                "",
                "schema:generic-v1",
                "/",
                "filter",
            ),
            ReceiptReference(
                "/disposition",
                "funnel-opportunity",
                event["funnel_opportunity_id"],
                "included",
                "",
                "schema:generic-v1",
                "/",
                "input",
            ),
            ReceiptReference(
                "/disposition",
                "funnel-event",
                event["funnel_event_id"],
                disposition,
                reason,
                "schema:generic-v1",
                "/",
                "input",
            ),
        ]
        if event["entity_mapping_id"]:
            refs.append(
                ReceiptReference(
                    "/disposition",
                    "entity-mapping",
                    event["entity_mapping_id"],
                    "included" if resolved else "excluded",
                    "" if resolved else "unresolved-entity",
                    "schema:generic-v1",
                    "/",
                    "filter",
                )
            )
        if event["target_grid_cell_id"]:
            refs.append(
                ReceiptReference(
                    "/disposition",
                    "target-grid-cell",
                    event["target_grid_cell_id"],
                    "included" if eligible else "excluded",
                    "" if eligible else (cell[1] if cell else "missing-target-grid"),
                    "schema:generic-v1",
                    "/",
                    "denominator",
                )
            )
        receipt = make_receipt(
            claim_id="claim:funnel-cohort-evaluation",
            output_locator=f"/links/{link_id}",
            input_digest=snapshot_slice.digest,
            output_schema_id="schema:generic-v1",
            current_attestation="D",
            live_attestation_ceiling="B",
            algorithm_id="funnel-cohort-rules",
            algorithm_version="1",
            parameters={
                "cohort": funnel_cohort_id,
                "inclusion_rule": cohort["inclusion_rule_json"],
                "exclusion_rule": cohort["exclusion_rule_json"],
                "entry_window": (cohort["entry_window_from"], cohort["entry_window_to"]),
                "observation_window_end": cohort["observation_window_end"],
                "absence_rule": cohort["absence_rule"],
                "censor_policy": cohort["censor_policy"],
                "right_censor_at": cohort["right_censor_at"],
            },
            value={"disposition": disposition, "reason": reason},
            references=tuple(refs),
        )
        store_receipt(conn, receipt)
        conn.execute(
            "INSERT OR IGNORE INTO funnel_cohort_event_link VALUES (?,?,?,?,?,?,?,?,?)",
            (
                link_id,
                funnel_cohort_id,
                event["funnel_opportunity_id"],
                event["funnel_event_id"],
                disposition,
                reason,
                "evaluated",
                censor_status,
                receipt.receipt_id,
            ),
        )
        links.append(
            dict(
                conn.execute(
                    "SELECT * FROM funnel_cohort_event_link WHERE funnel_cohort_event_link_id=?",
                    (link_id,),
                ).fetchone()
            )
        )
    return {"funnel_cohort_id": funnel_cohort_id, "links": tuple(links)}
