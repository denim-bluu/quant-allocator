PRIVATE_MARKET_SHAPES = (
    {"record_kind": "capital-call", "fields": ("notice_date", "due_date", "amount", "currency")},
    {"record_kind": "distribution", "fields": ("event_date", "amount", "currency")},
    {
        "record_kind": "quarterly-nav",
        "fields": ("as_of_date", "nav", "unfunded", "valuation_policy_version"),
    },
)


def build_private_markets_fixture(conn) -> None:
    from datetime import UTC, date, datetime

    from ..ingest import (
        expected_partition_manifest,
        ingest_dataset_delivery_partitions,
        ingest_dataset_observation_partition_links,
        ingest_dataset_observations,
        ingest_dataset_versions,
        ingest_items,
        received_partition_manifest,
        reconstruction_manifest,
    )
    from ..model import (
        DatasetDeliveryPartitionRecord,
        DatasetObservationPartitionLinkRecord,
        DatasetObservationRecord,
        DatasetVersionRecord,
        EvidenceItemRecord,
        canonical_bytes,
        machine_id,
        sha256,
        with_machine_id,
    )
    from .core import add_fact_dataset, build_core_fixture

    build_core_fixture(conn)
    add_fact_dataset(
        conn,
        slug="private-markets",
        facts=(
            {"label": "call-one", "record_kind": "capital-call", "value": 10_000_000},
            {"label": "distribution-one", "record_kind": "distribution", "value": 4_000_000},
            {"label": "nav-one", "record_kind": "quarterly-nav", "value": 85_000_000},
        ),
    )
    revised_at = datetime(2024, 7, 15, tzinfo=UTC)
    source_rows = tuple(
        conn.execute(
            "SELECT source_record_id,source_record_key FROM source_record WHERE dataset_id='dataset:private-markets' ORDER BY source_record_key"
        )
    )
    source_ids = {row[1]: row[0] for row in source_rows}
    right_id = conn.execute(
        "SELECT evidence_right_id FROM evidence_right WHERE dataset_id='dataset:private-markets'"
    ).fetchone()[0]
    prior_version_id = conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE dataset_id='dataset:private-markets' AND version_label='v1'"
    ).fetchone()[0]
    payload = {"label": "nav-one", "record_kind": "quarterly-nav", "value": 80_000_000}
    nav_source_id = source_ids["nav-one"]
    revised = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right_id,
            nav_source_id,
            sha256(canonical_bytes(payload)),
            "quarterly-nav",
            "schema:generic-v1",
            "point",
            revised_at,
            None,
            None,
            date(2024, 3, 31),
            None,
            None,
            revised_at,
            None,
            2,
            machine_id("evidence", {"source_record_id": nav_source_id, "version": 1}),
            "received",
            "shortlisted-nda",
            "v1",
            "nda",
            "research",
            payload,
        ),
    )
    ingest_items(conn, [revised])
    rows = [
        {
            "source_record_id": source_id,
            "evidence_item_id": machine_id(
                "evidence",
                {"source_record_id": source_id, "version": 2 if source_id == nav_source_id else 1},
            ),
            "observation_status": "present",
        }
        for source_id in (source_ids["call-one"], source_ids["distribution-one"], nav_source_id)
    ]
    content_hash = sha256(b"private-markets-v2")
    partitions = [
        {
            "partition_key": "all",
            "partition_status": "expected-received",
            "expected_record_count": 3,
            "received_record_count": 3,
            "received_content_sha256": content_hash,
        }
    ]
    version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            "dataset:private-markets",
            "v2",
            right_id,
            None,
            None,
            revised_at,
            None,
            content_hash,
            "full-snapshot",
            "not-inferable",
            "complete",
            expected_partition_manifest(partitions),
            received_partition_manifest(partitions),
            1,
            1,
            reconstruction_manifest(rows),
            3,
            prior_version_id,
        ),
    )
    ingest_dataset_versions(conn, [version])
    observations = [
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord(
                "",
                version.dataset_version_id,
                row["evidence_item_id"],
                "present",
            ),
        )
        for row in rows
    ]
    ingest_dataset_observations(conn, observations)
    manifest = conn.execute(
        "SELECT evidence_item_id FROM evidence_item JOIN source_record USING(source_record_id) WHERE dataset_id='dataset:private-markets' AND source_record_key='MANIFEST'"
    ).fetchone()[0]
    span = conn.execute(
        "SELECT evidence_span_id FROM evidence_span WHERE evidence_item_id=?", (manifest,)
    ).fetchone()[0]
    partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            version.dataset_version_id,
            "all",
            "expected-received",
            manifest,
            span,
            content_hash,
            3,
            3,
        ),
    )
    ingest_dataset_delivery_partitions(conn, [partition])
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    observation.dataset_observation_id,
                    partition.dataset_delivery_partition_id,
                ),
            )
            for index, observation in enumerate(observations, 1)
        ],
    )


def build_s7_private_market_sources(conn):
    """Author irregular S7 private cash flows and versioned quarterly NAV."""

    from datetime import UTC, datetime

    from .s7 import (
        S7_RELATIONSHIP_FIELDS,
        _ingest_s7_dataset,
        s7_provisional_relationship_items,
    )

    early = datetime(2024, 3, 31, 12, tzinfo=UTC)
    latest = datetime(2024, 8, 15, tzinfo=UTC)
    cashflow_fields = (
        "source_product_key",
        "event_id",
        "event_date",
        "event_kind",
        "amount",
        "currency",
        "recallable",
        "fee_expense_treatment",
        "cashflow_convention",
    )
    nav_fields = (
        "source_product_key",
        "valuation_date",
        "nav",
        "currency",
        "valuation_policy_id",
        "published_at",
        "frequency",
        "calendar",
    )

    def cashflow(source_key, event_id, event_date, event_kind, amount, treatment):
        return {
            "source_key": source_key,
            "record_kind": "s7-private-cashflow",
            "payload": dict(
                zip(
                    cashflow_fields,
                    (
                        "s7-private-main",
                        event_id,
                        event_date,
                        event_kind,
                        amount,
                        "USD",
                        "false",
                        treatment,
                        "investor-perspective-signed-cashflow",
                    ),
                    strict=True,
                )
            ),
            "available_at": early,
            "effective_at": datetime.fromisoformat(f"{event_date}T00:00:00+00:00"),
            "source_entity_type": "product",
            "base_currency": "USD",
        }

    items = [
        cashflow("s7-private-call", "call-001", "2024-01-17", "capital-call", "-12000000.00", "included-as-capital"),
        cashflow("s7-private-distribution", "distribution-001", "2024-03-08", "distribution", "3500000.00", "included-as-distribution"),
        cashflow("s7-private-fee", "fee-001", "2024-02-12", "fee-expense", "-175000.00", "included-as-fee-expense"),
    ]
    for version, nav, available_at in (
        (1, "85000000.00", early),
        (2, "80000000.00", latest),
    ):
        items.append(
            {
                "source_key": "s7-private-nav:2024-03-31",
                "record_kind": "s7-private-nav",
                "payload": dict(
                    zip(
                        nav_fields,
                        (
                            "s7-private-main",
                            "2024-03-31",
                            nav,
                            "USD",
                            "valuation-policy:s7-private-quarterly-v1",
                            available_at.isoformat().replace("+00:00", "Z"),
                            "quarterly",
                            "calendar-quarter-end",
                        ),
                        strict=True,
                    )
                ),
                "version": version,
                "available_at": available_at,
                "effective_at": datetime(2024, 3, 31, tzinfo=UTC),
                "source_entity_type": "product",
                "base_currency": "USD",
                "valuation_policy_id": "valuation-policy:s7-private-quarterly-v1",
            }
        )
    relationship_items = s7_provisional_relationship_items("private-market", early)
    items.extend(relationship_items)
    early_rows = tuple((str(row["source_key"]), 1, "present", None) for row in items if int(row.get("version", 1)) == 1)
    latest_rows = (
        ("s7-private-nav:2024-03-31", 2, "present", None),
        *(
            (
                row["source_key"],
                1,
                "explicitly-removed",
                "superseded-by-x3-reviewed-lineage",
            )
            for row in relationship_items
        ),
    )
    return _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-private-cashflow-nav",
        label="S7 irregular private cash flows and NAV",
        source_system="synthetic-partnership-delivery",
        availability_policy="manager-receipt",
        access_context="funded-private-partnership",
        licence_purpose="s7-research",
        schemas=(
            ("schema:s7-private-cashflow-v1", "s7-private-cashflow", cashflow_fields),
            ("schema:s7-private-nav-v1", "s7-private-nav", nav_fields),
            (
                "schema:s7-relationship-evidence-v1",
                "s7-relationship-evidence",
                S7_RELATIONSHIP_FIELDS,
            ),
        ),
        items=items,
        versions=(
            {
                "version_label": "early",
                "available_at": early,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": early_rows,
            },
            {
                "version_label": "latest",
                "available_at": latest,
                "delivery_mode": "delta",
                "absence_semantics": "explicit-tombstone-only",
                "observations": latest_rows,
            },
        ),
    )
