from quant_allocator.evidence.checks import EvidenceRefusal
from datetime import UTC, datetime

import pytest

from quant_allocator.evidence.fixtures.credit import CREDIT_SHAPES, build_credit_fixture
from quant_allocator.evidence.fixtures.core import core_right_id
from quant_allocator.evidence.fixtures.private_markets import (
    PRIVATE_MARKET_SHAPES,
    build_private_markets_fixture,
)
from quant_allocator.evidence.fixtures.public_markets import (
    PUBLIC_MARKET_SHAPES,
    build_public_markets_fixture,
)
from quant_allocator.evidence.fixtures.terms import TERMS_SHAPES, build_terms_fixture
from quant_allocator.evidence.ingest import reconstruct_dataset_version
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.model import DatasetSliceRequest
from quant_allocator.evidence.snapshot import as_known_slice
from quant_allocator.evidence.projections import (
    evaluate_funnel_cohort,
    project_funnel_opportunities,
)


def test_delivery_matrix_has_complete_full_complete_delta_and_incomplete_full() -> None:
    conn = connect()
    initialize(conn)
    build_public_markets_fixture(conn)
    matrix = [
        tuple(row)
        for row in conn.execute(
            "SELECT delivery_mode,completeness_status FROM dataset_version ORDER BY rowid"
        )
    ]
    assert matrix == [
        ("full-snapshot", "complete"),
        ("full-snapshot", "complete"),
        ("delta", "complete"),
        ("full-snapshot", "incomplete"),
    ]
    v3_id = conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE version_label='v3'"
    ).fetchone()[0]
    reconstructed = reconstruct_dataset_version(conn, v3_id)
    keys = [
        conn.execute(
            "SELECT source_record_key FROM source_record WHERE source_record_id=?",
            (row["source_record_id"],),
        ).fetchone()[0]
        for row in reconstructed.rows
    ]
    assert sorted(keys) == ["A", "B", "E"]
    v4_id = conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE version_label='v4'"
    ).fetchone()[0]
    try:
        reconstruct_dataset_version(conn, v4_id)
    except EvidenceRefusal as exc:
        assert exc.code == "incomplete-dataset-version"
    else:
        raise AssertionError("incomplete full snapshot advertised reconstruction")
    incomplete = conn.execute(
        "SELECT reconstruction_manifest_sha256,reconstruction_row_count FROM dataset_version WHERE dataset_version_id=?",
        (v4_id,),
    ).fetchone()
    assert tuple(incomplete) == (None, None)


def test_shared_source_shapes_are_deterministic_contractual_facts_only() -> None:
    shapes = PUBLIC_MARKET_SHAPES + CREDIT_SHAPES + PRIVATE_MARKET_SHAPES + TERMS_SHAPES
    assert len({row["record_kind"] for row in shapes}) == len(shapes)
    assert all(tuple(sorted(row)) == ("fields", "record_kind") for row in shapes)
    assert all(
        "score" not in field and "forecast" not in field
        for row in shapes
        for field in row["fields"]
    )


def test_multi_asset_fixture_modules_are_order_deterministic_and_emit_real_value_divergence() -> (
    None
):
    def build(order):
        conn = connect()
        initialize(conn)
        for builder in order:
            builder(conn)
        return conn

    builders = (build_credit_fixture, build_private_markets_fixture, build_terms_fixture)
    first = build(builders)
    second = build(tuple(reversed(builders)))
    digests = []
    for slug in ("credit", "private-markets", "terms"):
        request = DatasetSliceRequest(
            f"dataset:{slug}", "shortlisted-nda", core_right_id(slug), "research"
        )
        left = as_known_slice(first, decision_at=datetime(2024, 5, 1, tzinfo=UTC), request=request)
        right = as_known_slice(
            second, decision_at=datetime(2024, 5, 1, tzinfo=UTC), request=request
        )
        assert left.digest == right.digest
        digests.append((slug, tuple(row["payload"]["value"] for row in left.rows)))
    assert dict(digests)["credit"] != dict(digests)["private-markets"]


def test_fixture_funnel_and_denominator_matrix_covers_l42_to_l45() -> None:
    conn = connect()
    initialize(conn)
    build_public_markets_fixture(conn)
    request = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    snapshot = as_known_slice(conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=request)
    assert len(project_funnel_opportunities(conn, snapshot)) == 3
    assert conn.execute("SELECT count(*) FROM entity_mapping").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM universe_membership").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM target_grid_cell").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM entity_relationship").fetchone()[0] == 2
    cohort_ids = dict(conn.execute("SELECT cohort_label,funnel_cohort_id FROM funnel_cohort"))
    accepted = evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=cohort_ids["accepted-only"])
    wide = evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=cohort_ids["all-wide"])
    assert sorted(link["inclusion_disposition"] for link in accepted["links"]) == [
        "excluded",
        "excluded",
        "included",
    ]
    assert {link["funnel_event_id"] for link in accepted["links"]} == {
        link["funnel_event_id"] for link in wide["links"]
    }
    with pytest.raises(EvidenceRefusal, match="incomplete-funnel-cohort"):
        evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=cohort_ids["incomplete"])
    with pytest.raises(EvidenceRefusal, match="incomplete-funnel-window"):
        evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=cohort_ids["incomplete-window"])
    with pytest.raises(EvidenceRefusal, match="undefined-censor-policy"):
        evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=cohort_ids["undefined-censor"])


def test_private_latest_restatement_diverges_from_what_was_known() -> None:
    conn = connect()
    initialize(conn)
    build_private_markets_fixture(conn)
    request = DatasetSliceRequest(
        "dataset:private-markets", "shortlisted-nda", core_right_id("private-markets"), "research"
    )
    early = as_known_slice(conn, decision_at=datetime(2024, 6, 1, tzinfo=UTC), request=request)
    late = as_known_slice(conn, decision_at=datetime(2024, 8, 1, tzinfo=UTC), request=request)
    early_nav = next(
        row["payload"]["value"] for row in early.rows if row["payload"]["label"] == "nav-one"
    )
    late_nav = next(
        row["payload"]["value"] for row in late.rows if row["payload"]["label"] == "nav-one"
    )
    assert (early_nav, late_nav) == (85_000_000, 80_000_000)
    assert early.digest != late.digest

    public_conn = connect()
    initialize(public_conn)
    build_public_markets_fixture(public_conn)
    public_request = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    public_early = as_known_slice(
        public_conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=public_request
    )
    public_late = as_known_slice(
        public_conn, decision_at=datetime(2024, 5, 20, tzinfo=UTC), request=public_request
    )
    early_b = next(
        row["payload"]["value"] for row in public_early.rows if row["payload"]["label"] == "B"
    )
    late_b = next(
        row["payload"]["value"] for row in public_late.rows if row["payload"]["label"] == "B"
    )
    assert (early_b, late_b) == (1, 3)
