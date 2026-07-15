from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .checks import refuse
from .model import machine_id

SCHEMA_VERSION = 1


def connect(database: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(database), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.create_function(
        "qa_machine_id",
        2,
        lambda namespace, payload: machine_id(namespace, json.loads(payload)),
        deterministic=True,
    )
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_DDL = r"""
CREATE TABLE IF NOT EXISTS schema_migration(
    version INTEGER PRIMARY KEY, digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payload_schema(
    payload_schema_id TEXT PRIMARY KEY, record_kind TEXT NOT NULL,
    schema_json TEXT NOT NULL, schema_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS canonical_entity(
    entity_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, canonical_name TEXT NOT NULL,
    parent_entity_id TEXT REFERENCES canonical_entity(entity_id),
    temporal_type TEXT NOT NULL DEFAULT 'point', effective_at TEXT DEFAULT '1970-01-01T00:00:00.000000Z',
    effective_from TEXT, effective_to TEXT,
    CHECK ((temporal_type='point' AND effective_at IS NOT NULL AND effective_from IS NULL AND effective_to IS NULL)
        OR (temporal_type='interval' AND effective_at IS NULL AND effective_from IS NOT NULL
            AND (effective_to IS NULL OR effective_from < effective_to)))
);
CREATE TABLE IF NOT EXISTS dataset(
    dataset_id TEXT PRIMARY KEY, label TEXT NOT NULL, source_system TEXT NOT NULL,
    availability_policy TEXT NOT NULL, field_dictionary_version TEXT NOT NULL,
    sensitivity_class TEXT NOT NULL, licence_purpose TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_right(
    evidence_right_id TEXT PRIMARY KEY, right_series_id TEXT NOT NULL, right_version INTEGER NOT NULL,
    dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id), access_context TEXT NOT NULL,
    licence_purpose TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','expired','revoked','superseded')),
    retention_policy TEXT NOT NULL CHECK(retention_policy IN
      ('retain-after-expiry','access-only-while-active')),
    received_at_utc TEXT NOT NULL, entitlement_from TEXT NOT NULL, entitlement_to TEXT,
    supersedes_right_id TEXT UNIQUE REFERENCES evidence_right(evidence_right_id),
    UNIQUE(right_series_id,right_version),
    CHECK(entitlement_to IS NULL OR entitlement_from < entitlement_to)
);
CREATE TABLE IF NOT EXISTS dataset_version(
    dataset_version_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    acquisition_right_id TEXT NOT NULL REFERENCES evidence_right(evidence_right_id),
    version_label TEXT NOT NULL, published_at TEXT, first_observed_at_utc TEXT,
    received_at_utc TEXT, embargo_until TEXT, content_sha256 TEXT NOT NULL,
    delivery_mode TEXT NOT NULL CHECK(delivery_mode IN ('full-snapshot','delta')),
    absence_semantics TEXT NOT NULL CHECK(absence_semantics IN
      ('not-inferable','full-snapshot-means-removed','explicit-tombstone-only')),
    completeness_status TEXT NOT NULL CHECK(completeness_status IN ('complete','incomplete')),
    expected_partition_manifest_sha256 TEXT NOT NULL,
    received_partition_manifest_sha256 TEXT NOT NULL,
    expected_partition_count INTEGER NOT NULL CHECK(expected_partition_count>=0),
    received_partition_count INTEGER NOT NULL CHECK(received_partition_count>=0),
    predecessor_dataset_version_id TEXT REFERENCES dataset_version(dataset_version_id),
    base_dataset_version_id TEXT REFERENCES dataset_version(dataset_version_id),
    reconstruction_manifest_sha256 TEXT, reconstruction_row_count INTEGER,
    UNIQUE(dataset_id,version_label),
    CHECK((completeness_status='complete' AND reconstruction_manifest_sha256 IS NOT NULL
           AND reconstruction_row_count IS NOT NULL)
       OR (completeness_status='incomplete' AND reconstruction_manifest_sha256 IS NULL
           AND reconstruction_row_count IS NULL)),
    CHECK((delivery_mode='full-snapshot' AND base_dataset_version_id IS NULL)
       OR (delivery_mode='delta' AND base_dataset_version_id IS NOT NULL
           AND absence_semantics!='full-snapshot-means-removed'))
);
CREATE TABLE IF NOT EXISTS source_record(
    source_record_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    source_system TEXT NOT NULL, source_record_key TEXT NOT NULL, source_entity_type TEXT NOT NULL,
    UNIQUE(dataset_id,source_system,source_record_key)
);
CREATE TABLE IF NOT EXISTS evidence_item(
    evidence_item_id TEXT PRIMARY KEY, source_record_id TEXT NOT NULL REFERENCES source_record(source_record_id),
    acquisition_right_id TEXT NOT NULL REFERENCES evidence_right(evidence_right_id),
    content_sha256 TEXT NOT NULL, record_kind TEXT NOT NULL,
    payload_schema_id TEXT NOT NULL REFERENCES payload_schema(payload_schema_id),
    canonical_entity_id TEXT REFERENCES canonical_entity(entity_id), temporal_type TEXT NOT NULL,
    effective_at TEXT, effective_from TEXT, effective_to TEXT, as_of_date TEXT NOT NULL,
    published_at TEXT, first_observed_at_utc TEXT, received_at_utc TEXT, embargo_until TEXT,
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES evidence_item(evidence_item_id),
    publication_status TEXT NOT NULL CHECK(publication_status IN ('published','received','withdrawn')),
    access_context TEXT NOT NULL,
    field_dictionary_version TEXT NOT NULL, sensitivity_class TEXT NOT NULL,
    licence_purpose TEXT NOT NULL, payload_json TEXT NOT NULL,
    UNIQUE(source_record_id,version),
    CHECK ((temporal_type='point' AND effective_at IS NOT NULL AND effective_from IS NULL AND effective_to IS NULL)
        OR (temporal_type='interval' AND effective_at IS NULL AND effective_from IS NOT NULL
            AND (effective_to IS NULL OR effective_from < effective_to)))
);
CREATE TABLE IF NOT EXISTS evidence_span(
    evidence_span_id TEXT PRIMARY KEY, evidence_item_id TEXT NOT NULL REFERENCES evidence_item(evidence_item_id),
    json_pointer TEXT NOT NULL, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL,
    span_sha256 TEXT NOT NULL, UNIQUE(evidence_item_id,json_pointer,start_char,end_char)
);
CREATE TABLE IF NOT EXISTS entity_alias(
    alias_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES canonical_entity,
    source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, source_system TEXT NOT NULL,
    alias_text TEXT NOT NULL, temporal_type TEXT NOT NULL, effective_at TEXT,
    effective_from TEXT, effective_to TEXT
);
CREATE TABLE IF NOT EXISTS evidence_entity_link(
    evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    entity_id TEXT NOT NULL REFERENCES canonical_entity, role TEXT NOT NULL,
    PRIMARY KEY(evidence_item_id,entity_id,role)
);
CREATE TABLE IF NOT EXISTS entity_relationship(
    entity_relationship_id TEXT PRIMARY KEY,
    source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span,
    dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    relation_type TEXT NOT NULL, source_entity_id TEXT NOT NULL REFERENCES canonical_entity,
    target_entity_id TEXT NOT NULL REFERENCES canonical_entity, temporal_type TEXT NOT NULL,
    effective_at TEXT, effective_from TEXT, effective_to TEXT, version INTEGER NOT NULL,
    revision_of TEXT UNIQUE REFERENCES entity_relationship
);
CREATE TABLE IF NOT EXISTS dataset_delivery_partition(
    dataset_delivery_partition_id TEXT PRIMARY KEY,
    dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id),
    partition_key TEXT NOT NULL, partition_status TEXT NOT NULL,
    manifest_evidence_item_id TEXT NOT NULL REFERENCES evidence_item(evidence_item_id),
    manifest_evidence_span_id TEXT NOT NULL REFERENCES evidence_span(evidence_span_id),
    received_content_sha256 TEXT, expected_record_count INTEGER NOT NULL,
    received_record_count INTEGER NOT NULL, UNIQUE(dataset_version_id,partition_key),
    CHECK((partition_status='expected-received' AND received_content_sha256 IS NOT NULL
           AND expected_record_count=received_record_count AND expected_record_count>=0)
       OR (partition_status='expected-missing' AND received_content_sha256 IS NULL
           AND received_record_count=0)
       OR (partition_status='unexpected-received' AND received_content_sha256 IS NOT NULL
           AND expected_record_count=0 AND received_record_count>0))
);
CREATE TABLE IF NOT EXISTS dataset_observation(
    dataset_observation_id TEXT PRIMARY KEY,
    dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id),
    evidence_item_id TEXT NOT NULL REFERENCES evidence_item(evidence_item_id),
    observation_status TEXT NOT NULL CHECK(observation_status IN ('present','explicitly-removed')),
    disappearance_reason TEXT, UNIQUE(dataset_version_id,evidence_item_id)
);
CREATE TABLE IF NOT EXISTS dataset_observation_partition_link(
    dataset_observation_partition_link_id TEXT PRIMARY KEY,
    dataset_observation_id TEXT NOT NULL UNIQUE REFERENCES dataset_observation,
    dataset_delivery_partition_id TEXT NOT NULL REFERENCES dataset_delivery_partition,
    UNIQUE(dataset_observation_id,dataset_delivery_partition_id)
);
CREATE TABLE IF NOT EXISTS entity_mapping(
    entity_mapping_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    source_key TEXT NOT NULL, source_label TEXT NOT NULL, source_entity_type TEXT NOT NULL,
    canonical_entity_id TEXT REFERENCES canonical_entity,
    mapping_status TEXT NOT NULL CHECK(mapping_status IN ('resolved','ambiguous','unresolved','rejected')),
    candidate_entity_ids_json TEXT NOT NULL, resolution_rule TEXT NOT NULL, taxonomy_version TEXT NOT NULL,
    temporal_type TEXT NOT NULL, effective_at TEXT, effective_from TEXT, effective_to TEXT,
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES entity_mapping
);
CREATE TABLE IF NOT EXISTS universe_membership(
    universe_membership_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    entity_mapping_id TEXT NOT NULL REFERENCES entity_mapping,
    membership_status TEXT NOT NULL CHECK(membership_status IN ('active','inactive','dead','unknown')),
    taxonomy_version TEXT NOT NULL, temporal_type TEXT NOT NULL, effective_at TEXT,
    effective_from TEXT, effective_to TEXT, version INTEGER NOT NULL,
    revision_of TEXT UNIQUE REFERENCES universe_membership
);
CREATE TABLE IF NOT EXISTS observation_membership_link(
    observation_membership_link_id TEXT PRIMARY KEY,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    universe_membership_id TEXT NOT NULL REFERENCES universe_membership,
    UNIQUE(dataset_observation_id,universe_membership_id)
);
CREATE TABLE IF NOT EXISTS target_grid(
    target_grid_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    source_label TEXT NOT NULL, taxonomy_version TEXT NOT NULL, denominator_rule TEXT NOT NULL,
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES target_grid
);
CREATE TABLE IF NOT EXISTS target_grid_cell(
    target_grid_cell_id TEXT PRIMARY KEY, target_grid_id TEXT NOT NULL REFERENCES target_grid,
    dimensions_json TEXT NOT NULL,
    eligibility_status TEXT NOT NULL CHECK(eligibility_status IN ('eligible','excluded')),
    exclusion_reason TEXT,
    UNIQUE(target_grid_id,dimensions_json)
);
CREATE TABLE IF NOT EXISTS funnel_opportunity(
    funnel_opportunity_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    entity_mapping_id TEXT REFERENCES entity_mapping, source_opportunity_key TEXT NOT NULL,
    source_label TEXT NOT NULL, entity_grain TEXT NOT NULL, product_entity_id TEXT REFERENCES canonical_entity,
    temporal_type TEXT NOT NULL, effective_at TEXT, effective_from TEXT, effective_to TEXT,
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES funnel_opportunity
);
CREATE TABLE IF NOT EXISTS funnel_schema(
    funnel_schema_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    stage_dictionary_json TEXT NOT NULL, transition_rules_json TEXT NOT NULL,
    reason_dictionary_json TEXT NOT NULL,
    completeness_status TEXT NOT NULL CHECK(completeness_status IN ('complete','incomplete')),
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES funnel_schema
);
CREATE TABLE IF NOT EXISTS funnel_cohort(
    funnel_cohort_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    funnel_schema_id TEXT NOT NULL REFERENCES funnel_schema, cohort_label TEXT NOT NULL,
    inclusion_rule_json TEXT NOT NULL, exclusion_rule_json TEXT NOT NULL, entity_grain TEXT NOT NULL,
    entry_stage TEXT NOT NULL, outcome_stage TEXT NOT NULL, accepted_only INTEGER NOT NULL,
    entry_window_from TEXT NOT NULL, entry_window_to TEXT NOT NULL, observation_window_end TEXT NOT NULL,
    completeness_status TEXT NOT NULL CHECK(completeness_status IN ('complete','incomplete')),
    absence_rule TEXT NOT NULL CHECK(absence_rule IN
      ('no-outcome-observed','unknown-because-incomplete','undefined')),
    censor_policy TEXT NOT NULL CHECK(censor_policy IN ('right-censor','none','undefined')),
    right_censor_at TEXT NOT NULL, version INTEGER NOT NULL,
    revision_of TEXT UNIQUE REFERENCES funnel_cohort
);
CREATE TABLE IF NOT EXISTS funnel_event(
    funnel_event_id TEXT PRIMARY KEY, source_evidence_item_id TEXT NOT NULL REFERENCES evidence_item,
    evidence_span_id TEXT NOT NULL REFERENCES evidence_span, dataset_version_id TEXT NOT NULL REFERENCES dataset_version,
    dataset_observation_id TEXT NOT NULL REFERENCES dataset_observation,
    entity_mapping_id TEXT REFERENCES entity_mapping,
    target_grid_cell_id TEXT REFERENCES target_grid_cell,
    funnel_opportunity_id TEXT NOT NULL REFERENCES funnel_opportunity,
    funnel_schema_id TEXT NOT NULL REFERENCES funnel_schema, funnel_stage TEXT NOT NULL,
    event_status TEXT NOT NULL CHECK(event_status IN ('accepted','rejected','withdrawn','pending')),
    reason_code TEXT NOT NULL, effective_at TEXT NOT NULL,
    version INTEGER NOT NULL, revision_of TEXT UNIQUE REFERENCES funnel_event
);
CREATE TABLE IF NOT EXISTS reconstruction_receipt(
    receipt_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, output_locator TEXT NOT NULL,
    input_digest TEXT NOT NULL, output_schema_id TEXT NOT NULL, current_attestation TEXT NOT NULL,
    live_attestation_ceiling TEXT NOT NULL, algorithm_id TEXT NOT NULL,
    algorithm_version TEXT NOT NULL, parameters_sha256 TEXT NOT NULL, value_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipt_seal(
    receipt_id TEXT PRIMARY KEY REFERENCES reconstruction_receipt,
    reference_count INTEGER NOT NULL CHECK(reference_count>=0),
    references_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS funnel_cohort_event_link(
    funnel_cohort_event_link_id TEXT PRIMARY KEY, funnel_cohort_id TEXT NOT NULL REFERENCES funnel_cohort,
    funnel_opportunity_id TEXT NOT NULL REFERENCES funnel_opportunity,
    funnel_event_id TEXT NOT NULL REFERENCES funnel_event,
    inclusion_disposition TEXT NOT NULL CHECK(inclusion_disposition IN ('included','excluded','refused')),
    inclusion_reason_code TEXT NOT NULL,
    evaluation_status TEXT NOT NULL CHECK(evaluation_status IN ('evaluated','refused')),
    censor_status TEXT NOT NULL CHECK(censor_status IN ('observed','right-censored')),
    evaluation_receipt_id TEXT NOT NULL REFERENCES reconstruction_receipt,
    UNIQUE(funnel_cohort_id,funnel_event_id)
);
CREATE TRIGGER IF NOT EXISTS entity_relationship_machine_id BEFORE INSERT ON entity_relationship
WHEN NEW.entity_relationship_id != qa_machine_id('entity-relation',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'relation_type',NEW.relation_type,
  'source_entity_id',NEW.source_entity_id,'target_entity_id',NEW.target_entity_id,
  'temporal_type',NEW.temporal_type,'effective_at',NEW.effective_at,
  'effective_from',NEW.effective_from,'effective_to',NEW.effective_to,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS entity_mapping_machine_id BEFORE INSERT ON entity_mapping
WHEN NEW.entity_mapping_id != qa_machine_id('mapping',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'source_key',NEW.source_key,
  'source_label',NEW.source_label,'taxonomy_version',NEW.taxonomy_version,
  'version',NEW.version,'candidate_entity_ids_json',NEW.candidate_entity_ids_json))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS universe_membership_machine_id BEFORE INSERT ON universe_membership
WHEN NEW.universe_membership_id != qa_machine_id('membership',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'entity_mapping_id',NEW.entity_mapping_id,
  'dataset_version_id',NEW.dataset_version_id,'membership_status',NEW.membership_status,
  'taxonomy_version',NEW.taxonomy_version,'temporal_type',NEW.temporal_type,
  'effective_at',NEW.effective_at,'effective_from',NEW.effective_from,
  'effective_to',NEW.effective_to,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS observation_membership_link_machine_id BEFORE INSERT ON observation_membership_link
WHEN NEW.observation_membership_link_id != qa_machine_id('observation-membership',json_object(
  'dataset_observation_id',NEW.dataset_observation_id,'universe_membership_id',NEW.universe_membership_id))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS target_grid_machine_id BEFORE INSERT ON target_grid
WHEN NEW.target_grid_id != qa_machine_id('grid',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'source_label',NEW.source_label,
  'taxonomy_version',NEW.taxonomy_version,'denominator_rule',NEW.denominator_rule,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS target_grid_cell_machine_id BEFORE INSERT ON target_grid_cell
WHEN NEW.target_grid_cell_id != qa_machine_id('grid-cell',json_object(
  'target_grid_id',NEW.target_grid_id,'dimensions_json',NEW.dimensions_json,
  'eligibility_status',NEW.eligibility_status,'exclusion_reason',NEW.exclusion_reason))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS funnel_opportunity_machine_id BEFORE INSERT ON funnel_opportunity
WHEN NEW.funnel_opportunity_id != qa_machine_id('funnel-opportunity',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'evidence_span_id',NEW.evidence_span_id,
  'entity_mapping_id',NEW.entity_mapping_id,'source_opportunity_key',NEW.source_opportunity_key,
  'product_entity_id',NEW.product_entity_id,'entity_grain',NEW.entity_grain,
  'temporal_type',NEW.temporal_type,'effective_at',NEW.effective_at,
  'effective_from',NEW.effective_from,'effective_to',NEW.effective_to,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS funnel_schema_machine_id BEFORE INSERT ON funnel_schema
WHEN NEW.funnel_schema_id != qa_machine_id('funnel-schema',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'stage_dictionary_json',NEW.stage_dictionary_json,
  'transition_rules_json',NEW.transition_rules_json,'reason_dictionary_json',NEW.reason_dictionary_json,
  'completeness_status',NEW.completeness_status,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS funnel_cohort_machine_id BEFORE INSERT ON funnel_cohort
WHEN NEW.funnel_cohort_id != qa_machine_id('funnel-cohort',json_object(
  'source_evidence_item_id',NEW.source_evidence_item_id,'funnel_schema_id',NEW.funnel_schema_id,
  'cohort_label',NEW.cohort_label,'inclusion_rule_json',NEW.inclusion_rule_json,
  'exclusion_rule_json',NEW.exclusion_rule_json,'entity_grain',NEW.entity_grain,
  'entry_stage',NEW.entry_stage,'outcome_stage',NEW.outcome_stage,'accepted_only',NEW.accepted_only,
  'entry_window_from',NEW.entry_window_from,'entry_window_to',NEW.entry_window_to,
  'observation_window_end',NEW.observation_window_end,'completeness_status',NEW.completeness_status,
  'absence_rule',NEW.absence_rule,'censor_policy',NEW.censor_policy,
  'right_censor_at',NEW.right_censor_at,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS funnel_event_machine_id BEFORE INSERT ON funnel_event
WHEN NEW.funnel_event_id != qa_machine_id('funnel-event',json_object(
  'funnel_opportunity_id',NEW.funnel_opportunity_id,'funnel_schema_id',NEW.funnel_schema_id,
  'source_evidence_item_id',NEW.source_evidence_item_id,'entity_mapping_id',NEW.entity_mapping_id,
  'funnel_stage',NEW.funnel_stage,'reason_code',NEW.reason_code,
  'effective_at',NEW.effective_at,'version',NEW.version))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TRIGGER IF NOT EXISTS funnel_cohort_event_link_machine_id BEFORE INSERT ON funnel_cohort_event_link
WHEN NEW.funnel_cohort_event_link_id != qa_machine_id('funnel-cohort-event',json_object(
  'funnel_cohort_id',NEW.funnel_cohort_id,'funnel_event_id',NEW.funnel_event_id,
  'funnel_opportunity_id',NEW.funnel_opportunity_id,
  'inclusion_disposition',NEW.inclusion_disposition,
  'inclusion_reason_code',NEW.inclusion_reason_code,'evaluation_status',NEW.evaluation_status,
  'censor_status',NEW.censor_status))
BEGIN SELECT RAISE(ABORT,'machine-id-mismatch'); END;
CREATE TABLE IF NOT EXISTS snapshot_manifest(
    snapshot_digest TEXT PRIMARY KEY, request_json TEXT NOT NULL, row_count INTEGER NOT NULL,
    records_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshot_bundle_manifest(
    bundle_digest TEXT PRIMARY KEY, request_json TEXT NOT NULL, slice_digests_json TEXT NOT NULL,
    composite_input_digest TEXT NOT NULL, join_receipt_id TEXT NOT NULL REFERENCES reconstruction_receipt,
    row_count INTEGER NOT NULL, records_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipt_reference(
    receipt_id TEXT NOT NULL REFERENCES reconstruction_receipt, ordinal INTEGER NOT NULL,
    output_field TEXT NOT NULL, reference_type TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK(disposition IN ('included','excluded','refused')),
    reason_code TEXT NOT NULL,
    source_schema_id TEXT NOT NULL REFERENCES payload_schema, source_field TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN
      ('input','filter','denominator','benchmark','term','join','refusal')),
    evidence_item_id TEXT REFERENCES evidence_item,
    source_record_id TEXT REFERENCES source_record,
    dataset_observation_id TEXT REFERENCES dataset_observation,
    evidence_span_id TEXT REFERENCES evidence_span,
    evidence_right_id TEXT REFERENCES evidence_right,
    dataset_version_id TEXT REFERENCES dataset_version,
    universe_membership_id TEXT REFERENCES universe_membership,
    entity_mapping_id TEXT REFERENCES entity_mapping,
    observation_membership_link_id TEXT REFERENCES observation_membership_link,
    entity_relationship_id TEXT REFERENCES entity_relationship,
    target_grid_cell_id TEXT REFERENCES target_grid_cell,
    funnel_opportunity_id TEXT REFERENCES funnel_opportunity,
    funnel_schema_id TEXT REFERENCES funnel_schema,
    funnel_cohort_id TEXT REFERENCES funnel_cohort,
    funnel_event_id TEXT REFERENCES funnel_event,
    funnel_cohort_event_link_id TEXT REFERENCES funnel_cohort_event_link,
    dataset_delivery_partition_id TEXT REFERENCES dataset_delivery_partition,
    dataset_observation_partition_link_id TEXT REFERENCES dataset_observation_partition_link,
    snapshot_digest TEXT REFERENCES snapshot_manifest,
    PRIMARY KEY(receipt_id,ordinal),
    CHECK (
      (evidence_item_id IS NOT NULL)+(source_record_id IS NOT NULL)+
      (dataset_observation_id IS NOT NULL)+(evidence_span_id IS NOT NULL)+
      (evidence_right_id IS NOT NULL)+(dataset_version_id IS NOT NULL)+
      (universe_membership_id IS NOT NULL)+(entity_mapping_id IS NOT NULL)+
      (observation_membership_link_id IS NOT NULL)+(entity_relationship_id IS NOT NULL)+
      (target_grid_cell_id IS NOT NULL)+(funnel_opportunity_id IS NOT NULL)+
      (funnel_schema_id IS NOT NULL)+(funnel_cohort_id IS NOT NULL)+
      (funnel_event_id IS NOT NULL)+(funnel_cohort_event_link_id IS NOT NULL)+
      (dataset_delivery_partition_id IS NOT NULL)+
      (dataset_observation_partition_link_id IS NOT NULL)+(snapshot_digest IS NOT NULL)=1
    )
);
CREATE VIEW IF NOT EXISTS evidence_envelope AS
SELECT i.*, o.dataset_observation_id, o.dataset_version_id, o.observation_status,
       d.dataset_id, d.availability_policy, v.delivery_mode, v.absence_semantics,
       v.completeness_status, v.expected_partition_manifest_sha256,
       v.received_partition_manifest_sha256, v.expected_partition_count,
       v.received_partition_count, v.predecessor_dataset_version_id,
       v.base_dataset_version_id, v.reconstruction_manifest_sha256,
       v.reconstruction_row_count,
       max(CASE d.availability_policy
             WHEN 'public-publication' THEN coalesce(i.published_at,i.first_observed_at_utc)
             WHEN 'manager-receipt' THEN i.received_at_utc
             WHEN 'licensed-receipt' THEN max(coalesce(i.published_at,i.first_observed_at_utc),i.received_at_utc)
             ELSE i.received_at_utc END,
           coalesce(i.embargo_until,'0001-01-01T00:00:00.000000Z'),
           CASE d.availability_policy
             WHEN 'public-publication' THEN coalesce(v.published_at,v.first_observed_at_utc)
             ELSE v.received_at_utc END,
           coalesce(v.embargo_until,'0001-01-01T00:00:00.000000Z'),
           r.received_at_utc, r.entitlement_from,
           vr.received_at_utc, vr.entitlement_from) AS available_at
FROM evidence_item i
JOIN source_record s USING(source_record_id)
JOIN dataset d USING(dataset_id)
JOIN dataset_observation o USING(evidence_item_id)
JOIN dataset_version v USING(dataset_version_id)
JOIN evidence_right r ON r.evidence_right_id=i.acquisition_right_id
JOIN evidence_right vr ON vr.evidence_right_id=v.acquisition_right_id;
"""


_IMMUTABLE = (
    "payload_schema",
    "canonical_entity",
    "dataset",
    "evidence_right",
    "dataset_version",
    "source_record",
    "evidence_item",
    "evidence_span",
    "entity_alias",
    "evidence_entity_link",
    "entity_relationship",
    "dataset_delivery_partition",
    "dataset_observation",
    "dataset_observation_partition_link",
    "entity_mapping",
    "universe_membership",
    "observation_membership_link",
    "target_grid",
    "target_grid_cell",
    "funnel_opportunity",
    "funnel_schema",
    "funnel_cohort",
    "funnel_event",
    "funnel_cohort_event_link",
    "snapshot_manifest",
    "snapshot_bundle_manifest",
    "reconstruction_receipt",
    "receipt_seal",
    "receipt_reference",
)


def _schema_object_digest(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        """SELECT type,name,sql FROM sqlite_master
           WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
           ORDER BY type,name"""
    ).fetchall()
    payload = "\n".join(f"{row['type']}:{row['name']}:{row['sql']}" for row in rows)
    return hashlib.sha256(payload.encode()).hexdigest()


def initialize(conn: sqlite3.Connection) -> None:
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        refuse("foreign-keys-disabled")
    existing = conn.execute(
        "SELECT digest FROM schema_migration WHERE version=?"
        if _has_migration(conn)
        else "SELECT NULL",
        (SCHEMA_VERSION,) if _has_migration(conn) else (),
    ).fetchone()[0]
    if existing is not None and existing != _schema_object_digest(conn):
        refuse("schema-migration-mismatch")
    conn.executescript(_DDL)
    for table in _IMMUTABLE:
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_update_{table} BEFORE UPDATE ON {table} "
            "BEGIN SELECT RAISE(ABORT,'immutable-record'); END"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_delete_{table} BEFORE DELETE ON {table} "
            "BEGIN SELECT RAISE(ABORT,'immutable-record'); END"
        )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_dataset_observation
           BEFORE INSERT ON dataset_observation
           WHEN NOT EXISTS (
             SELECT 1 FROM evidence_item i
             JOIN source_record s USING(source_record_id)
             JOIN dataset_version v ON v.dataset_version_id=NEW.dataset_version_id
             WHERE i.evidence_item_id=NEW.evidence_item_id AND s.dataset_id=v.dataset_id
           )
           BEGIN SELECT RAISE(ABORT,'observation-dataset-mismatch'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS reject_sealed_receipt_reference
           BEFORE INSERT ON receipt_reference
           WHEN EXISTS (SELECT 1 FROM receipt_seal WHERE receipt_id=NEW.receipt_id)
           BEGIN SELECT RAISE(ABORT,'receipt-sealed'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_dataset_version_right
           BEFORE INSERT ON dataset_version
           WHEN NOT EXISTS (
             SELECT 1 FROM evidence_right r JOIN dataset d USING(dataset_id)
             WHERE r.evidence_right_id=NEW.acquisition_right_id
               AND r.dataset_id=NEW.dataset_id
               AND r.licence_purpose=d.licence_purpose
           )
           BEGIN SELECT RAISE(ABORT,'version-right-scope-mismatch'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_item_right
           BEFORE INSERT ON evidence_item
           WHEN NOT EXISTS (
             SELECT 1 FROM source_record s JOIN evidence_right r USING(dataset_id)
             WHERE s.source_record_id=NEW.source_record_id
               AND r.evidence_right_id=NEW.acquisition_right_id
               AND r.access_context=NEW.access_context
               AND r.licence_purpose=NEW.licence_purpose
           )
           BEGIN SELECT RAISE(ABORT,'item-right-scope-mismatch'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_partition_provenance
           BEFORE INSERT ON dataset_delivery_partition
           WHEN NOT EXISTS (
             SELECT 1 FROM dataset_version v
             JOIN evidence_item i ON i.evidence_item_id=NEW.manifest_evidence_item_id
             JOIN source_record s USING(source_record_id)
             JOIN evidence_span sp ON sp.evidence_span_id=NEW.manifest_evidence_span_id
             WHERE v.dataset_version_id=NEW.dataset_version_id
               AND s.dataset_id=v.dataset_id AND sp.evidence_item_id=i.evidence_item_id
           )
           BEGIN SELECT RAISE(ABORT,'partition-provenance-mismatch'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_item_revision
           BEFORE INSERT ON evidence_item WHEN NEW.version>1 AND NOT EXISTS (
             SELECT 1 FROM evidence_item p
             WHERE p.evidence_item_id=NEW.revision_of
               AND p.source_record_id=NEW.source_record_id AND p.version=NEW.version-1
           ) BEGIN SELECT RAISE(ABORT,'revision-gap'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_version_predecessor
           BEFORE INSERT ON dataset_version
           WHEN NEW.predecessor_dataset_version_id IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM dataset_version p
             WHERE p.dataset_version_id=NEW.predecessor_dataset_version_id
               AND p.dataset_id=NEW.dataset_id
               AND NOT EXISTS (
                 SELECT 1 FROM dataset_version c
                 WHERE c.predecessor_dataset_version_id=p.dataset_version_id
               )
           ) BEGIN SELECT RAISE(ABORT,'delta-predecessor-invalid'); END"""
    )
    for table in _PROVENANCE_TABLES:
        conn.execute(
            f"""CREATE TRIGGER IF NOT EXISTS validate_provenance_{table}
                BEFORE INSERT ON {table}
                WHEN NOT EXISTS (
                  SELECT 1 FROM evidence_item i
                  JOIN source_record s USING(source_record_id)
                  JOIN evidence_span sp ON sp.evidence_span_id=NEW.evidence_span_id
                  JOIN dataset_observation o
                    ON o.dataset_observation_id=NEW.dataset_observation_id
                  JOIN dataset_version v
                    ON v.dataset_version_id=NEW.dataset_version_id
                  WHERE i.evidence_item_id=NEW.source_evidence_item_id
                    AND sp.evidence_item_id=i.evidence_item_id
                    AND o.evidence_item_id=i.evidence_item_id
                    AND o.dataset_version_id=v.dataset_version_id
                    AND s.dataset_id=v.dataset_id
                )
                BEGIN SELECT RAISE(ABORT,'projection-provenance-mismatch'); END"""
        )
    for table in _TEMPORAL_PROJECTION_TABLES:
        conn.execute(
            f"""CREATE TRIGGER IF NOT EXISTS validate_temporal_{table}
                BEFORE INSERT ON {table}
                WHEN NOT (
                  (NEW.temporal_type='point' AND NEW.effective_at IS NOT NULL
                   AND NEW.effective_from IS NULL AND NEW.effective_to IS NULL)
                  OR
                  (NEW.temporal_type='interval' AND NEW.effective_at IS NULL
                   AND NEW.effective_from IS NOT NULL
                   AND (NEW.effective_to IS NULL OR NEW.effective_from<NEW.effective_to))
                )
                BEGIN SELECT RAISE(ABORT,'invalid-temporal-shape'); END"""
        )
    for table, identity_rule in _PROJECTION_REVISION_RULES.items():
        identifier = f"{table}_id"
        conn.execute(
            f"""CREATE TRIGGER IF NOT EXISTS validate_revision_{table}
                BEFORE INSERT ON {table}
                WHEN (NEW.version=1 AND (
                       NEW.revision_of IS NOT NULL OR EXISTS (
                         SELECT 1 FROM {table} root
                         WHERE root.version=1
                           AND root.source_evidence_item_id=NEW.source_evidence_item_id
                           AND ({identity_rule.replace("parent.", "root.")})
                       )))
                  OR (NEW.version>1 AND NOT EXISTS (
                    SELECT 1 FROM {table} parent
                    WHERE parent.{identifier}=NEW.revision_of
                      AND parent.version=NEW.version-1
                      AND parent.source_evidence_item_id=NEW.source_evidence_item_id
                      AND ({identity_rule})
                  ))
                BEGIN SELECT RAISE(ABORT,'revision-gap'); END"""
        )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS validate_funnel_event_links
           BEFORE INSERT ON funnel_event
           WHEN NOT EXISTS (
             SELECT 1 FROM funnel_opportunity o JOIN funnel_schema s
             WHERE o.funnel_opportunity_id=NEW.funnel_opportunity_id
               AND s.funnel_schema_id=NEW.funnel_schema_id
               AND o.dataset_version_id=NEW.dataset_version_id
               AND s.dataset_version_id=NEW.dataset_version_id
           )
           BEGIN SELECT RAISE(ABORT,'invalid-funnel-transition'); END"""
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migration(version,digest) VALUES (?,?)",
        (SCHEMA_VERSION, _schema_object_digest(conn)),
    )


def _has_migration(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migration'"
        ).fetchone()
        is not None
    )


def schema_digest(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT digest FROM schema_migration WHERE version=?", (SCHEMA_VERSION,)
    ).fetchone()
    if row is None:
        refuse("schema-not-initialized")
    return str(row[0])


_PROVENANCE_TABLES = (
    "entity_relationship",
    "entity_mapping",
    "universe_membership",
    "target_grid",
    "funnel_opportunity",
    "funnel_schema",
    "funnel_cohort",
    "funnel_event",
)

_TEMPORAL_PROJECTION_TABLES = (
    "entity_relationship",
    "entity_mapping",
    "universe_membership",
    "funnel_opportunity",
)


_PROJECTION_REVISION_RULES = {
    "entity_relationship": (
        "parent.relation_type=NEW.relation_type AND "
        "parent.source_entity_id=NEW.source_entity_id AND "
        "parent.target_entity_id=NEW.target_entity_id"
    ),
    "entity_mapping": "parent.source_key=NEW.source_key",
    "universe_membership": "parent.entity_mapping_id=NEW.entity_mapping_id",
    "target_grid": "parent.source_label=NEW.source_label",
    "funnel_opportunity": "parent.source_opportunity_key=NEW.source_opportunity_key",
    "funnel_schema": "1=1",
    "funnel_cohort": "parent.cohort_label=NEW.cohort_label",
    "funnel_event": (
        "parent.funnel_opportunity_id=NEW.funnel_opportunity_id AND "
        "parent.funnel_stage=NEW.funnel_stage"
    ),
}
