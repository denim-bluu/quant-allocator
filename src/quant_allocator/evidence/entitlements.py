from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Mapping

from .checks import refuse
from .model import EvidenceRightRecord, normalize_utc


def resolve_query_right(
    conn: sqlite3.Connection,
    *,
    evidence_right_id: str,
    decision_at: datetime,
    access_context: str,
    licence_purpose: str,
) -> EvidenceRightRecord:
    cutoff = normalize_utc(decision_at)
    row = conn.execute(
        "SELECT * FROM evidence_right WHERE evidence_right_id=?", (evidence_right_id,)
    ).fetchone()
    if row is None:
        refuse("missing-evidence-right")
    if row["received_at_utc"] > cutoff:
        refuse("right-not-known")
    if row["access_context"] != access_context:
        refuse("access-context-mismatch")
    if row["licence_purpose"] != licence_purpose:
        refuse("licence-purpose-mismatch")
    if not (
        row["entitlement_from"] <= cutoff
        and (row["entitlement_to"] is None or cutoff < row["entitlement_to"])
    ):
        refuse("entitlement-not-active")
    if row["status"] == "revoked":
        refuse("right-revoked")
    if row["status"] in {"expired", "superseded"}:
        refuse("right-superseded")
    later = conn.execute(
        "SELECT 1 FROM evidence_right WHERE right_series_id=? AND right_version>? AND received_at_utc<=? LIMIT 1",
        (row["right_series_id"], row["right_version"], cutoff),
    ).fetchone()
    if later is not None:
        refuse("right-superseded")
    return EvidenceRightRecord(
        row["evidence_right_id"],
        row["right_series_id"],
        row["right_version"],
        row["dataset_id"],
        row["access_context"],
        row["licence_purpose"],
        row["status"],
        row["retention_policy"],
        _dt(row["received_at_utc"]),
        _dt(row["entitlement_from"]),
        _dt(row["entitlement_to"]) if row["entitlement_to"] else None,
        row["supersedes_right_id"],
    )


def require_item_access(
    item: Mapping[str, object],
    query_right: EvidenceRightRecord,
    conn: sqlite3.Connection | None = None,
) -> bool:
    if item["access_context"] != query_right.access_context:
        refuse("access-context-mismatch")
    if item["licence_purpose"] != query_right.licence_purpose:
        refuse("licence-purpose-mismatch")
    acquired = item["acquisition_right_id"]
    if acquired != query_right.evidence_right_id:
        if query_right.retention_policy != "retain-after-expiry" or conn is None:
            refuse("right-retention-forbidden")
        acquired_row = conn.execute(
            "SELECT * FROM evidence_right WHERE evidence_right_id=?", (acquired,)
        ).fetchone()
        if (
            acquired_row is None
            or acquired_row["dataset_id"] != query_right.dataset_id
            or acquired_row["right_series_id"] != query_right.right_series_id
            or acquired_row["access_context"] != query_right.access_context
            or acquired_row["licence_purpose"] != query_right.licence_purpose
            or acquired_row["retention_policy"] != "retain-after-expiry"
            or acquired_row["status"] == "revoked"
        ):
            refuse("right-retention-forbidden")
    return True


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
