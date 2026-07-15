import json
import sqlite3
from collections import Counter
from dataclasses import fields, replace
from inspect import signature
from pathlib import Path

import pytest
import quant_allocator.evidence.fixtures.terms as terms_fixture

from quant_allocator.evidence.fixtures.terms import (
    P4_AUTHORED_NEGATIVE_CASE_IDS,
    P4_TERMS_AUTHORED_CLOSURE_SHA256,
    P4_TERMS_AUTHORED_MANIFEST_SHA256,
    P4_TERMS_AUTHORED_SCHEMA_SHA256,
    P4_CANONICAL_ENTITY_IDS,
    P4_DOCUMENT_DATASETS,
    P4_METHOD_POLICY_BUNDLE_CASE_ID,
    P4_METHOD_POLICY_DATASET,
    P4_NEGATIVE_BUNDLE_CASES,
    P4_NEGATIVE_DATASET,
    P4_NEGATIVE_ENTITY_RECORDS,
    P4BundleCaseContract,
    P4_P1_SCENARIO_IDS,
    P4_POSITIVE_CASE_IDS,
    P4_POSITIVE_SCENARIO_IDS,
    P4_PREDECESSOR_SCAFFOLD_IDS,
    P4_PROJECTION_KINDS,
    P4_SCENARIO_FAMILY_BY_ID,
    P4_TERMS_BUNDLE_CASES,
    P4_TERMS_CUTOFFS,
    P4_TERMS_DATASETS,
    P4_TERMS_DOCUMENT_IDS,
    P4TermsFixtureManifest,
    P4_TOPOLOGY_ADVERSARY_IDS,
    TERMS_SHAPES,
    build_p4_method_policy_bundle,
    build_p4_terms_bundle,
    build_terms_fixture,
    p4_method_policy_bundle_request,
    p4_terms_authored_closure_digest,
    p4_terms_authored_closure_payload,
    p4_terms_bundle_request,
    p4_terms_manifest_digest,
    p4_terms_manifest_payload,
    p4_terms_negative_bundle_request,
    verify_p4_terms_manifest,
)
from quant_allocator.evidence.terms import (
    P4_POSITIVE_ENTITY_RECORDS,
    P4_SCENARIO_DATASETS,
)
from quant_allocator.evidence.fixtures.core import core_right_id
from quant_allocator.evidence.ingest import reconstruct_dataset_version
from quant_allocator.evidence.lineage import resolve_span
from quant_allocator.evidence.model import DatasetSliceRequest, digest_id
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_slice


def test_p4_terms_contract_inventory_is_exact() -> None:
    assert tuple(P4_TERMS_CUTOFFS) == ("early", "amended", "side-letter")
    assert len(P4_DOCUMENT_DATASETS) == 7
    assert len(P4_SCENARIO_DATASETS) == 6
    assert len(P4_TERMS_DATASETS) == len(set(P4_TERMS_DATASETS)) == 15
    assert {row[0] for row in P4_DOCUMENT_DATASETS.values()} <= set(P4_TERMS_DATASETS)
    assert {row[0] for row in P4_SCENARIO_DATASETS.values()} <= set(P4_TERMS_DATASETS)
    assert P4_NEGATIVE_DATASET[0] in P4_TERMS_DATASETS
    assert P4_METHOD_POLICY_DATASET[0] in P4_TERMS_DATASETS
    assert len(P4_TERMS_BUNDLE_CASES) == 18
    assert P4_METHOD_POLICY_BUNDLE_CASE_ID == "method-policy:public"
    assert len(P4_NEGATIVE_BUNDLE_CASES) == 20
    assert len(P4_TERMS_DOCUMENT_IDS) == 7
    assert len(P4_POSITIVE_ENTITY_RECORDS) == 6
    assert len(P4_NEGATIVE_ENTITY_RECORDS) == 19
    assert len(P4_CANONICAL_ENTITY_IDS) == len(set(P4_CANONICAL_ENTITY_IDS)) == 25
    assert len(P4_PROJECTION_KINDS) == len(set(P4_PROJECTION_KINDS)) == 17
    assert len(TERMS_SHAPES) == 17
    assert tuple(shape["record_kind"] for shape in TERMS_SHAPES) == tuple(
        kind.replace("_", "-") for kind in P4_PROJECTION_KINDS
    )
    assert len(P4_POSITIVE_CASE_IDS) == len(set(P4_POSITIVE_CASE_IDS)) == 43
    assert len(P4_POSITIVE_SCENARIO_IDS) == len(set(P4_POSITIVE_SCENARIO_IDS)) == 47
    assert len(P4_P1_SCENARIO_IDS) == 5
    assert Counter(P4_SCENARIO_FAMILY_BY_ID.values())["p4-p1"] == 5
    assert set(P4_SCENARIO_FAMILY_BY_ID.values()) == set(P4_POSITIVE_CASE_IDS)
    assert len(P4_AUTHORED_NEGATIVE_CASE_IDS) == 19
    assert P4_TOPOLOGY_ADVERSARY_IDS == ("p4-auth-partial-document-authorization",)
    assert P4_PREDECESSOR_SCAFFOLD_IDS == (
        "scaffold:p4-p29b-from-p29a",
        "scaffold:p4-p29c-from-p29b",
    )
    right_contracts = {
        **{row[0]: (row[1], row[2]) for row in P4_DOCUMENT_DATASETS.values()},
        **{
            row[0]: (context, row[1])
            for context, row in P4_SCENARIO_DATASETS.items()
        },
        P4_NEGATIVE_DATASET[0]: P4_NEGATIVE_DATASET[1:],
        P4_METHOD_POLICY_DATASET[0]: P4_METHOD_POLICY_DATASET[1:],
    }
    assert len(right_contracts) == 15
    assert set(right_contracts) == set(P4_TERMS_DATASETS)


def test_terms_fixture_builds_exact_source_closure() -> None:
    conn = connect()
    initialize(conn)

    manifest = build_terms_fixture(conn)

    assert manifest.dataset_ids == tuple(P4_TERMS_DATASETS)
    assert manifest.document_dataset_ids == tuple(
        row[0] for row in P4_DOCUMENT_DATASETS.values()
    )
    assert manifest.scenario_dataset_ids == tuple(
        row[0] for row in P4_SCENARIO_DATASETS.values()
    )
    assert manifest.negative_dataset_id == P4_NEGATIVE_DATASET[0]
    assert manifest.method_policy_dataset_id == P4_METHOD_POLICY_DATASET[0]
    assert manifest.canonical_entity_ids == P4_CANONICAL_ENTITY_IDS
    assert set(manifest.canonical_entity_records) == set(P4_CANONICAL_ENTITY_IDS)
    expected_entity_identity = {
        row[0]: (row[1], row[2])
        for row in (
            *P4_POSITIVE_ENTITY_RECORDS.values(),
            *P4_NEGATIVE_ENTITY_RECORDS.values(),
        )
    }
    assert {
        entity_id: (record[1], record[2])
        for entity_id, record in manifest.canonical_entity_records.items()
    } == expected_entity_identity
    assert all(record[3] is None for record in manifest.canonical_entity_records.values())
    assert all(
        record[4:] == ("point", "1970-01-01T00:00:00.000000Z", None, None)
        for record in manifest.canonical_entity_records.values()
    )
    assert manifest.document_ids == P4_TERMS_DOCUMENT_IDS

    expected_right_scope = {
        **{row[0]: row[1:] for row in P4_DOCUMENT_DATASETS.values()},
        **{
            row[0]: (context, row[1])
            for context, row in P4_SCENARIO_DATASETS.items()
        },
        P4_NEGATIVE_DATASET[0]: P4_NEGATIVE_DATASET[1:],
        P4_METHOD_POLICY_DATASET[0]: P4_METHOD_POLICY_DATASET[1:],
    }
    assert set(manifest.right_ids) == set(P4_TERMS_DATASETS)
    assert {
        dataset_id: (manifest.access_contexts[dataset_id], manifest.licence_purposes[dataset_id])
        for dataset_id in P4_TERMS_DATASETS
    } == expected_right_scope
    assert manifest.right_ids["dataset:terms"] == core_right_id("terms")
    core_right = manifest.right_records["dataset:terms"]
    assert core_right[0] == core_right_id("terms")
    assert core_right[8:11] == (
        "2024-01-10T00:00:00.000000Z",
        "2024-01-10T00:00:00.000000Z",
        None,
    )
    for dataset_id in set(P4_TERMS_DATASETS) - {"dataset:terms"}:
        right = manifest.right_records[dataset_id]
        assert right[6:12] == (
            "active",
            "retain-after-expiry",
            "2024-01-01T00:00:00.000000Z",
            "2024-01-01T00:00:00.000000Z",
            None,
            None,
        )

    expected_schema_ids = {
        f"schema:p4-{kind.replace('_', '-')}-v1" for kind in P4_PROJECTION_KINDS
    }
    assert set(manifest.payload_schema_ids) == expected_schema_ids
    assert len(manifest.payload_schema_ids) == 17
    schema_rows = conn.execute(
        "SELECT schema_json FROM payload_schema WHERE payload_schema_id LIKE 'schema:p4-%'"
    ).fetchall()
    assert len(schema_rows) == 17
    for row in schema_rows:
        schema = json.loads(row[0])
        assert schema["required"] == [
            "record_key",
            "projection_kind",
            "classification",
            "source_text",
            "span_marker",
            "value",
        ]
        assert schema["additionalProperties"] is False
        assert schema["properties"]["value"]["additionalProperties"] is False

    expected_versions = {
        "dataset:p4-doc-public-liquid-prospectus": ("v1-full",),
        "dataset:p4-doc-segregated-ima": ("v1-full", "v2-amendment-delta"),
        "dataset:p4-doc-private-ppm": ("v1-full",),
        "dataset:p4-doc-whole-fund-lpa": (
            "v1-full",
            "v2-amendment-delta",
            "v3-side-letter-delta",
        ),
        "dataset:p4-doc-deal-by-deal-lpa": (
            "v1-full",
            "v2-amendment-delta",
            "v3-side-letter-delta",
        ),
        "dataset:terms": ("v1-amendment-full",),
        "dataset:p4-doc-side-letter": ("v1-side-letter-full",),
        "dataset:p4-scenarios-public": ("v1-full",),
        "dataset:p4-scenarios-prehire": ("v1-full",),
        "dataset:p4-scenarios-shortlisted": (
            "v1-full",
            "v2-p29b-delta",
            "v3-p29c-delta",
        ),
        "dataset:p4-scenarios-funded-commingled": ("v1-full",),
        "dataset:p4-scenarios-funded-private": (
            "v1-full",
            "v2-p29b-delta",
            "v3-p29c-delta",
        ),
        "dataset:p4-scenarios-segregated": ("v1-full",),
        "dataset:p4-negative-terms": ("v1-full", "v2-future-leak-delta"),
        "dataset:p4-method-boundary-policy": ("v1-full",),
    }
    actual_versions = {
        dataset_id: tuple(
            row[0]
            for row in conn.execute(
                "SELECT version_label FROM dataset_version WHERE dataset_id=? "
                "ORDER BY received_at_utc, version_label",
                (dataset_id,),
            )
        )
        for dataset_id in P4_TERMS_DATASETS
    }
    assert actual_versions == expected_versions
    assert len(manifest.version_ids) == 25
    assert all(len(rows) == 1 for rows in manifest.partition_records.values())
    for dataset_id, labels in expected_versions.items():
        rows = conn.execute(
            "SELECT * FROM dataset_version WHERE dataset_id=? "
            "ORDER BY received_at_utc, version_label",
            (dataset_id,),
        ).fetchall()
        assert tuple(row["version_label"] for row in rows) == labels
        for index, row in enumerate(rows):
            is_full = row["version_label"].endswith("full")
            assert row["delivery_mode"] == ("full-snapshot" if is_full else "delta")
            assert row["absence_semantics"] == (
                "full-snapshot-means-removed" if is_full else "not-inferable"
            )
            assert row["completeness_status"] == "complete"
            assert row["expected_partition_count"] == row["received_partition_count"] == 1
            expected_received = (
                "2024-07-15T00:00:00.000000Z"
                if "side-letter" in row["version_label"] or "p29c" in row["version_label"]
                else "2024-04-15T00:00:00.000000Z"
                if "amendment" in row["version_label"]
                or "p29b" in row["version_label"]
                or "future-leak" in row["version_label"]
                else "2024-01-15T00:00:00.000000Z"
            )
            assert row["received_at_utc"] == expected_received
            if is_full:
                assert row["predecessor_dataset_version_id"] is None
                assert row["base_dataset_version_id"] is None
            else:
                assert row["predecessor_dataset_version_id"] == rows[index - 1][
                    "dataset_version_id"
                ]
                assert row["base_dataset_version_id"] == rows[0]["dataset_version_id"]
            partition = conn.execute(
                "SELECT * FROM dataset_delivery_partition WHERE dataset_version_id=?",
                (row["dataset_version_id"],),
            ).fetchone()
            assert partition["partition_status"] == "expected-received"
            observation_count = conn.execute(
                "SELECT count(*) FROM dataset_observation WHERE dataset_version_id=?",
                (row["dataset_version_id"],),
            ).fetchone()[0]
            link_count = conn.execute(
                "SELECT count(*) FROM dataset_observation_partition_link l "
                "JOIN dataset_observation o USING(dataset_observation_id) "
                "WHERE o.dataset_version_id=?",
                (row["dataset_version_id"],),
            ).fetchone()[0]
            assert partition["received_record_count"] == observation_count == link_count
    assert all(
        reconstruct_dataset_version(conn, version_id).reconstruction_manifest_sha256
        == manifest.reconstruction_digests[version_id]
        for version_id in manifest.version_ids
    )

    document_rows = conn.execute(
        "SELECT payload_json FROM evidence_item WHERE record_kind='term-document'"
    ).fetchall()
    assert {
        json.loads(row[0])["value"]["document_id"] for row in document_rows
    } == set(P4_TERMS_DOCUMENT_IDS)
    scenario_source_datasets = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT s.dataset_id FROM evidence_item i "
            "JOIN source_record s USING(source_record_id) "
            "WHERE i.record_kind='scenario-input'"
        )
    }
    assert scenario_source_datasets == {
        *(row[0] for row in P4_SCENARIO_DATASETS.values()),
        P4_NEGATIVE_DATASET[0],
    }
    assert conn.execute(
        "SELECT count(*) FROM evidence_item WHERE record_kind='calculation-policy'"
    ).fetchone()[0] == 6
    assert {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT s.dataset_id,count(*) FROM evidence_item i "
            "JOIN source_record s USING(source_record_id) "
            "WHERE i.record_kind='calculation-policy' GROUP BY s.dataset_id"
        )
    } == {row[0]: 1 for row in P4_SCENARIO_DATASETS.values()}
    assert conn.execute(
        "SELECT count(*) FROM evidence_item WHERE record_kind='method-boundary-policy'"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT s.dataset_id FROM evidence_item i JOIN source_record s "
        "USING(source_record_id) WHERE i.record_kind='method-boundary-policy'"
    ).fetchone()[0] == P4_METHOD_POLICY_DATASET[0]

    assert len(manifest.evidence_item_ids) == len(manifest.evidence_span_ids)
    for span_id in manifest.evidence_span_ids:
        resolved = resolve_span(conn, span_id)
        item = conn.execute(
            "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?",
            (resolved["evidence_item_id"],),
        ).fetchone()
        payload = json.loads(item[0])
        assert resolved["json_pointer"] == "/source_text"
        assert resolved["text"] == payload["span_marker"]
        assert payload["source_text"].count(payload["span_marker"]) == 1

    smoke = conn.execute(
        "SELECT payload_json FROM evidence_item WHERE payload_json LIKE '%notice%' "
        "OR payload_json LIKE '%amendment-one%' OR payload_json LIKE '%precedence-one%'"
    ).fetchall()
    assert smoke == []
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert signature(build_terms_fixture).return_annotation == "P4TermsFixtureManifest"
    rebuilt = build_terms_fixture(conn)
    assert rebuilt.fixture_digest == manifest.fixture_digest
    assert rebuilt.evidence_item_ids == manifest.evidence_item_ids


def test_terms_fixture_pit_and_document_entity_topology_are_exact() -> None:
    conn = connect()
    initialize(conn)
    manifest = build_terms_fixture(conn)
    document_contexts = {
        "document:p4-public-liquid-prospectus": ("public", "funded-commingled"),
        "document:p4-segregated-ima": ("shortlisted-nda", "segregated-mandate"),
        "document:p4-private-ppm": (
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
        "document:p4-whole-fund-lpa": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
        "document:p4-deal-by-deal-lpa": (
            "shortlisted-nda",
            "funded-private-partnership",
        ),
        "document:p4-amendment": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ),
        "document:p4-side-letter": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
    }
    dataset_by_document = {
        document_id: row[0] for document_id, row in P4_DOCUMENT_DATASETS.items()
    }
    relation_contracts = {
        ("document:p4-public-liquid-prospectus", "public"): (
            "amends",
            "early",
            "2024-01-15",
        ),
        ("document:p4-segregated-ima", "shortlisted-nda"): (
            "supersedes",
            "amended",
            "2024-04-15",
        ),
        ("document:p4-private-ppm", "pre-hire-public"): (
            "clarifies",
            "early",
            "2024-01-15",
        ),
        ("document:p4-whole-fund-lpa", "funded-commingled"): (
            "incorporates",
            "early",
            "2024-01-15",
        ),
        ("document:p4-side-letter", "funded-private-partnership"): (
            "investor_override",
            "side-letter",
            "2024-07-15",
        ),
    }

    for document_id, contexts in document_contexts.items():
        dataset_id = dataset_by_document[document_id]
        persisted_entities = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT i.canonical_entity_id FROM evidence_item i "
                "JOIN source_record s USING(source_record_id) WHERE s.dataset_id=?",
                (dataset_id,),
            )
        }
        assert persisted_entities == {
            P4_POSITIVE_ENTITY_RECORDS[context][0] for context in contexts
        }
        if len(contexts) > 1:
            assert len(persisted_entities) >= 2

        for context in contexts:
            request = DatasetSliceRequest(
                dataset_id=dataset_id,
                access_context=manifest.access_contexts[dataset_id],
                evidence_right_id=manifest.right_ids[dataset_id],
                licence_purpose=manifest.licence_purposes[dataset_id],
                canonical_entity_ids=(P4_POSITIVE_ENTITY_RECORDS[context][0],),
                include_unresolved=False,
            )
            visibility = {
                cutoff_name: as_known_slice(
                    conn,
                    decision_at=cutoff,
                    request=request,
                )
                for cutoff_name, cutoff in P4_TERMS_CUTOFFS.items()
            }
            first_cutoff = (
                "amended"
                if document_id == "document:p4-amendment"
                else "side-letter"
                if document_id == "document:p4-side-letter"
                else "early"
            )
            for cutoff_name in P4_TERMS_CUTOFFS:
                document_is_visible = int(
                    tuple(P4_TERMS_CUTOFFS).index(cutoff_name)
                    >= tuple(P4_TERMS_CUTOFFS).index(first_cutoff)
                )
                relation_contract = relation_contracts.get((document_id, context))
                relation_first_cutoff = (
                    relation_contract[1] if relation_contract is not None else None
                )
                relation_is_visible = int(
                    relation_first_cutoff is not None
                    and tuple(P4_TERMS_CUTOFFS).index(cutoff_name)
                    >= tuple(P4_TERMS_CUTOFFS).index(relation_first_cutoff)
                )
                expected_count = document_is_visible + 3 * relation_is_visible
                assert len(visibility[cutoff_name].rows) == expected_count
                rows_by_key = {
                    row["payload"]["record_key"]: row
                    for row in visibility[cutoff_name].rows
                }
                expected_keys = (
                    {f"{document_id}:{context}"} if document_is_visible else set()
                )
                if relation_is_visible:
                    relation_type, _, effective_from = relation_contract
                    relation_slug = relation_type.replace("_", "-")
                    clause_keys = {
                        f"clause:{relation_slug}:source:{context}",
                        f"clause:{relation_slug}:target:{context}",
                    }
                    relation_key = f"relation:{relation_slug}:{context}"
                    expected_keys |= {*clause_keys, relation_key}
                    relation_value = rows_by_key[relation_key]["payload"]["value"]
                    assert relation_value == {
                        "document_key": document_id,
                        "relation_id": f"relation:p4-{relation_slug}",
                        "relation_type": relation_type,
                        "from_clause_key": f"clause:{relation_slug}:source:{context}",
                        "to_clause_key": f"clause:{relation_slug}:target:{context}",
                        "term_key": "management_fee_rate",
                        "investor_scope": [f"investor:p4-{context}"],
                        "vehicle_scope": [f"vehicle:p4-{context}"],
                        "effective_from": effective_from,
                        "effective_to": None,
                        "review_state": "reviewed",
                    }
                    for position in ("source", "target"):
                        clause_key = f"clause:{relation_slug}:{position}:{context}"
                        assert rows_by_key[clause_key]["payload"]["value"] == {
                            "document_key": document_id,
                            "clause_id": clause_key,
                            "clause_family": f"{relation_slug}-{position}",
                            "effective_from": effective_from,
                            "effective_to": None,
                        }
                assert set(rows_by_key) == expected_keys
                assert {
                    row["canonical_entity_id"] for row in visibility[cutoff_name].rows
                } <= {P4_POSITIVE_ENTITY_RECORDS[context][0]}

    sample_dataset = P4_DOCUMENT_DATASETS[
        "document:p4-public-liquid-prospectus"
    ][0]
    sample = DatasetSliceRequest(
        dataset_id=sample_dataset,
        access_context=manifest.access_contexts[sample_dataset],
        evidence_right_id=manifest.right_ids[sample_dataset],
        licence_purpose=manifest.licence_purposes[sample_dataset],
        canonical_entity_ids=(P4_POSITIVE_ENTITY_RECORDS["public"][0],),
        include_unresolved=False,
    )
    with pytest.raises(ValueError, match="access-context-mismatch"):
        as_known_slice(
            conn,
            decision_at=P4_TERMS_CUTOFFS["early"],
            request=replace(sample, access_context="shortlisted-nda"),
        )
    with pytest.raises(ValueError, match="licence-purpose-mismatch"):
        as_known_slice(
            conn,
            decision_at=P4_TERMS_CUTOFFS["early"],
            request=replace(sample, licence_purpose="research"),
        )
    wrong_right = manifest.right_ids[P4_DOCUMENT_DATASETS["document:p4-private-ppm"][0]]
    with pytest.raises(ValueError, match="access-context-mismatch"):
        as_known_slice(
            conn,
            decision_at=P4_TERMS_CUTOFFS["early"],
            request=replace(sample, evidence_right_id=wrong_right),
        )


def test_p4_terms_fixture_public_signatures_and_frozen_shapes_are_exact() -> None:
    expected_signatures = {
        build_terms_fixture: ("conn",),
        p4_terms_bundle_request: ("cutoff_name", "access_context"),
        build_p4_terms_bundle: ("conn", "cutoff_name", "access_context"),
        p4_terms_negative_bundle_request: ("case_id",),
        p4_method_policy_bundle_request: (),
        build_p4_method_policy_bundle: ("conn",),
        p4_terms_manifest_payload: ("manifest",),
        p4_terms_manifest_digest: ("manifest",),
        p4_terms_authored_closure_payload: ("conn",),
        p4_terms_authored_closure_digest: ("conn",),
        verify_p4_terms_manifest: ("conn", "manifest"),
    }
    for function, parameters in expected_signatures.items():
        assert tuple(signature(function).parameters) == parameters

    assert tuple(field.name for field in fields(P4BundleCaseContract)) == (
        "case_id",
        "case_kind",
        "cutoff_name",
        "access_context",
        "source_dataset_ids",
        "canonical_entity_ids",
        "request_digest",
        "expected_outcome",
    )
    assert tuple(field.name for field in fields(P4TermsFixtureManifest)) == (
        "fixture_id",
        "fixture_digest",
        "schema_version",
        "schema_digest",
        "digest_status",
        "dataset_ids",
        "document_dataset_ids",
        "scenario_dataset_ids",
        "negative_dataset_id",
        "method_policy_dataset_id",
        "canonical_entity_ids",
        "canonical_entity_records",
        "document_ids",
        "right_ids",
        "right_records",
        "access_contexts",
        "licence_purposes",
        "cutoff_values",
        "version_ids",
        "version_records",
        "partition_records",
        "payload_schema_ids",
        "payload_schema_digests",
        "source_record_ids",
        "evidence_item_ids",
        "evidence_span_ids",
        "observation_ids",
        "source_content_digests",
        "reconstruction_digests",
        "projection_ids",
        "projection_counts",
        "projection_receipt_ids",
        "positive_case_ids",
        "scenario_ids",
        "scenario_family_by_id",
        "negative_case_ids",
        "topology_adversary_ids",
        "predecessor_scaffold_ids",
        "bundle_case_records",
        "slice_receipt_ids",
        "slice_digests",
        "join_receipt_ids",
        "positive_bundle_digests",
        "negative_bundle_results",
        "method_policy_bundle_digest",
        "pit_cases",
        "limitations",
        "current_attestation",
        "live_attestation_ceiling",
        "disclosure",
    )


def _empty_manifest(**overrides) -> P4TermsFixtureManifest:
    mapping_fields = {
        "canonical_entity_records",
        "right_ids",
        "right_records",
        "access_contexts",
        "licence_purposes",
        "cutoff_values",
        "version_records",
        "partition_records",
        "payload_schema_digests",
        "source_content_digests",
        "reconstruction_digests",
        "projection_counts",
        "projection_receipt_ids",
        "scenario_family_by_id",
        "bundle_case_records",
        "slice_receipt_ids",
        "slice_digests",
        "join_receipt_ids",
        "positive_bundle_digests",
        "negative_bundle_results",
        "pit_cases",
    }
    tuple_fields = {
        "dataset_ids",
        "document_dataset_ids",
        "scenario_dataset_ids",
        "canonical_entity_ids",
        "document_ids",
        "version_ids",
        "payload_schema_ids",
        "source_record_ids",
        "evidence_item_ids",
        "evidence_span_ids",
        "observation_ids",
        "projection_ids",
        "positive_case_ids",
        "scenario_ids",
        "negative_case_ids",
        "topology_adversary_ids",
        "predecessor_scaffold_ids",
        "limitations",
    }
    values = {
        field.name: {} if field.name in mapping_fields else () if field.name in tuple_fields else "x"
        for field in fields(P4TermsFixtureManifest)
    }
    values.update(
        fixture_id="p4-terms-authored-v1",
        fixture_digest="a" * 64,
        schema_version="evidence-v1",
        schema_digest="b" * 64,
        digest_status="provisional-unreviewed",
        method_policy_bundle_digest="c" * 64,
        current_attestation="D",
        live_attestation_ceiling="B",
        disclosure="Synthetic authored evidence only.",
    )
    values.update(overrides)
    return P4TermsFixtureManifest(**values)


def test_p4_manifest_recursively_detaches_nested_mapping_and_record_aliases() -> None:
    nested_record = ["entity", {"nested": ["original"]}]
    partition_row = ["partition", ["original"]]
    limitations = ["source closed"]
    manifest = _empty_manifest(
        canonical_entity_records={"entity:p4": nested_record},
        partition_records={"version:p4": [partition_row]},
        limitations=limitations,
    )

    nested_record[1]["nested"].append("mutated")
    partition_row[1].append("mutated")
    limitations.append("mutated")

    assert manifest.canonical_entity_records["entity:p4"] == (
        "entity",
        {"nested": ("original",)},
    )
    assert manifest.partition_records["version:p4"] == (
        ("partition", ("original",)),
    )
    assert manifest.limitations == ("source closed",)
    with pytest.raises(TypeError):
        manifest.canonical_entity_records["new"] = ()


def _built_terms_fixture() -> tuple[sqlite3.Connection, P4TermsFixtureManifest]:
    conn = connect()
    initialize(conn)
    return conn, build_terms_fixture(conn)


def test_manifest_matches_complete_persisted_closure() -> None:
    conn, manifest = _built_terms_fixture()
    second, second_manifest = _built_terms_fixture()

    assert manifest.fixture_digest == p4_terms_manifest_digest(manifest)
    assert manifest.fixture_digest == second_manifest.fixture_digest
    assert p4_terms_authored_closure_digest(conn) == p4_terms_authored_closure_digest(second)
    assert manifest.digest_status == "reviewed-pinned"
    assert manifest.schema_digest == P4_TERMS_AUTHORED_SCHEMA_SHA256
    assert p4_terms_authored_closure_digest(conn) == P4_TERMS_AUTHORED_CLOSURE_SHA256
    assert manifest.fixture_digest == P4_TERMS_AUTHORED_MANIFEST_SHA256
    assert terms_fixture._p4_manifest_verification_failures(conn, manifest) == ()
    assert verify_p4_terms_manifest(conn, manifest)


def test_manifest_digest_ignores_logical_mapping_order() -> None:
    _, manifest = _built_terms_fixture()
    reordered = replace(
        manifest,
        right_ids=dict(reversed(tuple(manifest.right_ids.items()))),
        fixture_digest="0" * 64,
    )
    reordered = replace(reordered, fixture_digest=p4_terms_manifest_digest(reordered))
    assert reordered.fixture_digest == manifest.fixture_digest


def test_manifest_survives_close_and_reopen(tmp_path: Path) -> None:
    path = tmp_path / "p4-terms.sqlite"
    conn = connect(path)
    initialize(conn)
    manifest = build_terms_fixture(conn)
    pristine_manifest_digest = manifest.fixture_digest
    pristine_closure_digest = p4_terms_authored_closure_digest(conn)
    conn.close()

    reopened = connect(path)
    rebuilt = build_terms_fixture(reopened)
    assert rebuilt.fixture_digest == pristine_manifest_digest
    assert p4_terms_authored_closure_digest(reopened) == pristine_closure_digest


def test_manifest_closure_excludes_unrelated_rows_with_p4_request_text() -> None:
    conn, _ = _built_terms_fixture()
    expected = p4_terms_authored_closure_digest(conn)
    snapshot = conn.execute(
        "SELECT * FROM snapshot_manifest ORDER BY snapshot_digest LIMIT 1"
    ).fetchone()
    bundle = conn.execute(
        "SELECT * FROM snapshot_bundle_manifest ORDER BY bundle_digest LIMIT 1"
    ).fetchone()
    conn.execute(
        "INSERT INTO snapshot_manifest VALUES (?,?,?,?)",
        ("snapshot:unrelated", snapshot[1], snapshot[2], snapshot[3]),
    )
    conn.execute(
        "INSERT INTO snapshot_bundle_manifest VALUES (?,?,?,?,?,?,?)",
        ("bundle:unrelated", bundle[1], *tuple(bundle)[2:]),
    )
    alternate_slices = tuple(json.loads(bundle[2])[:-1])
    alternate_bundle_id = digest_id(
        "bundle",
        {
            "request": json.loads(bundle[1]),
            "slices": alternate_slices,
            "join_receipt_id": bundle[4],
        },
    )
    conn.execute(
        "INSERT INTO snapshot_bundle_manifest VALUES (?,?,?,?,?,?,?)",
        (
            alternate_bundle_id,
            bundle[1],
            json.dumps(alternate_slices, separators=(",", ":")),
            *tuple(bundle)[3:],
        ),
    )
    assert p4_terms_authored_closure_digest(conn) == expected


def test_manifest_changes_when_owned_closure_row_changes() -> None:
    conn, manifest = _built_terms_fixture()
    original = p4_terms_authored_closure_digest(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    trigger = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='canonical_entity' "
        "AND lower(sql) LIKE '%before update%'"
    ).fetchone()[0]
    conn.execute(f'DROP TRIGGER "{trigger}"')
    conn.execute(
        "UPDATE canonical_entity SET canonical_name=canonical_name || ' changed' WHERE entity_id=?",
        (P4_CANONICAL_ENTITY_IDS[0],),
    )
    conn.commit()
    assert p4_terms_authored_closure_digest(conn) != original
    assert not verify_p4_terms_manifest(conn, manifest)


def _drop_table_triggers(conn: sqlite3.Connection, table: str) -> None:
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)
    ):
        conn.execute(f'DROP TRIGGER "{row[0]}"')


def test_manifest_is_sensitive_to_each_owned_closure_table() -> None:
    base, manifest = _built_terms_fixture()
    expected = p4_terms_authored_closure_digest(base)
    closure = p4_terms_authored_closure_payload(base)

    for table, rows in closure.items():
        changed = connect()
        base.backup(changed)
        changed.execute("PRAGMA foreign_keys=OFF")
        _drop_table_triggers(changed, table)
        columns = tuple(changed.execute(f"PRAGMA table_info({table})"))
        primary_key = tuple(
            (column[5], index) for index, column in enumerate(columns) if column[5]
        )
        key_indexes = tuple(index for _, index in sorted(primary_key))
        key_names = tuple(columns[index][1] for index in key_indexes)
        target = rows[0]
        changed.execute(
            f"DELETE FROM {table} WHERE " + " AND ".join(f"{name}=?" for name in key_names),
            tuple(target[index] for index in key_indexes),
        )
        changed.commit()
        assert p4_terms_authored_closure_digest(changed) != expected, table
        assert not verify_p4_terms_manifest(changed, manifest), table
        assert manifest.digest_status == "reviewed-pinned"


@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("entity_id", "entity:p4-substituted"),
        ("entity_type", "vehicle"),
        ("canonical_name", "Changed name"),
        ("parent_entity_id", "entity:changed-parent"),
        ("temporal_type", "interval"),
        ("effective_at", "1971-01-01T00:00:00.000000Z"),
        ("effective_from", "1971-01-01T00:00:00.000000Z"),
        ("effective_to", "1972-01-01T00:00:00.000000Z"),
    ),
)
def test_manifest_is_sensitive_to_canonical_entity_identity_fields(
    column: str, value: str,
) -> None:
    conn, manifest = _built_terms_fixture()
    expected = p4_terms_authored_closure_digest(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA ignore_check_constraints=ON")
    _drop_table_triggers(conn, "canonical_entity")
    conn.execute(
        f"UPDATE canonical_entity SET {column}=? WHERE entity_id=?",
        (value, P4_CANONICAL_ENTITY_IDS[0]),
    )
    conn.commit()
    assert p4_terms_authored_closure_digest(conn) != expected
    assert not verify_p4_terms_manifest(conn, manifest)
    assert manifest.digest_status == "reviewed-pinned"


def _reinsert_selected_rows_reversed(
    conn: sqlite3.Connection,
    table: str,
    where: str,
    parameters: tuple[object, ...],
    order_by: str,
) -> None:
    columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE {where} ORDER BY {order_by}", parameters
    ).fetchall()
    triggers = conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=? "
        "AND (lower(sql) LIKE '%before insert%' OR lower(sql) LIKE '%before delete%')",
        (table,),
    ).fetchall()
    for trigger in triggers:
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(f"DELETE FROM {table} WHERE {where}", parameters)
    conn.executemany(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        (tuple(row) for row in reversed(rows)),
    )
    for trigger in triggers:
        conn.execute(trigger[1])


def test_manifest_is_invariant_to_physical_p4_insertion_order() -> None:
    conn, manifest = _built_terms_fixture()
    original = p4_terms_authored_closure_digest(conn)
    closure = p4_terms_authored_closure_payload(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    datasets = tuple(P4_TERMS_DATASETS)
    dataset_marks = ",".join("?" for _ in datasets)
    entities = tuple(P4_CANONICAL_ENTITY_IDS)
    entity_marks = ",".join("?" for _ in entities)
    receipt_ids = tuple(row[0] for row in closure["reconstruction_receipt"])
    receipt_marks = ",".join("?" for _ in receipt_ids)
    item_ids = tuple(row[0] for row in closure["evidence_item"])
    item_marks = ",".join("?" for _ in item_ids)
    observation_ids = tuple(row[0] for row in closure["dataset_observation"])
    observation_marks = ",".join("?" for _ in observation_ids)
    snapshot_ids = tuple(row[0] for row in closure["snapshot_manifest"])
    snapshot_marks = ",".join("?" for _ in snapshot_ids)
    bundle_ids = tuple(row[0] for row in closure["snapshot_bundle_manifest"])
    bundle_marks = ",".join("?" for _ in bundle_ids)
    _reinsert_selected_rows_reversed(conn, "canonical_entity", f"entity_id IN ({entity_marks})", entities, "entity_id")
    _reinsert_selected_rows_reversed(conn, "source_record", f"dataset_id IN ({dataset_marks})", datasets, "source_record_id")
    _reinsert_selected_rows_reversed(conn, "evidence_item", f"evidence_item_id IN ({item_marks})", item_ids, "evidence_item_id")
    _reinsert_selected_rows_reversed(conn, "evidence_span", f"evidence_item_id IN ({item_marks})", item_ids, "evidence_span_id")
    _reinsert_selected_rows_reversed(conn, "dataset_observation", f"dataset_observation_id IN ({observation_marks})", observation_ids, "dataset_observation_id")
    _reinsert_selected_rows_reversed(conn, "snapshot_manifest", f"snapshot_digest IN ({snapshot_marks})", snapshot_ids, "snapshot_digest")
    _reinsert_selected_rows_reversed(conn, "snapshot_bundle_manifest", f"bundle_digest IN ({bundle_marks})", bundle_ids, "bundle_digest")
    _reinsert_selected_rows_reversed(conn, "receipt_seal", f"receipt_id IN ({receipt_marks})", receipt_ids, "receipt_id")
    _reinsert_selected_rows_reversed(conn, "receipt_reference", f"receipt_id IN ({receipt_marks})", receipt_ids, "receipt_id,ordinal")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")

    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert p4_terms_authored_closure_digest(conn) == original
    assert build_terms_fixture(conn).fixture_digest == manifest.fixture_digest
    assert verify_p4_terms_manifest(conn, manifest)


def test_p4_manifest_rejects_non_hex_digest_contracts() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        _empty_manifest(fixture_digest="z" * 64)
    with pytest.raises(ValueError, match="lowercase"):
        _empty_manifest(payload_schema_digests={"schema:p4": "Z" * 64})


def _bundle_case(**overrides) -> P4BundleCaseContract:
    values = {
        "case_id": "early:public",
        "case_kind": "positive",
        "cutoff_name": "early",
        "access_context": "public",
        "source_dataset_ids": (
            "dataset:p4-doc-public-liquid-prospectus",
            "dataset:p4-scenarios-public",
        ),
        "canonical_entity_ids": ("legal-entity:p4-public-case",),
        "request_digest": "d" * 64,
        "expected_outcome": "admitted",
    }
    values.update(overrides)
    return P4BundleCaseContract(**values)


def test_bundle_case_contract_is_detached_and_controlled() -> None:
    source_ids = [
        "dataset:p4-doc-public-liquid-prospectus",
        "dataset:p4-scenarios-public",
    ]
    entity_ids = ["legal-entity:p4-public-case"]
    contract = _bundle_case(
        source_dataset_ids=source_ids,
        canonical_entity_ids=entity_ids,
    )
    source_ids.append("dataset:p4-negative-terms")
    entity_ids.append("case:p4-l1-missing-source-version")
    assert contract.source_dataset_ids == (
        "dataset:p4-doc-public-liquid-prospectus",
        "dataset:p4-scenarios-public",
    )
    assert contract.canonical_entity_ids == ("legal-entity:p4-public-case",)

    invalid_contracts = (
        {"case_kind": "free-form"},
        {"case_id": "not an id"},
        {"cutoff_name": "future"},
        {"access_context": "unknown"},
        {"request_digest": "z" * 64},
        {"source_dataset_ids": ("dataset:p4-scenarios-public",) * 2},
        {
            "source_dataset_ids": (
                "dataset:p4-scenarios-public",
                "dataset:p4-doc-public-liquid-prospectus",
            )
        },
        {"source_dataset_ids": ("dataset:unknown",)},
        {"canonical_entity_ids": ("legal-entity:unknown",)},
        {"expected_outcome": "free-form"},
        {"expected_outcome": "licence-purpose-mismatch"},
    )
    for mutation in invalid_contracts:
        with pytest.raises(ValueError):
            _bundle_case(**mutation)

    refusal = _bundle_case(
        case_id="p4-auth-partial-document-authorization",
        case_kind="expected-refusal",
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
        source_dataset_ids=("dataset:p4-doc-side-letter",),
        canonical_entity_ids=("legal-entity:p4-private-case",),
        expected_outcome="licence-purpose-mismatch",
    )
    assert refusal.expected_outcome == "licence-purpose-mismatch"


def test_fixture_package_exports_reviewed_s7_and_p4_surfaces() -> None:
    import quant_allocator.evidence.fixtures as fixtures

    assert fixtures.__all__ == [
        "P4TermsFixtureManifest",
        "S7_AUTHORED_CLOSURE_CONTRACT_VERSION",
        "S7_CUTOFFS",
        "S7_DATASET_IDS",
        "S7_FIXTURE_ID",
        "S7_SCENARIOS",
        "S7_SCHEMA_SHA256",
        "S7BundleContract",
        "S7FixtureManifest",
        "S7MethodPolicyEvidence",
        "S7ScenarioContract",
        "build_core_fixture",
        "build_p4_method_policy_bundle",
        "build_p4_terms_bundle",
        "build_s7_fixture",
        "build_terms_fixture",
        "s7_authored_closure_digest",
        "s7_manifest_digest",
        "s7_manifest_payload",
        "s7_policy_bundle",
        "s7_source_requests",
        "verify_p4_terms_manifest",
        "verify_s7_manifest",
    ]
