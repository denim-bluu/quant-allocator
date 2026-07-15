from __future__ import annotations

import sqlite3
from datetime import datetime

from .checks import refuse
from .model import DatasetSliceRequest, normalize_utc


def members_as_known_at(
    conn: sqlite3.Connection, *, slice_request: DatasetSliceRequest, decision_at: datetime
):
    cutoff = normalize_utc(decision_at)
    rows = conn.execute(
        """SELECT DISTINCT m.canonical_entity_id FROM entity_mapping m
           JOIN universe_membership u USING(entity_mapping_id)
           JOIN evidence_envelope e ON e.evidence_item_id=u.source_evidence_item_id
           WHERE e.dataset_id=? AND e.available_at<=? AND m.mapping_status='resolved'
             AND u.membership_status IN ('active','inactive','dead')
           ORDER BY m.canonical_entity_id""",
        (slice_request.dataset_id, cutoff),
    )
    return tuple(row[0] for row in rows)


def require_member(conn, *, universe_membership_id: str, slice_request, decision_at, valid_at):
    cutoff = normalize_utc(decision_at)
    valid = normalize_utc(valid_at)
    row = conn.execute(
        """SELECT u.*,m.canonical_entity_id,e.available_at FROM universe_membership u
           JOIN entity_mapping m USING(entity_mapping_id)
           JOIN evidence_envelope e ON e.evidence_item_id=u.source_evidence_item_id
           WHERE u.universe_membership_id=?""",
        (universe_membership_id,),
    ).fetchone()
    if row is None or row["available_at"] > cutoff:
        refuse("universe-member-not-known")
    if row["temporal_type"] == "interval" and not (
        row["effective_from"] <= valid
        and (row["effective_to"] is None or valid < row["effective_to"])
    ):
        refuse("universe-member-not-known")
    if row["canonical_entity_id"] is None:
        refuse("ambiguous-entity-mapping")
    return row["canonical_entity_id"]
