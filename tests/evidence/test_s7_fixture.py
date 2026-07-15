from dataclasses import fields, replace
import json

import pytest

from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
from quant_allocator.evidence.lineage import verify_receipt
from quant_allocator.evidence.schema import connect, initialize


def test_s7_public_contract_is_exact_and_closed() -> None:
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        S7_DATASET_IDS,
        S7_FIXTURE_ID,
        S7_SCHEMA_SHA256,
        S7_SCENARIOS,
        S7FixtureManifest,
        S7MethodPolicyEvidence,
    )

    assert S7_FIXTURE_ID == "s7_evidence_v1"
    assert S7_SCHEMA_SHA256 == "43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818"
    assert S7_SCENARIOS == ("public-equity", "hedge-fund", "credit", "private-market")
    assert tuple(S7_CUTOFFS) == ("early", "latest")
    assert S7_DATASET_IDS == (
        "dataset:s7-public-registered",
        "dataset:s7-hedge-composite",
        "dataset:s7-credit-lineage",
        "dataset:s7-private-cashflow-nav",
        "dataset:s7-fx",
        "dataset:s7-benchmark",
        "dataset:s7-lineage-terms",
        "dataset:s7-method-boundary",
    )
    assert fields(S7MethodPolicyEvidence)[0].name == "policy_id"
    assert S7FixtureManifest.__dataclass_params__.frozen is True


def test_s7_request_registry_rejects_unknown_tokens() -> None:
    from quant_allocator.evidence.fixtures.s7 import s7_source_requests

    for kwargs, code in (
        ({"scenario": "other", "cutoff_name": "early", "revision_mode": "latest-known"}, "s7-unknown-scenario"),
        ({"scenario": "public-equity", "cutoff_name": "other", "revision_mode": "latest-known"}, "s7-unknown-cutoff"),
        ({"scenario": "public-equity", "cutoff_name": "early", "revision_mode": "other"}, "s7-unknown-revision-mode"),
    ):
        with pytest.raises(ValueError, match=code):
            s7_source_requests(object(), **kwargs)
    with pytest.raises(TypeError, match="s7-manifest-required"):
        s7_source_requests(
            None,
            scenario="public-equity",
            cutoff_name="early",
            revision_mode="latest-known",
        )


def test_s7_terms_policy_and_death_evidence_are_strict_and_receipted() -> None:
    from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources

    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    policy, bundle = build_s7_terms_sources(conn)

    schemas = {
        row["payload_schema_id"]: json.loads(row["schema_json"])
        for row in conn.execute(
            "SELECT * FROM payload_schema WHERE payload_schema_id LIKE 'schema:s7-%'"
        )
    }
    assert {
        "schema:s7-basis-term-v1",
        "schema:s7-relationship-evidence-v1",
        "schema:s7-death-evidence-v1",
        "schema:s7-method-policy-v1",
        "schema:s7-delivery-manifest-v1",
    } <= set(schemas)
    assert all(schema["additionalProperties"] is False for schema in schemas.values())
    assert not conn.execute(
        "SELECT 1 FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id LIKE 'dataset:s7-%' AND i.payload_schema_id='schema:generic-v1'"
    ).fetchone()

    payload = json.loads(
        conn.execute(
            "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?", (policy.item_id,)
        ).fetchone()[0]
    )
    assert payload == {
        "output_pointer": "/refusals/performance-estimator",
        "policy_id": "s7-method-boundary/v1",
        "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
        "statement": (
            "S7 reconstructs lineage and basis-qualified panels; it does not estimate "
            "alpha, Sharpe, IRR, PME, skill, or manager ranking."
        ),
    }
    span = conn.execute(
        "SELECT * FROM evidence_span WHERE evidence_span_id=?", (policy.span_id,)
    ).fetchone()
    assert span["evidence_item_id"] == policy.item_id
    assert span["json_pointer"] == "/statement"
    assert bundle.slices[0].digest == policy.snapshot_digest
    assert bundle.slices[0].receipt_id == policy.slice_receipt_id
    assert bundle.bundle_digest == policy.bundle_digest
    assert bundle.join_receipt_id == policy.join_receipt_id
    verify_receipt(conn, policy.slice_receipt_id, bundle)
    verify_receipt(conn, policy.join_receipt_id, bundle)


def test_s7_policy_reconstruction_and_death_receipt_reject_tampering() -> None:
    from quant_allocator.evidence.checks import EvidenceRefusal
    from quant_allocator.evidence.fixtures.credit import build_s7_credit_sources
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )
    from quant_allocator.evidence.fixtures.s7 import (
        S7_FIXTURE_ID,
        S7_SCHEMA_SHA256,
        S7FixtureManifest,
        _close_s7_projection_links,
        s7_policy_bundle,
    )
    from quant_allocator.evidence.fixtures.terms import (
        build_s7_death_bundle,
        build_s7_terms_sources,
    )

    conn = connect()
    initialize(conn)
    x3 = build_x3_fixture(conn)
    build_s7_public_market_sources(conn)
    build_s7_credit_sources(conn)
    build_s7_private_market_sources(conn)
    policy, _ = build_s7_terms_sources(conn)
    _close_s7_projection_links(conn, x3)
    closed_observation_id = conn.execute(
        "SELECT o.dataset_observation_id FROM dataset_observation o "
        "JOIN evidence_item i USING(evidence_item_id) JOIN source_record s USING(source_record_id) "
        "WHERE s.source_record_key='s7-hf-closed:2023-12'"
    ).fetchone()[0]
    death_bundle = build_s7_death_bundle(conn)
    assert any(
        row["payload"].get("affected_observation_ids") == closed_observation_id
        for row in death_bundle.slices[0].rows
    )
    verify_receipt(conn, death_bundle.slices[0].receipt_id, death_bundle)
    verify_receipt(conn, death_bundle.join_receipt_id, death_bundle)
    death_span_receipt = conn.execute(
        "SELECT receipt_id FROM reconstruction_receipt WHERE algorithm_id='s7-death-span-v1'"
    ).fetchone()[0]
    verify_receipt(conn, death_span_receipt, death_bundle)
    death_payload = json.loads(
        conn.execute(
            "SELECT payload_json FROM evidence_item WHERE record_kind='s7-death-evidence'"
        ).fetchone()[0]
    )
    assert death_payload["canonical_product_id"] == "composite:x3-02"
    assert death_payload["affected_observation_ids"] == closed_observation_id
    assert death_payload["effective_at"] == "2023-12-31T00:00:00.000000Z"
    assert death_payload["first_known_at"] == "2024-09-01T00:00:00Z"

    manifest = S7FixtureManifest(
        fixture_id=S7_FIXTURE_ID,
        fixture_digest="",
        closure_digest="",
        schema_version=1,
        schema_digest=S7_SCHEMA_SHA256,
        x3_fixture_digest=x3.fixture_digest,
        dataset_ids=(),
        payload_schema_digests=(),
        source_record_records=(),
        item_records=(),
        span_records=(),
        right_records=tuple(
            tuple(row) for row in conn.execute("SELECT * FROM evidence_right ORDER BY 1")
        ),
        version_records=(),
        partition_records=(),
        observation_records=(),
        mapping_records=(),
        observation_membership_link_records=(),
        relationship_records=(),
        receipt_ids=(),
        scenario_contracts=(),
        bundle_contracts=(),
        policy=policy,
        limitation_codes=(),
    )
    rebuilt = s7_policy_bundle(conn, manifest)
    assert rebuilt.bundle_digest == policy.bundle_digest
    for field_name in (
        "policy_id",
        "dataset_id",
        "payload_schema_id",
        "payload_schema_sha256",
        "item_id",
        "span_id",
        "observation_id",
        "version_id",
        "right_id",
        "snapshot_digest",
        "slice_receipt_id",
        "bundle_digest",
        "join_receipt_id",
        "payload_sha256",
    ):
        tampered = replace(manifest, policy=replace(policy, **{field_name: "tampered"}))
        with pytest.raises((ValueError, EvidenceRefusal), match="s7-policy|not-known|right"):
            s7_policy_bundle(conn, tampered)

    conn.execute("SAVEPOINT mutate_policy_span")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_span' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute("UPDATE evidence_span SET start_char=1 WHERE evidence_span_id=?", (policy.span_id,))
    with pytest.raises(EvidenceRefusal, match="content-hash-mismatch"):
        s7_policy_bundle(conn, manifest)
    conn.execute("ROLLBACK TO mutate_policy_span")
    conn.execute("RELEASE mutate_policy_span")

    conn.execute("SAVEPOINT mutate_policy_schema")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='payload_schema' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(
        "UPDATE payload_schema SET schema_json=json_set(schema_json,'$.additionalProperties',1) "
        "WHERE payload_schema_id=?",
        (policy.payload_schema_id,),
    )
    with pytest.raises(ValueError, match="s7-policy-manifest-mismatch"):
        s7_policy_bundle(conn, manifest)
    conn.execute("ROLLBACK TO mutate_policy_schema")
    conn.execute("RELEASE mutate_policy_schema")

    from quant_allocator.evidence.model import canonical_bytes, sha256

    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_item' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    altered = dict(
        json.loads(
            conn.execute(
                "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?", (policy.item_id,)
            ).fetchone()[0]
        )
    )
    altered["output_pointer"] = "/tampered"
    conn.execute(
        "UPDATE evidence_item SET payload_json=?,content_sha256=? WHERE evidence_item_id=?",
        (canonical_bytes(altered).decode(), sha256(canonical_bytes(altered)), policy.item_id),
    )
    with pytest.raises(ValueError, match="s7-policy-manifest-mismatch"):
        s7_policy_bundle(conn, manifest)


def test_s7_public_hedge_fx_and_benchmark_sources_encode_pit_adversaries() -> None:
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )

    conn = connect()
    initialize(conn)
    build_s7_public_market_sources(conn)

    assert {
        row[0]
        for row in conn.execute("SELECT dataset_id FROM dataset WHERE dataset_id LIKE 'dataset:s7-%'")
    } == {
        "dataset:s7-public-registered",
        "dataset:s7-hedge-composite",
        "dataset:s7-fx",
        "dataset:s7-benchmark",
    }
    expected_schemas = {
        "schema:s7-periodic-return-v1",
        "schema:s7-fx-return-v1",
        "schema:s7-benchmark-return-v1",
        "schema:s7-delivery-manifest-v1",
    }
    assert expected_schemas <= {
        row[0] for row in conn.execute("SELECT payload_schema_id FROM payload_schema")
    }
    rights = {
        row[0]: (row[1], row[2])
        for row in conn.execute(
            "SELECT dataset_id,access_context,licence_purpose FROM evidence_right "
            "WHERE dataset_id LIKE 'dataset:s7-%'"
        )
    }
    assert rights == {
        "dataset:s7-public-registered": ("public", "s7-research"),
        "dataset:s7-hedge-composite": ("shortlisted-nda", "s7-research"),
        "dataset:s7-fx": ("public", "s7-research"),
        "dataset:s7-benchmark": ("public", "s7-research"),
    }

    payloads = {
        (row[0], row[1], row[2]): json.loads(row[3])
        for row in conn.execute(
            "SELECT s.dataset_id,s.source_record_key,i.version,i.payload_json "
            "FROM evidence_item i JOIN source_record s USING(source_record_id) "
            "WHERE s.dataset_id IN "
            "('dataset:s7-public-registered','dataset:s7-hedge-composite',"
            "'dataset:s7-fx','dataset:s7-benchmark') AND i.record_kind!='s7-delivery-manifest'"
        )
    }
    assert payloads[("dataset:s7-hedge-composite", "s7-hf-main:2024-02", 1)][
        "return_value"
    ] == "0.0100"
    assert payloads[("dataset:s7-hedge-composite", "s7-hf-main:2024-02", 2)][
        "return_value"
    ] == "0.0080"
    assert payloads[("dataset:s7-fx", "s7-fx-eur-usd:2024-02", 1)]["fx_return"] == "0.0200"
    assert payloads[("dataset:s7-fx", "s7-fx-eur-usd:2024-02", 2)]["fx_return"] == "0.0180"
    assert payloads[("dataset:s7-hedge-composite", "s7-hf-fee-unresolved", 1)][
        "management_fee_basis"
    ] == ""
    assert {
        payloads[("dataset:s7-public-registered", key, 1)]["benchmark_version"]
        for key in ("s7-public-benchmark-v1", "s7-public-benchmark-v2")
    } == {"v1", "v2"}
    assert (
        "dataset:s7-hedge-composite",
        "s7-hf-not-inferable",
        1,
    ) in payloads
    assert (
        "dataset:s7-public-registered",
        "s7-null-same-label",
        1,
    ) in payloads
    assert (
        "dataset:s7-hedge-composite",
        "s7-null-same-label",
        1,
    ) in payloads

    hedge_versions = {
        row[0]: row
        for row in conn.execute(
            "SELECT version_label,delivery_mode,absence_semantics,reconstruction_row_count "
            "FROM dataset_version WHERE dataset_id='dataset:s7-hedge-composite'"
        )
    }
    assert hedge_versions["early"][1:3] == ("full-snapshot", "not-inferable")
    assert hedge_versions["latest"][1:3] == ("delta", "explicit-tombstone-only")
    inherited_id = conn.execute(
        "SELECT source_record_id FROM source_record WHERE dataset_id='dataset:s7-hedge-composite' "
        "AND source_record_key='s7-hf-inherited'"
    ).fetchone()[0]
    tombstoned_id = conn.execute(
        "SELECT source_record_id FROM source_record WHERE dataset_id='dataset:s7-hedge-composite' "
        "AND source_record_key='s7-hf-tombstoned'"
    ).fetchone()[0]
    latest_observations = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT i.source_record_id,o.observation_status FROM dataset_observation o "
            "JOIN dataset_version v USING(dataset_version_id) "
            "JOIN evidence_item i USING(evidence_item_id) "
            "WHERE v.dataset_id='dataset:s7-hedge-composite' AND v.version_label='latest'"
        )
    }
    assert inherited_id not in latest_observations
    assert latest_observations[tombstoned_id] == "explicitly-removed"
    assert hedge_versions["latest"][3] == hedge_versions["early"][3]
    assert conn.execute(
        "SELECT COUNT(*) FROM source_record s JOIN evidence_item i USING(source_record_id) "
        "WHERE s.dataset_id='dataset:s7-public-registered' AND i.record_kind='s7-periodic-return' "
        "AND json_extract(i.payload_json,'$.source_product_key')='s7-public-main'"
    ).fetchone()[0] >= 3
    assert conn.execute(
        "SELECT COUNT(*) FROM source_record s JOIN evidence_item i USING(source_record_id) "
        "WHERE s.dataset_id='dataset:s7-hedge-composite' AND i.record_kind='s7-periodic-return' "
        "AND json_extract(i.payload_json,'$.source_product_key')='s7-hf-main'"
    ).fetchone()[0] >= 4


def test_s7_liquid_and_private_actual_slices_preserve_cutoff_semantics() -> None:
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )
    from quant_allocator.evidence.fixtures.s7 import S7_CUTOFFS
    from quant_allocator.evidence.model import DatasetSliceRequest
    from quant_allocator.evidence.snapshot import as_known_slice

    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    liquid = build_s7_public_market_sources(conn)
    private = build_s7_private_market_sources(conn)

    def snapshot(dataset_id, right_id, access_context, cutoff_name):
        return as_known_slice(
            conn,
            decision_at=S7_CUTOFFS[cutoff_name],
            request=DatasetSliceRequest(
                dataset_id,
                access_context,
                right_id,
                "s7-research",
                revision_mode="latest-known",
                include_unresolved=True,
            ),
        )

    hedge_early = snapshot(
        "dataset:s7-hedge-composite", liquid["hedge"]["right_id"], "shortlisted-nda", "early"
    )
    hedge_latest = snapshot(
        "dataset:s7-hedge-composite", liquid["hedge"]["right_id"], "shortlisted-nda", "latest"
    )
    key_by_id = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT source_record_id,source_record_key FROM source_record "
            "WHERE dataset_id LIKE 'dataset:s7-%'"
        )
    }
    early_by_key = {key_by_id[row["source_record_id"]]: row for row in hedge_early.rows}
    latest_by_key = {key_by_id[row["source_record_id"]]: row for row in hedge_latest.rows}
    assert early_by_key["s7-hf-main:2024-02"]["payload"]["return_value"] == "0.0100"
    assert latest_by_key["s7-hf-main:2024-02"]["payload"]["return_value"] == "0.0080"
    assert "s7-hf-inherited" in latest_by_key
    assert "s7-hf-tombstoned" not in latest_by_key
    assert "s7-hf-not-inferable" not in early_by_key
    assert "s7-hf-closed:2023-12" not in early_by_key
    assert "s7-hf-closed:2023-12" in latest_by_key

    fx_early = snapshot("dataset:s7-fx", liquid["fx"]["right_id"], "public", "early")
    fx_latest = snapshot("dataset:s7-fx", liquid["fx"]["right_id"], "public", "latest")
    assert fx_early.rows[0]["payload"]["fx_return"] == "0.0200"
    assert fx_latest.rows[0]["payload"]["fx_return"] == "0.0180"

    private_early = snapshot(
        "dataset:s7-private-cashflow-nav",
        private["right_id"],
        "funded-private-partnership",
        "early",
    )
    private_latest = snapshot(
        "dataset:s7-private-cashflow-nav",
        private["right_id"],
        "funded-private-partnership",
        "latest",
    )
    early_nav = next(row for row in private_early.rows if "nav" in row["payload"])
    latest_nav = next(row for row in private_latest.rows if "nav" in row["payload"])
    assert early_nav["payload"]["nav"] == "85000000.00"
    assert latest_nav["payload"]["nav"] == "80000000.00"
    assert sum("event_kind" in row["payload"] for row in private_latest.rows) == 3
    assert sum("nav" in row["payload"] for row in private_latest.rows) == 1


def test_s7_inherited_projection_requires_verified_slice_receipt() -> None:
    from quant_allocator.evidence.checks import EvidenceRefusal
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        build_s7_fixture,
        s7_source_requests,
    )
    from quant_allocator.evidence.projections import project_entity_mappings
    from quant_allocator.evidence.snapshot import as_known_slice

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    def latest_slice(scenario: str, dataset_id: str):
        request = next(
            request
            for request in s7_source_requests(
                manifest,
                scenario=scenario,
                cutoff_name="latest",
                revision_mode="latest-known",
            )
            if request.dataset_id == dataset_id
        )
        return as_known_slice(conn, decision_at=S7_CUTOFFS["latest"], request=request)

    hedge = latest_slice("hedge-fund", "dataset:s7-hedge-composite")
    private = latest_slice("private-market", "dataset:s7-private-cashflow-nav")
    assert "s7-hf-fee-unresolved" in {
        row["source_key"] for row in project_entity_mappings(conn, hedge)
    }
    assert "s7-private-call" in {
        row["source_key"] for row in project_entity_mappings(conn, private)
    }

    for incomplete in (replace(hedge, receipt_id=None), replace(hedge, decision_at=None)):
        with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
            project_entity_mappings(conn, incomplete)

    conn.execute("SAVEPOINT strip_slice_receipt")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='receipt_seal' "
        "AND sql LIKE '%BEFORE DELETE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute("DELETE FROM receipt_seal WHERE receipt_id=?", (hedge.receipt_id,))
    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        project_entity_mappings(conn, hedge)
    conn.execute("ROLLBACK TO strip_slice_receipt")
    conn.execute("RELEASE strip_slice_receipt")

    inherited_mapping = conn.execute(
        "SELECT source_evidence_item_id,dataset_observation_id,dataset_version_id "
        "FROM entity_mapping WHERE source_key='s7-hf-fee-unresolved'"
    ).fetchone()
    assert inherited_mapping is not None
    tampered_rows = tuple(
        {
            **row,
            "dataset_version_id": inherited_mapping["dataset_version_id"],
        }
        if (
            row["evidence_item_id"],
            row["dataset_observation_id"],
        )
        == (
            inherited_mapping["source_evidence_item_id"],
            inherited_mapping["dataset_observation_id"],
        )
        else row
        for row in hedge.rows
    )
    assert tampered_rows != hedge.rows
    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        project_entity_mappings(conn, replace(hedge, rows=tampered_rows))


def test_s7_credit_and_private_sources_preserve_native_frequency_and_nav_revision() -> None:
    from quant_allocator.evidence.fixtures.credit import build_s7_credit_sources
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )

    conn = connect()
    initialize(conn)
    build_s7_credit_sources(conn)
    build_s7_private_market_sources(conn)

    rights = {
        row[0]: (row[1], row[2])
        for row in conn.execute(
            "SELECT dataset_id,access_context,licence_purpose FROM evidence_right "
            "WHERE dataset_id IN ('dataset:s7-credit-lineage','dataset:s7-private-cashflow-nav')"
        )
    }
    assert rights == {
        "dataset:s7-credit-lineage": ("segregated-mandate", "s7-research"),
        "dataset:s7-private-cashflow-nav": ("funded-private-partnership", "s7-research"),
    }
    assert {
        row[0]
        for row in conn.execute(
            "SELECT payload_schema_id FROM payload_schema WHERE payload_schema_id LIKE 'schema:s7-%'"
        )
    } >= {
        "schema:s7-credit-return-v1",
        "schema:s7-private-cashflow-v1",
        "schema:s7-private-nav-v1",
    }

    credit_payloads = [
        json.loads(row[0])
        for row in conn.execute(
            "SELECT i.payload_json FROM evidence_item i JOIN source_record s USING(source_record_id) "
            "WHERE s.dataset_id='dataset:s7-credit-lineage' AND i.record_kind='s7-credit-return'"
        )
    ]
    assert {(row["source_product_key"], row["frequency"]) for row in credit_payloads} == {
        ("s7-credit-liquid", "monthly"),
        ("s7-credit-private", "quarterly"),
    }
    assert {row["period_end"] for row in credit_payloads} == {
        "2024-02-29T00:00:00Z",
        "2024-03-31T00:00:00Z",
    }
    assert not any(
        row["source_product_key"] == "s7-credit-private"
        and row["period_end"] == "2024-02-29T00:00:00Z"
        for row in credit_payloads
    )

    private_payloads = {
        (row[0], row[1]): json.loads(row[2])
        for row in conn.execute(
            "SELECT s.source_record_key,i.version,i.payload_json FROM evidence_item i "
            "JOIN source_record s USING(source_record_id) "
            "WHERE s.dataset_id='dataset:s7-private-cashflow-nav' "
            "AND i.record_kind IN ('s7-private-cashflow','s7-private-nav')"
        )
    }
    assert {
        private_payloads[(key, 1)]["event_kind"]
        for key in ("s7-private-call", "s7-private-distribution", "s7-private-fee")
    } == {"capital-call", "distribution", "fee-expense"}
    assert {
        private_payloads[(key, 1)]["event_date"]
        for key in ("s7-private-call", "s7-private-distribution", "s7-private-fee")
    } == {"2024-01-17", "2024-03-08", "2024-02-12"}
    assert private_payloads[("s7-private-nav:2024-03-31", 1)]["nav"] == "85000000.00"
    assert private_payloads[("s7-private-nav:2024-03-31", 2)]["nav"] == "80000000.00"
    assert not conn.execute(
        "SELECT 1 FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id='dataset:s7-private-cashflow-nav' "
        "AND i.record_kind='s7-periodic-return'"
    ).fetchone()


def test_s7_projection_closure_links_resolved_observations_to_x3_and_sources_relationships() -> None:
    from quant_allocator.evidence.fixtures.credit import build_s7_credit_sources
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )
    from quant_allocator.evidence.fixtures.s7 import _close_s7_projection_links
    from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources
    from quant_allocator.evidence.fixtures.x3 import verify_x3_manifest

    conn = connect()
    initialize(conn)
    x3_manifest = build_x3_fixture(conn)
    assert verify_x3_manifest(conn, x3_manifest)
    build_s7_public_market_sources(conn)
    build_s7_credit_sources(conn)
    build_s7_private_market_sources(conn)
    build_s7_terms_sources(conn)
    contracts = _close_s7_projection_links(conn, x3_manifest)

    assert verify_x3_manifest(conn, x3_manifest)
    assert {contract.scenario for contract in contracts} == {
        "public-equity",
        "hedge-fund",
        "credit",
        "private-market",
    }
    assert not conn.execute(
        "SELECT 1 FROM entity_mapping WHERE source_key LIKE 's7-%' AND mapping_status='resolved' "
        "AND entity_mapping_id NOT IN "
        "(SELECT m.entity_mapping_id FROM observation_membership_link l "
        "JOIN universe_membership u USING(universe_membership_id) "
        "JOIN entity_mapping m ON m.dataset_observation_id=l.dataset_observation_id "
        "WHERE m.source_key LIKE 's7-%')"
    ).fetchone()
    assert not conn.execute(
        "SELECT dataset_observation_id FROM observation_membership_link l "
        "JOIN entity_mapping m USING(dataset_observation_id) WHERE m.source_key LIKE 's7-%' "
        "GROUP BY dataset_observation_id HAVING COUNT(*)!=1"
    ).fetchone()
    ambiguous = conn.execute(
        "SELECT entity_mapping_id,canonical_entity_id,candidate_entity_ids_json "
        "FROM entity_mapping WHERE source_key='s7-hf-ambiguous'"
    ).fetchone()
    assert ambiguous[1] is None
    assert json.loads(ambiguous[2]) == ["composite:x3-00", "composite:x3-01"]
    assert not conn.execute(
        "SELECT 1 FROM observation_membership_link l JOIN entity_mapping m "
        "USING(dataset_observation_id) WHERE m.entity_mapping_id=?",
        (ambiguous[0],),
    ).fetchone()
    statuses = {status for contract in contracts for _, status in contract.source_statuses}
    assert statuses <= {"active", "inactive", "closed", "unknown"}
    assert "closed" in statuses
    assert "dead" not in statuses

    relationship_rows = conn.execute(
        "SELECT r.relation_type,r.source_entity_id,r.target_entity_id,r.effective_from,r.effective_to "
        "FROM entity_relationship r JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
        "WHERE i.record_kind='s7-relationship-evidence' ORDER BY relation_type,source_entity_id,target_entity_id"
    ).fetchall()
    assert len(relationship_rows) == 24
    assert (
        "employed_by",
        "person:s7-lead",
        "manager:x3-01",
        "2020-01-01T00:00:00.000000Z",
        "2024-01-01T00:00:00.000000Z",
    ) in {tuple(row) for row in relationship_rows}
    point_rows = conn.execute(
        "SELECT r.relation_type,r.temporal_type,r.effective_at,r.effective_from,r.effective_to "
        "FROM entity_relationship r JOIN evidence_item i "
        "ON i.evidence_item_id=r.source_evidence_item_id "
        "WHERE i.record_kind='s7-relationship-evidence' "
        "AND relation_type IN ('predecessor_claim','contradicts_transfer') ORDER BY relation_type"
    ).fetchall()
    assert {tuple(row) for row in point_rows} == {
        ("predecessor_claim", "point", "2024-01-01T00:00:00.000000Z", None, None),
        ("contradicts_transfer", "point", "2024-06-01T00:00:00.000000Z", None, None),
    }
    assert conn.execute(
        "SELECT COUNT(*) FROM canonical_entity WHERE entity_id IN "
        "('person:s7-lead','person:s7-support') AND entity_type='person'"
    ).fetchone()[0] == 2

    death = conn.execute(
        "SELECT i.evidence_item_id,sp.evidence_span_id,json_extract(i.payload_json,'$.reason_code') "
        "FROM evidence_item i JOIN evidence_span sp USING(evidence_item_id) "
        "WHERE i.record_kind='s7-death-evidence' AND sp.json_pointer='/reason_code'"
    ).fetchone()
    assert death is not None and death[2] == "later-dead-product"
    hedge_contract = next(contract for contract in contracts if contract.scenario == "hedge-fund")
    assert death[0] in hedge_contract.death_evidence_item_ids
    assert death[1] in hedge_contract.death_evidence_span_ids


def test_s7_provisional_paths_are_scenario_local_and_tombstoned_latest() -> None:
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        build_s7_fixture,
        s7_source_requests,
    )
    from quant_allocator.evidence.fixtures.x3 import verify_x3_manifest
    from quant_allocator.evidence.model import SnapshotBundleRequest
    from quant_allocator.evidence.projections import project_entity_relationships
    from quant_allocator.evidence.snapshot import as_known_bundle
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    x3_manifest = build_x3_fixture(conn)
    x3_digest = x3_manifest.fixture_digest
    manifest = build_s7_fixture(conn)

    assert x3_digest == "14a159d4547960c937485d328c3b270051daba7114e54f1380869466a11275e0"
    assert verify_x3_manifest(conn, x3_manifest)
    assert build_x3_fixture(conn).fixture_digest == x3_digest
    required_source_keys = {
        "public-equity": ("s7-public-eur",),
        "hedge-fund": ("s7-hf-fee-unresolved",),
        "credit": ("s7-credit-liquid", "s7-credit-private"),
        "private-market": ("s7-private-call", "s7-private-nav:2024-03-31"),
    }
    expected_relationship_counts = {
        "public-equity": 4,
        "hedge-fund": 12,
        "credit": 3,
        "private-market": 5,
    }
    assert {
        contract.scenario: len(contract.relationship_ids)
        for contract in manifest.scenario_contracts
    } == expected_relationship_counts

    provisional_rows = conn.execute(
        "SELECT r.entity_relationship_id,json_extract(i.payload_json,'$.scope') "
        "FROM entity_relationship r JOIN evidence_item i "
        "ON i.evidence_item_id=r.source_evidence_item_id "
        "WHERE i.record_kind='s7-relationship-evidence' "
        "AND json_extract(i.payload_json,'$.scope') LIKE 'provisional-lineage:%'"
    ).fetchall()
    assert len(provisional_rows) == 15
    provisional_ids = {str(row[0]) for row in provisional_rows}
    provisional_by_scenario = {
        scenario: {
            str(row[0])
            for row in provisional_rows
            if row[1] == f"provisional-lineage:{scenario}"
        }
        for scenario in required_source_keys
    }
    assert {
        scenario: len(relationship_ids)
        for scenario, relationship_ids in provisional_by_scenario.items()
    } == {"public-equity": 4, "hedge-fund": 3, "credit": 3, "private-market": 5}

    for scenario, source_keys in required_source_keys.items():
        early_result = build_lineage_from_s7_projections(
            conn, manifest, scenario=scenario, cutoff_name="early"
        )
        placeholders = ",".join("?" for _ in source_keys)
        required_observation_ids = {
            str(row[0])
            for row in conn.execute(
                "SELECT o.dataset_observation_id FROM dataset_observation o "
                "JOIN dataset_version v USING(dataset_version_id) "
                "JOIN evidence_item i USING(evidence_item_id) "
                "JOIN source_record s USING(source_record_id) "
                f"WHERE v.version_label='early' AND o.observation_status='present' "
                f"AND s.source_record_key IN ({placeholders})",
                source_keys,
            )
        }
        assert required_observation_ids <= set(early_result.admitted_observation_ids)

        early_bundle = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS["early"],
                s7_source_requests(
                    manifest,
                    scenario=scenario,
                    cutoff_name="early",
                    revision_mode="latest-known",
                ),
                ("field_dictionary_version",),
                "s7-provisional-path-test-v1",
            ),
        )
        early_relationship_ids = {
            str(relationship["entity_relationship_id"])
            for slice_ in early_bundle.slices
            for relationship in project_entity_relationships(conn, slice_)
        }
        assert provisional_ids & early_relationship_ids == provisional_by_scenario[scenario]

        latest_result = build_lineage_from_s7_projections(
            conn, manifest, scenario=scenario, cutoff_name="latest"
        )
        assert latest_result.admitted_observation_ids
        assert all(
            refusal.reason_code != "lineage-relationship-missing"
            for refusal in latest_result.refusals
        )
        latest_bundle = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS["latest"],
                s7_source_requests(
                    manifest,
                    scenario=scenario,
                    cutoff_name="latest",
                    revision_mode="latest-known",
                ),
                ("field_dictionary_version",),
                "s7-provisional-path-test-v1",
            ),
        )
        latest_relationship_ids = {
            str(relationship["entity_relationship_id"])
            for slice_ in latest_bundle.slices
            for relationship in project_entity_relationships(conn, slice_)
        }
        assert not (provisional_ids & latest_relationship_ids)


def test_s7_l9_overlap_owns_one_product_through_two_receipted_intervals() -> None:
    """The planted hedge overlap is source-backed, scoped, and effective-dated."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.fixtures.x3 import verify_x3_manifest

    conn = connect()
    initialize(conn)
    x3_manifest = build_x3_fixture(conn)
    manifest = build_s7_fixture(conn)

    rows = conn.execute(
        "SELECT json_extract(i.payload_json,'$.relationship_key') AS relationship_key,"
        "r.entity_relationship_id,r.relation_type,r.source_entity_id,r.target_entity_id,"
        "r.effective_from,r.effective_to,r.evidence_span_id,r.dataset_observation_id,"
        "r.dataset_version_id,json_extract(i.payload_json,'$.scope') AS scope "
        "FROM entity_relationship r JOIN evidence_item i "
        "ON i.evidence_item_id=r.source_evidence_item_id "
        "WHERE json_extract(i.payload_json,'$.relationship_key') LIKE 's7-hf-overlap-%' "
        "ORDER BY relationship_key"
    ).fetchall()
    assert tuple(row["relationship_key"] for row in rows) == (
        "s7-hf-overlap-owner-a",
        "s7-hf-overlap-owner-b",
        "s7-hf-overlap-path-offers",
    )
    owners = tuple(row for row in rows if row["scope"] == "s7-l9-overlap-owner")
    assert {
        (
            row["relation_type"],
            row["source_entity_id"],
            row["target_entity_id"],
            row["effective_from"],
            row["effective_to"],
        )
        for row in owners
    } == {
        (
            "reported_through",
            "strategy:x3-00",
            "composite:x3-01",
            "2024-02-01T00:00:00.000000Z",
            "2024-03-01T00:00:00.000000Z",
        ),
        (
            "reported_through",
            "strategy:x3-01",
            "composite:x3-01",
            "2024-02-01T00:00:00.000000Z",
            "2024-03-01T00:00:00.000000Z",
        ),
    }
    hedge_contract = next(
        contract
        for contract in manifest.scenario_contracts
        if contract.scenario == "hedge-fund"
    )
    assert {str(row["entity_relationship_id"]) for row in rows} <= set(
        hedge_contract.relationship_ids
    )
    assert all(
        conn.execute(
            "SELECT 1 FROM evidence_span WHERE evidence_span_id=? "
            "AND json_pointer='/assertion'",
            (row["evidence_span_id"],),
        ).fetchone()
        for row in rows
    )
    assert verify_x3_manifest(conn, x3_manifest)


def test_s7_retroactive_membership_is_late_visible_and_historically_effective() -> None:
    from quant_allocator.evidence.fixtures.s7 import S7_CUTOFFS, build_s7_fixture
    from quant_allocator.evidence.model import DatasetSliceRequest
    from quant_allocator.evidence.projections import (
        project_entity_mappings,
        project_universe_memberships,
    )
    from quant_allocator.evidence.snapshot import as_known_slice
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    x3_manifest = build_x3_fixture(conn)
    manifest = build_s7_fixture(conn)
    assert len(manifest.observation_membership_link_records) == 25

    retro = conn.execute(
        "SELECT o.dataset_observation_id,i.effective_at FROM dataset_observation o "
        "JOIN dataset_version v USING(dataset_version_id) "
        "JOIN evidence_item i USING(evidence_item_id) "
        "JOIN source_record s USING(source_record_id) "
        "WHERE s.source_record_key='s7-hf-retro-member' "
        "AND v.version_label='early' AND o.observation_status='present'"
    ).fetchall()
    assert len(retro) == 1
    retro_observation_id = str(retro[0][0])
    assert retro[0][1] == "2024-01-31T00:00:00.000000Z"

    persisted_links = conn.execute(
        "SELECT l.observation_membership_link_id,l.universe_membership_id,xm.source_key,"
        "xm.canonical_entity_id FROM observation_membership_link l "
        "JOIN universe_membership u USING(universe_membership_id) "
        "JOIN entity_mapping xm USING(entity_mapping_id) "
        "WHERE l.dataset_observation_id=?",
        (retro_observation_id,),
    ).fetchall()
    assert len(persisted_links) == 1
    assert tuple(persisted_links[0]) == (
        "observation-membership:sha256:e7642ec20b68023daf93d17c80681b357a48c4233f1536a1b82f7ec26a345f67",
        "membership:sha256:e4eb2903f740f2a5014e6872d1749a80057a723e24c328e5c10bc195b414f07a",
        "x3-source-0003",
        "composite:x3-03",
    )
    s7_mappings_to_retro_product = conn.execute(
        "SELECT source_key,dataset_observation_id FROM entity_mapping "
        "WHERE source_key LIKE 's7-%' AND canonical_entity_id='composite:x3-03'"
    ).fetchall()
    assert [tuple(row) for row in s7_mappings_to_retro_product] == [
        ("s7-hf-retro-member", retro_observation_id)
    ]

    dataset_id = "dataset:x3-strategy-export"

    def projections(cutoff_name: str):
        cutoff = S7_CUTOFFS[cutoff_name]
        snapshot = as_known_slice(
            conn,
            decision_at=cutoff,
            request=DatasetSliceRequest(
                dataset_id,
                x3_manifest.access_contexts[dataset_id],
                x3_manifest.right_ids[dataset_id],
                "x3-research",
                valid_at=cutoff,
            ),
        )
        return (
            project_entity_mappings(conn, snapshot),
            project_universe_memberships(conn, snapshot),
        )

    early_mappings, early_memberships = projections("early")
    assert not any(mapping["source_key"] == "x3-source-0003" for mapping in early_mappings)
    assert not any(
        membership["universe_membership_id"]
        == "membership:sha256:e4eb2903f740f2a5014e6872d1749a80057a723e24c328e5c10bc195b414f07a"
        for membership in early_memberships
    )
    early_result = build_lineage_from_s7_projections(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )
    assert retro_observation_id not in early_result.admitted_observation_ids

    latest_mappings, latest_memberships = projections("latest")
    latest_mapping = [
        mapping for mapping in latest_mappings if mapping["source_key"] == "x3-source-0003"
    ]
    assert len(latest_mapping) == 1
    assert latest_mapping[0]["entity_mapping_id"] == (
        "mapping:sha256:8dacd066b31357169b416d1b4c2d1d0ee5477512a09e6802ff5a62a81d563f9d"
    )
    assert latest_mapping[0]["canonical_entity_id"] == "composite:x3-03"
    latest_membership = [
        membership
        for membership in latest_memberships
        if membership["entity_mapping_id"] == latest_mapping[0]["entity_mapping_id"]
    ]
    assert len(latest_membership) == 1
    assert latest_membership[0]["universe_membership_id"] == persisted_links[0][1]
    assert latest_membership[0]["effective_from"] == "2024-01-01T00:00:00.000000Z"
    assert latest_membership[0]["effective_to"] is None
    assert latest_membership[0]["effective_from"] <= retro[0][1]

    latest_result = build_lineage_from_s7_projections(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )
    assert retro_observation_id in latest_result.admitted_observation_ids


def test_s7_complete_manifest_builds_paired_bundles_and_verifies_receipts() -> None:
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        S7_DATASET_IDS,
        build_s7_fixture,
        s7_source_requests,
        verify_s7_manifest,
    )
    from quant_allocator.evidence.model import SnapshotBundleRequest
    from quant_allocator.evidence.schema import SCHEMA_VERSION
    from quant_allocator.evidence.snapshot import as_known_bundle

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    assert manifest.dataset_ids == S7_DATASET_IDS
    assert manifest.schema_version == SCHEMA_VERSION == 1
    assert type(manifest.schema_version) is int
    assert len(manifest.scenario_contracts) == 4
    assert len(manifest.bundle_contracts) == 8
    assert verify_s7_manifest(conn, manifest)

    for contract in manifest.bundle_contracts:
        analytic_requests = s7_source_requests(
            manifest,
            scenario=contract.scenario,
            cutoff_name=contract.cutoff_name,
            revision_mode="latest-known",
        )
        audit_requests = s7_source_requests(
            manifest,
            scenario=contract.scenario,
            cutoff_name=contract.cutoff_name,
            revision_mode="all-known-versions",
        )
        assert tuple(replace(request, revision_mode="all-known-versions") for request in analytic_requests) == audit_requests
        analytic = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS[contract.cutoff_name],
                analytic_requests,
                    ("field_dictionary_version",),
                "s7-track-lineage-v1",
            ),
        )
        audit = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS[contract.cutoff_name],
                audit_requests,
                    ("field_dictionary_version",),
                "s7-track-lineage-v1",
            ),
        )
        assert analytic.bundle_digest == contract.analytic_bundle_digest
        assert audit.bundle_digest == contract.audit_bundle_digest
        verify_receipt(conn, analytic.join_receipt_id, analytic)
        verify_receipt(conn, audit.join_receipt_id, audit)
        for slice_ in analytic.slices:
            verify_receipt(conn, slice_.receipt_id, analytic)
        for slice_ in audit.slices:
            verify_receipt(conn, slice_.receipt_id, audit)


def test_s7_semantic_spans_are_field_relative_resolvable_and_mutation_safe() -> None:
    from quant_allocator.evidence.checks import EvidenceRefusal
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.lineage import resolve_span

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    mapping_span_ids = tuple(row[2] for row in manifest.mapping_records)
    relationship_span_ids = tuple(row[2] for row in manifest.relationship_records)
    assert len(mapping_span_ids) == 28
    assert len(relationship_span_ids) == 24
    semantic_span_ids = (
        mapping_span_ids
        + relationship_span_ids
        + (manifest.scenario_contracts[1].death_evidence_span_ids[0], manifest.policy.span_id)
    )
    for span_id in semantic_span_ids:
        resolved = resolve_span(conn, span_id)
        assert resolved["text"]
        span = conn.execute(
            "SELECT start_char,end_char FROM evidence_span WHERE evidence_span_id=?", (span_id,)
        ).fetchone()
        assert span[0] == 0
        assert span[1] == len(resolved["text"])

    target = mapping_span_ids[0]
    conn.execute("SAVEPOINT mutate_span_offset")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_span' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute("UPDATE evidence_span SET start_char=1 WHERE evidence_span_id=?", (target,))
    with pytest.raises(EvidenceRefusal, match="content-hash-mismatch"):
        resolve_span(conn, target)
    conn.execute("ROLLBACK TO mutate_span_offset")
    conn.execute("RELEASE mutate_span_offset")

    conn.execute("SAVEPOINT mutate_span_hash")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_span' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute("UPDATE evidence_span SET span_sha256=? WHERE evidence_span_id=?", ("0" * 64, target))
    with pytest.raises(EvidenceRefusal, match="content-hash-mismatch"):
        resolve_span(conn, target)
    conn.execute("ROLLBACK TO mutate_span_hash")
    conn.execute("RELEASE mutate_span_hash")


def test_s7_manifest_is_idempotent_order_independent_and_detects_payload_mutation() -> None:
    from quant_allocator.evidence.fixtures.credit import build_s7_credit_sources
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        build_s7_fixture,
        s7_authored_closure_digest,
        s7_source_requests,
        verify_s7_manifest,
    )
    from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources
    from quant_allocator.evidence.model import SnapshotBundleRequest
    from quant_allocator.evidence.snapshot import as_known_bundle

    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    for builder in (
        build_s7_terms_sources,
        build_s7_private_market_sources,
        build_s7_credit_sources,
        build_s7_public_market_sources,
    ):
        builder(conn)
    first = build_s7_fixture(conn)
    second = build_s7_fixture(conn)
    assert second == first
    assert verify_s7_manifest(conn, first)

    closure_before = s7_authored_closure_digest(conn)
    downstream_sources = s7_source_requests(
        first,
        scenario="public-equity",
        cutoff_name="latest",
        revision_mode="latest-known",
    )
    as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS["latest"],
            downstream_sources,
            ("field_dictionary_version",),
            "s8-downstream-consumer-v1",
        ),
    )
    assert s7_authored_closure_digest(conn) == closure_before
    assert verify_s7_manifest(conn, first)

    authoritative_snapshot = first.bundle_contracts[0].analytic_slice_digests[0][1]
    conn.execute("SAVEPOINT mutate_authoritative_snapshot")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='snapshot_manifest' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(
        "UPDATE snapshot_manifest SET row_count=row_count+1 WHERE snapshot_digest=?",
        (authoritative_snapshot,),
    )
    assert not verify_s7_manifest(conn, first)
    conn.execute("ROLLBACK TO mutate_authoritative_snapshot")
    conn.execute("RELEASE mutate_authoritative_snapshot")
    assert verify_s7_manifest(conn, first)

    authoritative_receipt = first.bundle_contracts[0].analytic_join_receipt_id
    conn.execute("SAVEPOINT mutate_authoritative_receipt")
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='reconstruction_receipt' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(
        "UPDATE reconstruction_receipt SET value_sha256=? WHERE receipt_id=?",
        ("0" * 64, authoritative_receipt),
    )
    assert not verify_s7_manifest(conn, first)
    conn.execute("ROLLBACK TO mutate_authoritative_receipt")
    conn.execute("RELEASE mutate_authoritative_receipt")


@pytest.mark.parametrize(
    ("table", "target_sql", "mutation_sql"),
    (
        (
            "dataset",
            "SELECT dataset_id FROM dataset WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE dataset SET label=label||'-tampered' WHERE dataset_id=?",
        ),
        (
            "source_record",
            "SELECT source_record_id FROM source_record WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE source_record SET source_entity_type=source_entity_type||'-tampered' WHERE source_record_id=?",
        ),
        (
            "evidence_right",
            "SELECT evidence_right_id FROM evidence_right WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE evidence_right SET received_at_utc=received_at_utc||'-tampered' WHERE evidence_right_id=?",
        ),
        (
            "dataset_version",
            "SELECT dataset_version_id FROM dataset_version WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE dataset_version SET content_sha256='tampered' WHERE dataset_version_id=?",
        ),
        (
            "dataset_delivery_partition",
            "SELECT p.dataset_delivery_partition_id FROM dataset_delivery_partition p "
            "JOIN dataset_version v USING(dataset_version_id) "
            "WHERE v.dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE dataset_delivery_partition SET received_content_sha256='tampered' "
            "WHERE dataset_delivery_partition_id=?",
        ),
        (
            "dataset_observation",
            "SELECT o.dataset_observation_id FROM dataset_observation o "
            "JOIN dataset_version v USING(dataset_version_id) "
            "WHERE v.dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE dataset_observation SET disappearance_reason='tampered' "
            "WHERE dataset_observation_id=?",
        ),
        (
            "dataset_observation_partition_link",
            "SELECT l.dataset_observation_partition_link_id "
            "FROM dataset_observation_partition_link l "
            "JOIN dataset_observation o USING(dataset_observation_id) "
            "JOIN dataset_version v USING(dataset_version_id) "
            "WHERE v.dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE dataset_observation_partition_link "
            "SET dataset_observation_partition_link_id=dataset_observation_partition_link_id||'-tampered' "
            "WHERE dataset_observation_partition_link_id=?",
        ),
        (
            "entity_mapping",
            "SELECT entity_mapping_id FROM entity_mapping "
            "WHERE source_key LIKE 's7-%' ORDER BY 1 LIMIT 1",
            "UPDATE entity_mapping SET resolution_rule=resolution_rule||'-tampered' "
            "WHERE entity_mapping_id=?",
        ),
        (
            "observation_membership_link",
            "SELECT DISTINCT l.observation_membership_link_id "
            "FROM observation_membership_link l "
            "JOIN entity_mapping m USING(dataset_observation_id) "
            "WHERE m.source_key LIKE 's7-%' ORDER BY 1 LIMIT 1",
            "UPDATE observation_membership_link "
            "SET observation_membership_link_id=observation_membership_link_id||'-tampered' "
            "WHERE observation_membership_link_id=?",
        ),
        (
            "entity_relationship",
            "SELECT r.entity_relationship_id FROM entity_relationship r "
            "JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
            "JOIN source_record s ON s.source_record_id=i.source_record_id "
            "WHERE s.dataset_id LIKE 'dataset:s7-%' ORDER BY 1 LIMIT 1",
            "UPDATE entity_relationship SET version=version+1 WHERE entity_relationship_id=?",
        ),
        (
            "receipt_reference",
            "SELECT rr.receipt_id,rr.ordinal FROM receipt_reference rr "
            "JOIN reconstruction_receipt r USING(receipt_id) "
            "WHERE r.claim_id='claim:s7-death-evidence' "
            "AND r.algorithm_id='s7-death-span-v1' ORDER BY 1,2 LIMIT 1",
            "UPDATE receipt_reference SET output_field=output_field||'-tampered' "
            "WHERE receipt_id=? AND ordinal=?",
        ),
        (
            "receipt_seal",
            "SELECT s.receipt_id FROM receipt_seal s "
            "JOIN reconstruction_receipt r USING(receipt_id) "
            "WHERE r.claim_id='claim:s7-death-evidence' "
            "AND r.algorithm_id='s7-death-span-v1' LIMIT 1",
            "UPDATE receipt_seal SET references_sha256='tampered' WHERE receipt_id=?",
        ),
        (
            "snapshot_bundle_manifest",
            "SELECT bundle_digest FROM snapshot_bundle_manifest "
            "WHERE request_json LIKE '%s7-track-lineage-v1%' ORDER BY 1 LIMIT 1",
            "UPDATE snapshot_bundle_manifest SET records_sha256='tampered' WHERE bundle_digest=?",
        ),
    ),
    ids=(
        "dataset",
        "source-record",
        "evidence-right",
        "dataset-version",
        "dataset-delivery-partition",
        "dataset-observation",
        "dataset-observation-partition-link",
        "entity-mapping",
        "observation-membership-link",
        "entity-relationship",
        "receipt-reference",
        "receipt-seal",
        "snapshot-bundle-manifest",
    ),
)
def test_s7_persisted_table_mutation_falsifies_authoritative_verifier(
    table: str, target_sql: str, mutation_sql: str
) -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture, verify_s7_manifest

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    target = conn.execute(target_sql).fetchone()
    assert target is not None

    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=? "
        "AND sql LIKE '%BEFORE UPDATE%'",
        (table,),
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    if table == "dataset_observation_partition_link":
        conn.commit()
        conn.execute("PRAGMA foreign_keys=OFF")
    mutation = conn.execute(mutation_sql, tuple(target))
    assert mutation.rowcount == 1
    if table == "dataset_observation_partition_link":
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall()
    assert not verify_s7_manifest(conn, manifest)


def test_s7_individual_row_reinsertion_order_is_tuple_normalized() -> None:
    from quant_allocator.evidence.fixtures.s7 import (
        build_s7_fixture,
        s7_authored_closure_digest,
        verify_s7_manifest,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    table = "snapshot_bundle_manifest"
    columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
    rows = tuple(
        tuple(row)
        for row in conn.execute(
            "SELECT * FROM snapshot_bundle_manifest WHERE request_json LIKE '%s7-%' "
            "ORDER BY bundle_digest"
        )
    )
    assert len(rows) > 1

    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=? "
        "AND sql LIKE '%BEFORE DELETE%'",
        (table,),
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    for row in rows:
        conn.execute(
            "DELETE FROM snapshot_bundle_manifest WHERE bundle_digest=?",
            (row[0],),
        )
    placeholders = ",".join("?" for _ in columns)
    for row in reversed(rows):
        conn.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
            row,
        )

    physical_rows = tuple(
        tuple(row) for row in conn.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY rowid")
    )
    assert physical_rows[-len(rows) :] == tuple(reversed(rows))
    rebuilt = build_s7_fixture(conn)
    assert rebuilt == manifest
    assert rebuilt.closure_digest == s7_authored_closure_digest(conn)
    assert verify_s7_manifest(conn, rebuilt)
