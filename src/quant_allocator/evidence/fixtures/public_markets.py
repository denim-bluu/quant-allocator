from __future__ import annotations

from datetime import UTC, date, datetime

from ..ingest import (
    ingest_dataset_delivery_partitions,
    ingest_dataset_observations,
    ingest_dataset_observation_partition_links,
    ingest_dataset_versions,
    ingest_items,
    ingest_source_records,
    ingest_spans,
    expected_partition_manifest,
    received_partition_manifest,
    reconstruction_manifest,
)
from ..model import (
    DatasetDeliveryPartitionRecord,
    DatasetObservationRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetVersionRecord,
    EvidenceItemRecord,
    EvidenceSpanRecord,
    SourceRecordRecord,
    canonical_bytes,
    machine_id,
    sha256,
    with_machine_id,
)
from .core import build_core_fixture


def build_public_markets_fixture(conn) -> None:
    build_core_fixture(conn)
    may = datetime(2024, 5, 10, tzinfo=UTC)
    june = datetime(2024, 6, 10, tzinfo=UTC)
    right_id = conn.execute(
        "SELECT evidence_right_id FROM evidence_right WHERE dataset_id='dataset:public-markets'"
    ).fetchone()[0]
    existing_sources = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT source_record_key,source_record_id FROM source_record WHERE dataset_id='dataset:public-markets'"
        )
    }
    e_source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:public-markets", "manager", "E", "product")
    )
    ingest_source_records(
        conn,
        [
            with_machine_id(
                "source-record",
                SourceRecordRecord("", "dataset:public-markets", "manager", "MANIFEST", "document"),
            ),
            e_source,
        ],
    )
    manifest_payload = {"label": "all", "value": 1}
    manifest_item = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right_id,
            existing_sources["MANIFEST"],
            sha256(canonical_bytes(manifest_payload)),
            "generic-record",
            "schema:generic-v1",
            "point",
            datetime(2024, 1, 10, tzinfo=UTC),
            None,
            None,
            date(2024, 1, 10),
            None,
            None,
            datetime(2024, 1, 10, tzinfo=UTC),
            None,
            1,
            None,
            "received",
            "shortlisted-nda",
            "v1",
            "nda",
            "research",
            manifest_payload,
        ),
    )
    b3_payload = {"label": "B", "value": 3}
    b3 = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right_id,
            existing_sources["B"],
            sha256(canonical_bytes(b3_payload)),
            "generic-record",
            "schema:generic-v1",
            "point",
            may,
            None,
            None,
            date(2024, 5, 10),
            None,
            None,
            may,
            None,
            3,
            machine_id("evidence", {"source_record_id": existing_sources["B"], "version": 2}),
            "received",
            "shortlisted-nda",
            "v1",
            "nda",
            "research",
            b3_payload,
            canonical_entity_id="manager:aster-quay",
        ),
    )
    e1_payload = {"label": "E", "value": 1}
    e1 = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right_id,
            e_source.source_record_id,
            sha256(canonical_bytes(e1_payload)),
            "generic-record",
            "schema:generic-v1",
            "point",
            may,
            None,
            None,
            date(2024, 5, 10),
            None,
            None,
            may,
            None,
            1,
            None,
            "received",
            "shortlisted-nda",
            "v1",
            "nda",
            "research",
            e1_payload,
            canonical_entity_id="manager:aster-quay",
        ),
    )
    ingest_items(conn, [manifest_item, b3, e1])
    manifest_span = with_machine_id(
        "span",
        EvidenceSpanRecord("", manifest_item.evidence_item_id, "/label", 0, 3, sha256(b"all")),
    )
    ingest_spans(conn, [manifest_span])
    delta_rows = [
        {
            "source_record_id": existing_sources["A"],
            "evidence_item_id": machine_id(
                "evidence", {"source_record_id": existing_sources["A"], "version": 1}
            ),
            "observation_status": "present",
        },
        {
            "source_record_id": existing_sources["B"],
            "evidence_item_id": b3.evidence_item_id,
            "observation_status": "present",
        },
        {
            "source_record_id": e_source.source_record_id,
            "evidence_item_id": e1.evidence_item_id,
            "observation_status": "present",
        },
    ]
    v3_partitions = [
        {
            "partition_key": "all",
            "partition_status": "expected-received",
            "expected_record_count": 3,
            "received_record_count": 3,
            "received_content_sha256": sha256(b"public-v3"),
        }
    ]
    v4_partitions = [
        {
            "partition_key": "all",
            "partition_status": "expected-missing",
            "expected_record_count": 1,
            "received_record_count": 0,
            "received_content_sha256": None,
        }
    ]
    v2_id = conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE dataset_id='dataset:public-markets' AND version_label='v2'"
    ).fetchone()[0]
    v3 = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            "dataset:public-markets",
            "v3",
            right_id,
            None,
            None,
            may,
            None,
            "5" * 64,
            "delta",
            "explicit-tombstone-only",
            "complete",
            expected_partition_manifest(v3_partitions),
            received_partition_manifest(v3_partitions),
            1,
            1,
            reconstruction_manifest(delta_rows),
            3,
            v2_id,
            v2_id,
        ),
    )
    v4 = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            "dataset:public-markets",
            "v4",
            right_id,
            None,
            None,
            june,
            None,
            "7" * 64,
            "full-snapshot",
            "full-snapshot-means-removed",
            "incomplete",
            expected_partition_manifest(v4_partitions),
            received_partition_manifest(v4_partitions),
            1,
            0,
            None,
            None,
            v3.dataset_version_id,
        ),
    )
    ingest_dataset_versions(conn, [v3, v4])
    c1_id = machine_id("evidence", {"source_record_id": existing_sources["C"], "version": 1})
    observations = [
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord("", v3.dataset_version_id, b3.evidence_item_id, "present"),
        ),
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord(
                "",
                v3.dataset_version_id,
                c1_id,
                "explicitly-removed",
                "source-tombstone",
            ),
        ),
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord("", v3.dataset_version_id, e1.evidence_item_id, "present"),
        ),
    ]
    ingest_dataset_observations(conn, observations)
    version_rows = tuple(
        conn.execute(
            "SELECT dataset_version_id,version_label FROM dataset_version WHERE dataset_id='dataset:public-markets' ORDER BY version_label"
        )
    )
    partitions = [
        with_machine_id(
            "dataset-partition",
            DatasetDeliveryPartitionRecord(
                "",
                version_id,
                "all",
                "expected-received",
                manifest_item.evidence_item_id,
                manifest_span.evidence_span_id,
                sha256(f"public-{label}".encode()),
                3,
                3,
            ),
        )
        for version_id, label in version_rows
        if label != "v4"
    ]
    partitions.append(
        with_machine_id(
            "dataset-partition",
            DatasetDeliveryPartitionRecord(
                "",
                v4.dataset_version_id,
                "all",
                "expected-missing",
                manifest_item.evidence_item_id,
                manifest_span.evidence_span_id,
                None,
                1,
                0,
            ),
        )
    )
    ingest_dataset_delivery_partitions(conn, partitions)
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    observation.dataset_observation_id,
                    next(
                        p.dataset_delivery_partition_id
                        for p in partitions
                        if p.dataset_version_id == v3.dataset_version_id
                    ),
                ),
            )
            for observation in observations
        ],
    )
    _add_projection_matrix(conn)


def build_s7_public_market_sources(conn):
    """Author the four strict, point-in-time S7 liquid-source datasets."""

    from .s7 import (
        S7_RELATIONSHIP_FIELDS,
        _ingest_s7_dataset,
        s7_provisional_relationship_items,
    )

    early = datetime(2024, 3, 15, tzinfo=UTC)
    latest = datetime(2024, 9, 15, tzinfo=UTC)
    periodic_fields = (
        "source_product_key",
        "period_end",
        "return_value",
        "return_kind",
        "gross_net",
        "currency",
        "frequency",
        "calendar",
        "management_fee_basis",
        "incentive_fee_basis",
        "benchmark_id",
        "benchmark_version",
        "benchmark_convention",
        "valuation_policy_id",
        "cashflow_convention",
    )

    def periodic_item(
        source_key,
        product_key,
        period_end,
        value,
        *,
        version=1,
        available_at=early,
        gross_net="net",
        currency="USD",
        management_fee_basis="net-of-management-fees",
        incentive_fee_basis="net-of-incentive-fees",
        benchmark_id="benchmark:s7-public",
        benchmark_version="v1",
        return_kind="total-return",
    ):
        values = (
            product_key,
            period_end,
            value,
            return_kind,
            gross_net,
            currency,
            "monthly",
            "calendar-month-end",
            management_fee_basis,
            incentive_fee_basis,
            benchmark_id,
            benchmark_version,
            "total-return",
            "valuation-policy:s7-liquid-v1",
            "time-weighted-no-external-flows",
        )
        return {
            "source_key": source_key,
            "record_kind": "s7-periodic-return",
            "payload": dict(zip(periodic_fields, values, strict=True)),
            "version": version,
            "available_at": available_at,
            "effective_at": datetime.fromisoformat(period_end.replace("Z", "+00:00")),
            "source_entity_type": "product",
            "base_currency": currency,
            "gross_net_fee_basis": gross_net,
            "valuation_policy_id": "valuation-policy:s7-liquid-v1",
            "benchmark_id": benchmark_id,
            "benchmark_version": benchmark_version,
        }

    public_items = [
        periodic_item("s7-public-main:2024-01", "s7-public-main", "2024-01-31T00:00:00Z", "0.0120"),
        periodic_item("s7-public-main:2024-02", "s7-public-main", "2024-02-29T00:00:00Z", "-0.0040"),
        periodic_item("s7-public-main:2024-03", "s7-public-main", "2024-03-31T00:00:00Z", "0.0090"),
        periodic_item("s7-public-eur", "s7-public-eur", "2024-02-29T00:00:00Z", "0.0060", currency="EUR"),
        periodic_item("s7-public-benchmark-v1", "s7-public-main", "2024-02-29T00:00:00Z", "0.0040", benchmark_version="v1"),
        periodic_item("s7-public-benchmark-v2", "s7-public-main", "2024-02-29T00:00:00Z", "0.0040", benchmark_version="v2"),
        periodic_item("s7-null-same-label", "s7-null-same-label", "2024-02-29T00:00:00Z", "0.0010"),
        periodic_item("s7-public-no-archive", "s7-public-no-archive", "2024-02-29T00:00:00Z", "0.0020"),
    ]
    public_relationship_items = s7_provisional_relationship_items("public-equity", early)
    public_items.extend(public_relationship_items)
    public = _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-public-registered",
        label="S7 registered public returns",
        source_system="synthetic-public-record",
        availability_policy="public-publication",
        access_context="public",
        licence_purpose="s7-research",
        schemas=(
            ("schema:s7-periodic-return-v1", "s7-periodic-return", periodic_fields),
            (
                "schema:s7-relationship-evidence-v1",
                "s7-relationship-evidence",
                S7_RELATIONSHIP_FIELDS,
            ),
        ),
        items=public_items,
        versions=(
            {
                "version_label": "early",
                "available_at": early,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": tuple((row["source_key"], 1, "present", None) for row in public_items),
            },
            {
                "version_label": "latest",
                "available_at": latest,
                "delivery_mode": "delta",
                "absence_semantics": "explicit-tombstone-only",
                "observations": tuple(
                    (
                        row["source_key"],
                        1,
                        "explicitly-removed",
                        "superseded-by-x3-reviewed-lineage",
                    )
                    for row in public_relationship_items
                ),
            },
        ),
    )

    hedge_items = [
        periodic_item("s7-hf-main:2024-01", "s7-hf-main", "2024-01-31T00:00:00Z", "0.0060"),
        periodic_item("s7-hf-main:2024-02", "s7-hf-main", "2024-02-29T00:00:00Z", "0.0100"),
        periodic_item("s7-hf-main:2024-02", "s7-hf-main", "2024-02-29T00:00:00Z", "0.0080", version=2, available_at=latest),
        periodic_item("s7-hf-main:2024-03", "s7-hf-main", "2024-03-31T00:00:00Z", "-0.0030"),
        periodic_item("s7-hf-closed:2023-12", "s7-hf-closed", "2023-12-31T00:00:00Z", "0.0040", available_at=latest),
        periodic_item("s7-hf-not-inferable", "s7-hf-not-inferable", "2024-02-29T00:00:00Z", "0.0020"),
        periodic_item("s7-hf-inherited", "s7-hf-inherited", "2024-02-29T00:00:00Z", "0.0030"),
        periodic_item("s7-hf-tombstoned", "s7-hf-tombstoned", "2024-02-29T00:00:00Z", "0.0040"),
        periodic_item("s7-hf-retro-member", "s7-hf-retro-member", "2024-01-31T00:00:00Z", "0.0025"),
        periodic_item("s7-hf-ambiguous", "s7-hf-ambiguous", "2024-02-29T00:00:00Z", "0.0015"),
        periodic_item("s7-null-same-label", "s7-null-same-label", "2024-02-29T00:00:00Z", "0.0010"),
        periodic_item("s7-hf-overlap", "s7-hf-overlap", "2024-02-29T00:00:00Z", "0.0020"),
        periodic_item("s7-hf-gross-break", "s7-hf-gross-break", "2024-02-29T00:00:00Z", "0.0150", gross_net="gross"),
        periodic_item("s7-hf-fee-unresolved", "s7-hf-fee-unresolved", "2024-02-29T00:00:00Z", "0.0070", management_fee_basis=""),
    ]
    early_hedge_keys = (
        "s7-hf-main:2024-01",
        "s7-hf-main:2024-02",
        "s7-hf-main:2024-03",
        "s7-hf-inherited",
        "s7-hf-tombstoned",
        "s7-hf-retro-member",
        "s7-hf-ambiguous",
        "s7-null-same-label",
        "s7-hf-overlap",
        "s7-hf-gross-break",
        "s7-hf-fee-unresolved",
    )
    hedge = _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-hedge-composite",
        label="S7 hedge composite returns",
        source_system="synthetic-manager-delivery",
        availability_policy="manager-receipt",
        access_context="shortlisted-nda",
        licence_purpose="s7-research",
        schemas=(("schema:s7-periodic-return-v1", "s7-periodic-return", periodic_fields),),
        items=hedge_items,
        versions=(
            {
                "version_label": "early",
                "available_at": early,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": tuple((key, 1, "present", None) for key in early_hedge_keys),
            },
            {
                "version_label": "latest",
                "available_at": latest,
                "delivery_mode": "delta",
                "absence_semantics": "explicit-tombstone-only",
                "observations": (
                    ("s7-hf-main:2024-02", 2, "present", None),
                    ("s7-hf-closed:2023-12", 1, "present", None),
                    ("s7-hf-tombstoned", 1, "explicitly-removed", "manager-withdrawal"),
                ),
            },
        ),
    )

    fx_fields = (
        "series_id",
        "period_end",
        "fx_return",
        "base_currency",
        "quote_currency",
        "quotation_direction",
        "hedge_treatment",
        "rule_id",
    )
    fx_items = []
    for version, value, available_at in ((1, "0.0200", early), (2, "0.0180", latest)):
        fx_items.append(
            {
                "source_key": "s7-fx-eur-usd:2024-02",
                "record_kind": "s7-fx-return",
                "payload": dict(
                    zip(
                        fx_fields,
                        ("s7-fx-eur-usd", "2024-02-29T00:00:00Z", value, "EUR", "USD", "base-per-quote", "unhedged", "s7-fx-rule-v1"),
                        strict=True,
                    )
                ),
                "version": version,
                "available_at": available_at,
                "effective_at": datetime(2024, 2, 29, tzinfo=UTC),
                "source_entity_type": "fx-series",
            }
        )
    fx = _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-fx",
        label="S7 public FX returns",
        source_system="synthetic-public-record",
        availability_policy="public-publication",
        access_context="public",
        licence_purpose="s7-research",
        schemas=(("schema:s7-fx-return-v1", "s7-fx-return", fx_fields),),
        items=fx_items,
        versions=tuple(
            {
                "version_label": label,
                "available_at": available_at,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": (("s7-fx-eur-usd:2024-02", version, "present", None),),
            }
            for label, version, available_at in (("early", 1, early), ("latest", 2, latest))
        ),
    )

    benchmark_fields = (
        "benchmark_id",
        "benchmark_version",
        "period_end",
        "return_value",
        "return_convention",
        "currency",
        "frequency",
        "calendar",
    )
    benchmark_items = []
    for version, value in (("v1", "0.0030"), ("v2", "0.0035")):
        benchmark_items.append(
            {
                "source_key": f"s7-public-benchmark-{version}",
                "record_kind": "s7-benchmark-return",
                "payload": dict(zip(benchmark_fields, ("benchmark:s7-public", version, "2024-02-29T00:00:00Z", value, "total-return", "USD", "monthly", "calendar-month-end"), strict=True)),
                "available_at": early,
                "effective_at": datetime(2024, 2, 29, tzinfo=UTC),
                "source_entity_type": "benchmark",
            }
        )
    benchmark = _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-benchmark",
        label="S7 versioned public benchmark",
        source_system="synthetic-public-record",
        availability_policy="public-publication",
        access_context="public",
        licence_purpose="s7-research",
        schemas=(("schema:s7-benchmark-return-v1", "s7-benchmark-return", benchmark_fields),),
        items=benchmark_items,
        versions=(
            {
                "version_label": "early",
                "available_at": early,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": tuple((row["source_key"], 1, "present", None) for row in benchmark_items),
            },
        ),
    )
    return {"public": public, "hedge": hedge, "fx": fx, "benchmark": benchmark}


def _add_projection_matrix(conn) -> None:
    item_id = conn.execute(
        "SELECT i.evidence_item_id FROM evidence_item i JOIN source_record s USING(source_record_id) WHERE s.dataset_id='dataset:public-markets' AND s.source_record_key='A' AND i.version=1"
    ).fetchone()[0]
    version_id = conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE dataset_id='dataset:public-markets' AND version_label='v1'"
    ).fetchone()[0]
    observation_id = conn.execute(
        "SELECT o.dataset_observation_id FROM dataset_observation o JOIN evidence_item i USING(evidence_item_id) JOIN source_record s USING(source_record_id) WHERE o.dataset_version_id=? AND s.source_record_key='A'",
        (version_id,),
    ).fetchone()[0]
    span_id = machine_id(
        "span",
        {
            "evidence_item_id": item_id,
            "json_pointer": "/label",
            "start_char": 0,
            "end_char": 1,
            "span_sha256": sha256(b"A"),
        },
    )

    def mapping_id(key: str, label: str) -> str:
        return machine_id(
            "mapping",
            {
                "source_evidence_item_id": item_id,
                "source_key": key,
                "source_label": label,
                "taxonomy_version": "v1",
                "version": 1,
                "candidate_entity_ids_json": "[]",
            },
        )

    mapping_a = mapping_id("A", "A")
    mapping_unresolved = mapping_id("A-unresolved", "A unresolved")
    membership_a = machine_id(
        "membership",
        {
            "source_evidence_item_id": item_id,
            "entity_mapping_id": mapping_a,
            "dataset_version_id": version_id,
            "membership_status": "active",
            "taxonomy_version": "v1",
            "temporal_type": "interval",
            "effective_at": None,
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
            "version": 1,
        },
    )
    grid_id = machine_id(
        "grid",
        {
            "source_evidence_item_id": item_id,
            "source_label": "Public opportunity grid",
            "taxonomy_version": "v1",
            "denominator_rule": "all-products",
            "version": 1,
        },
    )
    grid_a = machine_id(
        "grid-cell",
        {
            "target_grid_id": grid_id,
            "dimensions_json": '{"segment":"public"}',
            "eligibility_status": "eligible",
            "exclusion_reason": None,
        },
    )
    grid_excluded = machine_id(
        "grid-cell",
        {
            "target_grid_id": grid_id,
            "dimensions_json": '{"segment":"unresolved"}',
            "eligibility_status": "excluded",
            "exclusion_reason": "outside-target-grid",
        },
    )
    funnel_schema = machine_id(
        "funnel-schema",
        {
            "source_evidence_item_id": item_id,
            "stage_dictionary_json": '["accepted","rejected"]',
            "transition_rules_json": '[["accepted","rejected"]]',
            "reason_dictionary_json": '["accepted","not-accepted"]',
            "completeness_status": "complete",
            "version": 1,
        },
    )

    def opportunity_id(suffix: str, mapping: str) -> str:
        return machine_id(
            "funnel-opportunity",
            {
                "source_evidence_item_id": item_id,
                "evidence_span_id": span_id,
                "entity_mapping_id": mapping,
                "source_opportunity_key": f"opportunity-{suffix}",
                "product_entity_id": "manager:aster-quay",
                "entity_grain": "product",
                "temporal_type": "point",
                "effective_at": "2024-01-10T00:00:00.000000Z",
                "effective_from": None,
                "effective_to": None,
                "version": 1,
            },
        )

    conn.execute(
        "INSERT INTO evidence_span VALUES (?,?,?,?,?,?)",
        (span_id, item_id, "/label", 0, 1, sha256(b"A")),
    )
    common = (item_id, span_id, version_id, observation_id)
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mapping_a,
            *common,
            "A",
            "A",
            "product",
            "manager:aster-quay",
            "resolved",
            "[]",
            "exact",
            "v1",
            "point",
            "2024-01-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO universe_membership VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            membership_a,
            *common,
            mapping_a,
            "active",
            "v1",
            "interval",
            None,
            "2024-01-01T00:00:00.000000Z",
            None,
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mapping_unresolved,
            *common,
            "A-unresolved",
            "A unresolved",
            "product",
            None,
            "unresolved",
            "[]",
            "unresolved-source",
            "v1",
            "point",
            "2024-01-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO target_grid VALUES (?,?,?,?,?,?,?,?,?,?)",
        (grid_id, *common, "Public opportunity grid", "v1", "all-products", 1, None),
    )
    conn.execute(
        "INSERT INTO target_grid_cell VALUES (?,?,?,?,?)",
        (grid_a, grid_id, '{"segment":"public"}', "eligible", None),
    )
    conn.execute(
        "INSERT INTO target_grid_cell VALUES (?,?,?,?,?)",
        (
            grid_excluded,
            grid_id,
            '{"segment":"unresolved"}',
            "excluded",
            "outside-target-grid",
        ),
    )
    for suffix, legal in (("one", "legal-entity:aster-one"), ("two", "legal-entity:aster-two")):
        conn.execute(
            "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                machine_id(
                    "entity-relation",
                    {
                        "source_evidence_item_id": item_id,
                        "relation_type": "advises",
                        "source_entity_id": "adviser:northglass",
                        "target_entity_id": legal,
                        "temporal_type": "interval",
                        "effective_at": None,
                        "effective_from": "2024-01-01T00:00:00.000000Z",
                        "effective_to": None,
                        "version": 1,
                    },
                ),
                *common,
                "advises",
                "adviser:northglass",
                legal,
                "interval",
                None,
                "2024-01-01T00:00:00.000000Z",
                None,
                1,
                None,
            ),
        )
    conn.execute(
        "INSERT INTO funnel_schema VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            funnel_schema,
            *common,
            '["accepted","rejected"]',
            '[["accepted","rejected"]]',
            '["accepted","not-accepted"]',
            "complete",
            1,
            None,
        ),
    )
    for suffix, mapping in (
        ("one", mapping_a),
        ("two", mapping_a),
        ("three", mapping_unresolved),
    ):
        conn.execute(
            "INSERT INTO funnel_opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                opportunity_id(suffix, mapping),
                *common,
                mapping,
                f"opportunity-{suffix}",
                f"Opportunity {suffix}",
                "product",
                "manager:aster-quay",
                "point",
                "2024-01-10T00:00:00.000000Z",
                None,
                None,
                1,
                None,
            ),
        )
    for suffix, status, mapping, grid_cell in (
        ("one", "accepted", mapping_a, grid_a),
        ("two", "rejected", mapping_a, grid_a),
        ("three", "accepted", mapping_unresolved, grid_excluded),
    ):
        conn.execute(
            "INSERT INTO funnel_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                machine_id(
                    "funnel-event",
                    {
                        "funnel_opportunity_id": opportunity_id(suffix, mapping),
                        "funnel_schema_id": funnel_schema,
                        "source_evidence_item_id": item_id,
                        "entity_mapping_id": mapping,
                        "funnel_stage": status,
                        "reason_code": status,
                        "effective_at": "2024-01-10T00:00:00.000000Z",
                        "version": 1,
                    },
                ),
                *common,
                mapping,
                grid_cell,
                opportunity_id(suffix, mapping),
                funnel_schema,
                status,
                status,
                status,
                "2024-01-10T00:00:00.000000Z",
                1,
                None,
            ),
        )
    for suffix, complete, accepted_only, start, end, censor in (
        (
            "accepted-only",
            "complete",
            1,
            "2024-01-01T00:00:00.000000Z",
            "2024-02-01T00:00:00.000000Z",
            "right-censor",
        ),
        (
            "all-wide",
            "complete",
            0,
            "2024-01-01T00:00:00.000000Z",
            "2024-04-01T00:00:00.000000Z",
            "right-censor",
        ),
        (
            "incomplete",
            "incomplete",
            0,
            "2024-01-01T00:00:00.000000Z",
            "2024-04-01T00:00:00.000000Z",
            "right-censor",
        ),
        (
            "incomplete-window",
            "complete",
            0,
            "2024-04-01T00:00:00.000000Z",
            "2024-04-01T00:00:00.000000Z",
            "right-censor",
        ),
        (
            "undefined-censor",
            "complete",
            0,
            "2024-01-01T00:00:00.000000Z",
            "2024-04-01T00:00:00.000000Z",
            "undefined",
        ),
    ):
        conn.execute(
            "INSERT INTO funnel_cohort VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                machine_id(
                    "funnel-cohort",
                    {
                        "source_evidence_item_id": item_id,
                        "funnel_schema_id": funnel_schema,
                        "cohort_label": suffix,
                        "inclusion_rule_json": "{}",
                        "exclusion_rule_json": "{}",
                        "entity_grain": "product",
                        "entry_stage": "accepted",
                        "outcome_stage": "accepted",
                        "accepted_only": accepted_only,
                        "entry_window_from": start,
                        "entry_window_to": end,
                        "observation_window_end": end,
                        "completeness_status": complete,
                        "absence_rule": "no-outcome-observed",
                        "censor_policy": censor,
                        "right_censor_at": end,
                        "version": 1,
                    },
                ),
                *common,
                funnel_schema,
                suffix,
                "{}",
                "{}",
                "product",
                "accepted",
                "accepted",
                accepted_only,
                start,
                end,
                end,
                complete,
                "no-outcome-observed",
                censor,
                end,
                1,
                None,
            ),
        )


PUBLIC_MARKET_SHAPES = (
    {"record_kind": "monthly-return", "fields": ("period_end", "gross_return", "net_return")},
    {"record_kind": "liquidity-bucket", "fields": ("bucket", "weight", "as_of_date")},
)
