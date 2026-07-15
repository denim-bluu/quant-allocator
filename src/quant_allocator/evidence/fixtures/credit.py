CREDIT_SHAPES = (
    {
        "record_kind": "facility",
        "fields": ("borrower_key", "facility_key", "commitment", "currency"),
    },
    {"record_kind": "covenant", "fields": ("definition_version", "threshold", "test_date")},
    {"record_kind": "cash-event", "fields": ("event_date", "principal", "interest", "currency")},
)


def build_credit_fixture(conn) -> None:
    from .core import add_fact_dataset, build_core_fixture

    build_core_fixture(conn)
    add_fact_dataset(
        conn,
        slug="credit",
        facts=(
            {"label": "facility-one", "record_kind": "facility", "value": 125_000_000},
            {"label": "covenant-one", "record_kind": "covenant", "value": 4.5},
            {"label": "cash-event-one", "record_kind": "cash-event", "value": 2_500_000},
        ),
    )


def build_s7_credit_sources(conn):
    """Author monthly-liquid and quarterly-valued S7 credit observations."""

    from datetime import UTC, datetime

    from .s7 import (
        S7_RELATIONSHIP_FIELDS,
        _ingest_s7_dataset,
        s7_provisional_relationship_items,
    )

    early = datetime(2024, 3, 15, tzinfo=UTC)
    latest = datetime(2024, 9, 15, tzinfo=UTC)
    fields = (
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
        "income_treatment",
        "price_treatment",
        "default_recovery_treatment",
        "cash_treatment",
        "duration_convention",
    )

    def item(source_key, period_end, value, frequency, return_kind, valuation_policy):
        values = (
            source_key,
            period_end,
            value,
            return_kind,
            "net",
            "USD",
            frequency,
            "calendar-period-end",
            "net-of-management-fees",
            "not-applicable",
            "benchmark:s7-credit",
            "v1",
            "total-return",
            valuation_policy,
            "time-weighted-no-external-flows",
            "reinvested",
            "marked-to-market" if frequency == "monthly" else "quarterly-valuation",
            "included-when-realized",
            "included",
            "modified-duration",
        )
        return {
            "source_key": source_key,
            "record_kind": "s7-credit-return",
            "payload": dict(zip(fields, values, strict=True)),
            "available_at": early,
            "effective_at": datetime.fromisoformat(period_end.replace("Z", "+00:00")),
            "source_entity_type": "product",
            "base_currency": "USD",
            "gross_net_fee_basis": "net",
            "valuation_policy_id": valuation_policy,
            "benchmark_id": "benchmark:s7-credit",
            "benchmark_version": "v1",
        }

    return_items = (
        item(
            "s7-credit-liquid",
            "2024-02-29T00:00:00Z",
            "0.0060",
            "monthly",
            "total-return",
            "valuation-policy:s7-credit-daily-v1",
        ),
        item(
            "s7-credit-private",
            "2024-03-31T00:00:00Z",
            "0.0140",
            "quarterly",
            "valuation-based-change",
            "valuation-policy:s7-credit-quarterly-v1",
        ),
    )
    relationship_items = s7_provisional_relationship_items("credit", early)
    items = (*return_items, *relationship_items)
    return _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-credit-lineage",
        label="S7 native-frequency credit lineage",
        source_system="synthetic-manager-delivery",
        availability_policy="manager-receipt",
        access_context="segregated-mandate",
        licence_purpose="s7-research",
        schemas=(
            ("schema:s7-credit-return-v1", "s7-credit-return", fields),
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
                "observations": tuple((row["source_key"], 1, "present", None) for row in items),
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
                    for row in relationship_items
                ),
            },
        ),
    )
