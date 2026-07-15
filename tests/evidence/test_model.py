from datetime import UTC, datetime, timedelta

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.model import (
    DatasetSliceRequest,
    SourceRecordRecord,
    canonical_bytes,
    contains,
    digest_id,
    machine_id,
    machine_id_for_record,
    normalize_utc,
    require_machine_id,
    validate_identifier,
    with_machine_id,
)


def test_model_normalizes_utc_and_uses_half_open_intervals() -> None:
    local = datetime(2024, 6, 1, 4, tzinfo=UTC) + timedelta(0)
    assert normalize_utc(local) == "2024-06-01T04:00:00.000000Z"
    assert contains(
        "2024-01-01T00:00:00.000000Z", "2024-02-01T00:00:00.000000Z", "2024-01-31T23:59:59.000000Z"
    )
    assert not contains(
        "2024-01-01T00:00:00.000000Z", "2024-02-01T00:00:00.000000Z", "2024-02-01T00:00:00.000000Z"
    )
    with pytest.raises(EvidenceRefusal, match="invalid-utc"):
        normalize_utc(datetime(2024, 1, 1))


def test_ids_and_requests_are_canonical_and_temporally_unambiguous() -> None:
    validate_identifier("dataset:public-returns")
    with pytest.raises(EvidenceRefusal, match="invalid-id"):
        validate_identifier("Dataset_Bad")
    assert digest_id("snapshot", {"b": 2, "a": 1}) == digest_id("snapshot", {"a": 1, "b": 2})
    assert canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:returns", "manager", "A", "product")
    )
    assert source.source_record_id == machine_id_for_record("source-record", source)
    with pytest.raises(EvidenceRefusal, match="machine-id-mismatch"):
        require_machine_id("source-record", f"source-record:sha256:{'0' * 64}", source)
    with pytest.raises(EvidenceRefusal, match="invalid-machine-id-input"):
        machine_id("mapping", {"source_evidence_item_id": source.source_record_id})
    with pytest.raises(EvidenceRefusal, match="invalid-temporal-shape"):
        DatasetSliceRequest(
            dataset_id="dataset:returns",
            access_context="public",
            evidence_right_id=f"right:sha256:{'0' * 64}",
            licence_purpose="research",
            valid_at=datetime(2024, 1, 1, tzinfo=UTC),
            valid_window=(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)),
        )
