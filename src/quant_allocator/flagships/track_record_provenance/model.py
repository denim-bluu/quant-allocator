"""Stable public boundary for the S7 provenance exhibit."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from quant_allocator.evidence.model import canonical_bytes, sha256

if TYPE_CHECKING:
    from quant_allocator.evidence.fixtures.s7 import S7MethodPolicyEvidence


class EntityGrain(StrEnum):
    """Canonical grains that may carry an S7 provenance observation."""

    MANAGER = "manager"
    ADVISER = "adviser"
    STRATEGY = "strategy"
    COMPOSITE = "composite"
    VEHICLE = "vehicle"
    SHARE_CLASS = "share-class"
    MANDATE = "mandate"
    FUND = "fund"


FORBIDDEN_ESTIMATOR_OR_RANKING_FIELDS: tuple[str, ...] = (
    "alpha",
    "sharpe",
    "information_ratio",
    "irr",
    "pme",
    "skill_score",
    "manager_rank",
    "recommendation",
)
"""Outputs owned by estimator, ranking, or recommendation cards rather than S7."""


@dataclass(frozen=True, slots=True)
class TrackObservation:
    """An exact source value whose availability remains substrate-derived."""

    observation_id: str
    source_record_id: str
    evidence_item_id: str
    dataset_observation_id: str
    canonical_entity_id: str
    entity_grain: EntityGrain
    observed_at: date
    value: Decimal
    value_kind: str
    basis_signature_id: str
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.entity_grain, EntityGrain):
            raise ValueError("s7-entity-grain-invalid")
        if not isinstance(self.value, Decimal):
            raise ValueError("s7-decimal-required")
        if self.version < 1:
            raise ValueError("s7-observation-version-invalid")


@dataclass(frozen=True, slots=True)
class PolicyRefusalContract:
    """Fixed policy-refusal metadata carried from the reviewed S7 fixture seam."""

    claim_id: str
    output_schema_id: str
    output_pointer: str
    algorithm_id: str
    algorithm_version: str
    current_attestation: str
    live_attestation_ceiling: str
    access_semantics: str
    policy_id: str
    policy_dataset_id: str
    policy_access_context: str
    policy_dataset_delivery_mode: str
    policy_licence_purpose: str
    policy_payload_schema_id: str
    policy_payload_schema_sha256: str
    policy_payload_sha256: str
    policy_item_id: str
    policy_span_id: str
    policy_observation_id: str
    policy_version_id: str
    policy_right_id: str
    policy_snapshot_digest: str
    policy_slice_receipt_id: str
    policy_bundle_digest: str
    policy_join_receipt_id: str
    policy_join_receipt_binding: str
    policy_included_reference_roles: tuple[tuple[str, str, str, str, str], ...]
    policy_parameter_identity: tuple[str, ...]

    def __post_init__(self) -> None:
        fixed_values = {
            "claim_id": "performance_estimator_refusal",
            "output_schema_id": "s7-provenance-output/v1",
            "output_pointer": "/refusals/performance-estimator",
            "algorithm_id": "s7-method-boundary/v1",
            "algorithm_version": "1",
            "current_attestation": "D",
            "live_attestation_ceiling": "D",
            "access_semantics": "refusal-in-every-context",
            "policy_id": "s7-method-boundary/v1",
            "policy_dataset_id": "dataset:s7-method-boundary",
            "policy_access_context": "public",
            "policy_dataset_delivery_mode": "full-snapshot",
            "policy_licence_purpose": "s7-research",
            "policy_join_receipt_binding": "parameters-and-input-digest-only",
        }
        for field_name, expected in fixed_values.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"s7-policy-refusal-{field_name}-invalid")
        reference_fields = (
            "policy_item_id",
            "policy_span_id",
            "policy_observation_id",
            "policy_version_id",
            "policy_right_id",
            "policy_snapshot_digest",
            "policy_slice_receipt_id",
            "policy_bundle_digest",
            "policy_join_receipt_id",
            "policy_payload_schema_id",
            "policy_payload_schema_sha256",
            "policy_payload_sha256",
        )
        if any(
            not isinstance(getattr(self, field_name), str) or not getattr(self, field_name)
            for field_name in reference_fields
        ):
            raise ValueError("s7-policy-refusal-reference-invalid")
        expected_roles = (
            ("policy-item", "evidence-item", self.policy_item_id, "included", "input"),
            ("policy-span", "evidence-span", self.policy_span_id, "included", "input"),
            ("policy-observation", "dataset-observation", self.policy_observation_id, "included", "input"),
            ("policy-version", "dataset-version", self.policy_version_id, "included", "input"),
            ("policy-right", "evidence-right", self.policy_right_id, "included", "filter"),
            ("policy-snapshot", "snapshot", self.policy_snapshot_digest, "included", "input"),
        )
        if self.policy_included_reference_roles != expected_roles:
            raise ValueError("s7-policy-refusal-reference-roles-invalid")
        expected_parameter_identity = (
            self.policy_item_id,
            self.policy_span_id,
            self.policy_observation_id,
            self.policy_version_id,
            self.policy_right_id,
            self.policy_snapshot_digest,
            self.policy_bundle_digest,
            self.policy_join_receipt_id,
            self.policy_payload_schema_id,
            self.policy_payload_schema_sha256,
            self.policy_payload_sha256,
        )
        if self.policy_parameter_identity != expected_parameter_identity:
            raise ValueError("s7-policy-refusal-parameter-identity-invalid")

    @classmethod
    def from_fixture(
        cls, *, conn: sqlite3.Connection, policy: S7MethodPolicyEvidence
    ) -> PolicyRefusalContract:
        """Create the contract from immutable policy IDs and reviewed fixture rows."""
        version = conn.execute(
            "SELECT dataset_id,acquisition_right_id,delivery_mode FROM dataset_version "
            "WHERE dataset_version_id=?",
            (policy.version_id,),
        ).fetchone()
        if (
            version is None
            or version["dataset_id"] != policy.dataset_id
            or version["acquisition_right_id"] != policy.right_id
            or version["delivery_mode"] != "full-snapshot"
        ):
            raise ValueError("s7-policy-refusal-fixture-delivery-identity-invalid")
        right = conn.execute(
            "SELECT dataset_id,access_context,licence_purpose FROM evidence_right "
            "WHERE evidence_right_id=?",
            (policy.right_id,),
        ).fetchone()
        if right is None or right["dataset_id"] != policy.dataset_id:
            raise ValueError("s7-policy-refusal-fixture-right-identity-invalid")
        item = conn.execute(
            "SELECT sr.dataset_id,i.payload_schema_id,i.content_sha256,i.payload_json "
            "FROM evidence_item i JOIN source_record sr USING(source_record_id) "
            "WHERE i.evidence_item_id=?",
            (policy.item_id,),
        ).fetchone()
        if item is None or item["dataset_id"] != policy.dataset_id:
            raise ValueError("s7-policy-refusal-fixture-payload-identity-invalid")
        schema = conn.execute(
            "SELECT schema_sha256 FROM payload_schema WHERE payload_schema_id=?",
            (item["payload_schema_id"],),
        ).fetchone()
        try:
            payload = json.loads(item["payload_json"])
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("s7-policy-refusal-fixture-payload-identity-invalid") from error
        expected_payload = {
            "policy_id": policy.policy_id,
            "output_pointer": "/refusals/performance-estimator",
            "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
            "statement": (
                "S7 reconstructs lineage and basis-qualified panels; it does not estimate alpha, "
                "Sharpe, IRR, PME, skill, or manager ranking."
            ),
        }
        if (
            schema is None
            or item["payload_schema_id"] != policy.payload_schema_id
            or item["content_sha256"] != policy.payload_sha256
            or item["content_sha256"] != sha256(canonical_bytes(payload))
            or schema["schema_sha256"] != policy.payload_schema_sha256
            or payload != expected_payload
        ):
            raise ValueError("s7-policy-refusal-fixture-payload-identity-invalid")
        span = conn.execute(
            "SELECT evidence_item_id,json_pointer,start_char,end_char,span_sha256 "
            "FROM evidence_span "
            "WHERE evidence_span_id=?",
            (policy.span_id,),
        ).fetchone()
        observation = conn.execute(
            "SELECT evidence_item_id,dataset_version_id FROM dataset_observation "
            "WHERE dataset_observation_id=?",
            (policy.observation_id,),
        ).fetchone()
        if (
            span is None
            or span["evidence_item_id"] != policy.item_id
            or span["json_pointer"] != "/statement"
            or span["start_char"] != 0
            or span["end_char"] != len(expected_payload["statement"])
            or span["span_sha256"]
            != sha256(expected_payload["statement"].encode())
            or expected_payload["statement"][
                span["start_char"] : span["end_char"]
            ]
            != expected_payload["statement"]
            or observation is None
            or observation["evidence_item_id"] != policy.item_id
            or observation["dataset_version_id"] != policy.version_id
        ):
            raise ValueError("s7-policy-refusal-fixture-reference-identity-invalid")

        from quant_allocator.evidence.fixtures.s7 import S7_CUTOFFS
        from quant_allocator.evidence.model import (
            DatasetSliceRequest,
            SnapshotBundleRequest,
        )
        from quant_allocator.evidence.snapshot import as_known_bundle

        policy_bundle = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS["latest"],
                (
                    DatasetSliceRequest(
                        policy.dataset_id,
                        "public",
                        policy.right_id,
                        "s7-research",
                        revision_mode="latest-known",
                        include_unresolved=True,
                    ),
                ),
                ("evidence_item_id",),
                "s7-method-policy-v1",
            ),
        )
        if (
            len(policy_bundle.slices) != 1
            or policy_bundle.slices[0].digest != policy.snapshot_digest
            or policy_bundle.slices[0].receipt_id != policy.slice_receipt_id
            or policy_bundle.bundle_digest != policy.bundle_digest
            or policy_bundle.join_receipt_id != policy.join_receipt_id
            or not any(
                row["evidence_item_id"] == policy.item_id
                and row["dataset_observation_id"] == policy.observation_id
                and row["dataset_version_id"] == policy.version_id
                for row in policy_bundle.slices[0].rows
            )
        ):
            raise ValueError("s7-policy-refusal-fixture-bundle-identity-invalid")
        return cls(
            claim_id="performance_estimator_refusal",
            output_schema_id="s7-provenance-output/v1",
            output_pointer="/refusals/performance-estimator",
            algorithm_id="s7-method-boundary/v1",
            algorithm_version="1",
            current_attestation="D",
            live_attestation_ceiling="D",
            access_semantics="refusal-in-every-context",
            policy_id=policy.policy_id,
            policy_dataset_id=policy.dataset_id,
            policy_access_context=right["access_context"],
            policy_dataset_delivery_mode=version["delivery_mode"],
            policy_licence_purpose=right["licence_purpose"],
            policy_payload_schema_id=item["payload_schema_id"],
            policy_payload_schema_sha256=schema["schema_sha256"],
            policy_payload_sha256=item["content_sha256"],
            policy_item_id=policy.item_id,
            policy_span_id=policy.span_id,
            policy_observation_id=policy.observation_id,
            policy_version_id=policy.version_id,
            policy_right_id=policy.right_id,
            policy_snapshot_digest=policy.snapshot_digest,
            policy_slice_receipt_id=policy.slice_receipt_id,
            policy_bundle_digest=policy.bundle_digest,
            policy_join_receipt_id=policy.join_receipt_id,
            policy_join_receipt_binding="parameters-and-input-digest-only",
            policy_included_reference_roles=(
                ("policy-item", "evidence-item", policy.item_id, "included", "input"),
                ("policy-span", "evidence-span", policy.span_id, "included", "input"),
                (
                    "policy-observation",
                    "dataset-observation",
                    policy.observation_id,
                    "included",
                    "input",
                ),
                (
                    "policy-version",
                    "dataset-version",
                    policy.version_id,
                    "included",
                    "input",
                ),
                ("policy-right", "evidence-right", policy.right_id, "included", "filter"),
                ("policy-snapshot", "snapshot", policy.snapshot_digest, "included", "input"),
            ),
            policy_parameter_identity=(
                policy.item_id,
                policy.span_id,
                policy.observation_id,
                policy.version_id,
                policy.right_id,
                policy.snapshot_digest,
                policy.bundle_digest,
                policy.join_receipt_id,
                policy.payload_schema_id,
                policy.payload_schema_sha256,
                policy.payload_sha256,
            ),
        )

TRACK_RECORD_PROVENANCE_CONTRACT: tuple[tuple[str, str], ...] = (
    ("exhibit_kind", "disclosure-and-refusal"),
    ("estimator_policy", "no-estimator"),
    (
        "prohibited_outputs",
        "returns, risk, alpha, attribution, capacity, and statistical estimates",
    ),
    ("performance_estimator_refusal_pointer", "/refusals/performance-estimator"),
    ("performance_estimator_refusal_access", "refusal-in-every-context"),
)
"""Immutable S7 contract: provenance disclosure only, with an estimator refusal path."""
