from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


FactKey = tuple[str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class OperationalFact:
    fact_id: str
    manager_entity_id: str
    domain: str
    subject_entity_id: str
    predicate: str
    scope: str
    typed_value: str
    temporal_type: str
    effective_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    source_family: str
    independence_group: str
    assertion_kind: str
    evidence_item_id: str
    evidence_span_id: str
    dataset_observation_id: str
    dataset_version_id: str
    evidence_right_id: str
    entity_relationship_id: str | None

    @property
    def fact_key(self) -> FactKey:
        return (
            self.manager_entity_id,
            self.domain,
            self.subject_entity_id,
            self.predicate,
            self.scope,
        )

    @property
    def effective_time(self) -> datetime:
        value = self.effective_at or self.effective_from
        if value is None:
            raise ValueError("explicit-effective-time-required")
        return value


@dataclass(frozen=True, slots=True)
class ChangeRecord:
    change_id: str
    fact_key: FactKey
    change_kind: str
    before_fact_id: str | None
    after_fact_id: str | None
    effective_at: datetime
    first_known_at: datetime
    receipt_id: str


@dataclass(frozen=True, slots=True)
class EvidenceState:
    fact_key: FactKey
    state: str
    supporting_fact_ids: tuple[str, ...]
    conflicting_fact_ids: tuple[str, ...]
    as_of: datetime
    reason_codes: tuple[str, ...]
    receipt_id: str


@dataclass(frozen=True, slots=True)
class ReunderwritingItem:
    queue_id: str
    action_bucket: str
    domain: str
    fact_key: FactKey
    question: str
    reason_codes: tuple[str, ...]
    evidence_state_receipt_id: str


@dataclass(frozen=True, slots=True)
class OperationalRefusal:
    refusal_id: str
    reason_code: str
    affected_id: str
    output_pointer: str
    receipt_id: str


@dataclass(frozen=True, slots=True)
class OperationalExclusion:
    exclusion_id: str
    reason_code: str
    source_record_id: str
    evidence_item_id: str
    output_pointer: str
    receipt_id: str
