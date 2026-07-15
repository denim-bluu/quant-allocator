from datetime import UTC, datetime

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.entitlements import require_item_access, resolve_query_right
from quant_allocator.evidence.ingest import ingest_datasets, ingest_rights
from quant_allocator.evidence.model import DatasetRecord, EvidenceRightRecord, with_machine_id
from quant_allocator.evidence.schema import connect, initialize


def test_rights_are_exact_scope_half_open_and_never_silently_upgraded() -> None:
    conn = connect()
    initialize(conn)
    ingest_datasets(
        conn,
        [DatasetRecord("dataset:d", "D", "licensed", "licensed-receipt", "v1", "nda", "research")],
    )
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 2, 1, tzinfo=UTC)
    right_record = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:r",
            1,
            "dataset:d",
            "funded-manager-reporting",
            "research",
            "active",
            "access-only-while-active",
            start,
            start,
            end,
        ),
    )
    ingest_rights(conn, [right_record])
    right = resolve_query_right(
        conn,
        evidence_right_id=right_record.evidence_right_id,
        decision_at=datetime(2024, 1, 15, tzinfo=UTC),
        access_context="funded-manager-reporting",
        licence_purpose="research",
    )
    assert right.evidence_right_id == right_record.evidence_right_id
    with pytest.raises(EvidenceRefusal, match="entitlement-not-active"):
        resolve_query_right(
            conn,
            evidence_right_id=right_record.evidence_right_id,
            decision_at=end,
            access_context="funded-manager-reporting",
            licence_purpose="research",
        )
    with pytest.raises(EvidenceRefusal, match="access-context-mismatch"):
        resolve_query_right(
            conn,
            evidence_right_id=right_record.evidence_right_id,
            decision_at=datetime(2024, 1, 15, tzinfo=UTC),
            access_context="public",
            licence_purpose="research",
        )


def test_item_access_requires_matching_acquisition_scope() -> None:
    item = {
        "access_context": "public",
        "licence_purpose": "research",
        "acquisition_right_id": f"right:sha256:{'0' * 64}",
    }
    right = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:r",
            1,
            "dataset:d",
            "funded-manager-reporting",
            "research",
            "active",
            "retain-after-expiry",
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 1, tzinfo=UTC),
            None,
        ),
    )
    with pytest.raises(EvidenceRefusal, match="access-context-mismatch"):
        require_item_access(item, right)


def test_access_only_acquisition_cannot_be_reclassified_as_retained_by_successor() -> None:
    conn = connect()
    initialize(conn)
    ingest_datasets(
        conn,
        [DatasetRecord("dataset:d", "D", "licensed", "licensed-receipt", "v1", "nda", "research")],
    )
    jan = datetime(2024, 1, 1, tzinfo=UTC)
    feb = datetime(2024, 2, 1, tzinfo=UTC)
    mar = datetime(2024, 3, 1, tzinfo=UTC)
    first = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:r",
            1,
            "dataset:d",
            "funded-manager-reporting",
            "research",
            "active",
            "access-only-while-active",
            jan,
            jan,
            feb,
        ),
    )
    second = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:r",
            2,
            "dataset:d",
            "funded-manager-reporting",
            "research",
            "active",
            "retain-after-expiry",
            mar,
            mar,
            None,
            first.evidence_right_id,
        ),
    )
    ingest_rights(conn, [first, second])
    successor = resolve_query_right(
        conn,
        evidence_right_id=second.evidence_right_id,
        decision_at=datetime(2024, 4, 1, tzinfo=UTC),
        access_context="funded-manager-reporting",
        licence_purpose="research",
    )
    item = {
        "access_context": "funded-manager-reporting",
        "licence_purpose": "research",
        "acquisition_right_id": first.evidence_right_id,
    }
    with pytest.raises(EvidenceRefusal, match="right-retention-forbidden"):
        require_item_access(item, successor, conn)
