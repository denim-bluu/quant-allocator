from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Mapping, Sequence

from quant_allocator.evidence.model import SnapshotBundle, machine_id
from quant_allocator.flagships.knowledge.operational_evidence import OperationalEvidenceFixture

from .model import (
    ChangeRecord,
    EvidenceState,
    FactKey,
    OperationalExclusion,
    OperationalFact,
    OperationalRefusal,
    ReunderwritingItem,
)

METHOD_VERSION = "e4-operational-state/v1"
DOMAINS = ("organisation", "process", "control", "provider", "incident")
CHANGE_KINDS = tuple(
    sorted(
        (
            "added",
            "modified",
            "explicitly-removed",
            "relationship-started",
            "relationship-ended",
            "corrected",
        )
    )
)
STATE_PRECEDENCE = ("conflicted", "stale", "corroborated", "asserted")
E4_MIN_INDEPENDENT_GROUPS = 2
E4_STALE_DAYS = {
    "organisation": 180,
    "process": 180,
    "control": 365,
    "provider": 365,
    "incident": 90,
}
ACTION_BUCKETS = (
    "immediate-clarification",
    "scheduled-reunderwrite",
    "evidence-refresh",
    "no-action-from-e4",
)
DOMAIN_ORDER = {value: index for index, value in enumerate(DOMAINS)}


@dataclass(frozen=True, slots=True)
class FactContext:
    fact: OperationalFact
    dataset_id: str
    source_record_id: str
    available_at: datetime
    freshness_at: datetime | None
    incident_materiality: str
    observation_status: str
    source_schema_id: str


@dataclass(frozen=True, slots=True)
class OperationalAnalysis:
    facts: tuple[OperationalFact, ...]
    fact_contexts: tuple[FactContext, ...]
    changes: tuple[ChangeRecord, ...]
    states: tuple[EvidenceState, ...]
    queue: tuple[ReunderwritingItem, ...]
    exclusions: tuple[OperationalExclusion, ...]
    refusals: tuple[OperationalRefusal, ...]


def _dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def age_days(freshness_at: datetime, decision_at: datetime) -> int:
    if freshness_at.tzinfo is None or decision_at.tzinfo is None:
        raise ValueError("timezone-aware-datetime-required")
    delta = decision_at.astimezone(UTC) - freshness_at.astimezone(UTC)
    return delta.days


def choose_state(
    *,
    compatible: bool,
    age: int | None,
    stale_threshold: int,
    independence_groups: Sequence[str],
    source_families: Sequence[str],
    assertion_kinds: Sequence[str],
    domain: str,
) -> tuple[str, tuple[str, ...]]:
    if not compatible:
        return "conflicted", ("incompatible-current-values",)
    if age is None:
        return "asserted", ("staleness-unknown",)
    if age > stale_threshold:
        return "stale", ("freshness-threshold-exceeded",)
    groups = tuple(sorted(set(independence_groups)))
    if len(groups) < E4_MIN_INDEPENDENT_GROUPS:
        return "asserted", ("single-independence-group",)
    if domain == "control" and "control-effectiveness-assertion" in assertion_kinds:
        if not {"control-test", "provider-confirmation"}.intersection(source_families):
            return "asserted", ("independent-control-test-required",)
    if domain == "incident" and not {
        "remediation-assertion",
        "closure-assertion",
    }.intersection(assertion_kinds):
        return "asserted", ("remediation-evidence-required",)
    return "corroborated", ("independent-groups-confirm",)


def _span_for(fixture: OperationalEvidenceFixture, item_id: str, pointer: str) -> str:
    row = fixture.conn.execute(
        "SELECT evidence_span_id FROM evidence_span WHERE evidence_item_id=? AND json_pointer=? "
        "ORDER BY evidence_span_id LIMIT 1",
        (item_id, pointer),
    ).fetchone()
    if row is None:
        raise ValueError("operational-field-span-missing")
    return row[0]


def _right_for(fixture: OperationalEvidenceFixture, item_id: str) -> str:
    row = fixture.conn.execute(
        "SELECT acquisition_right_id FROM evidence_item WHERE evidence_item_id=?", (item_id,)
    ).fetchone()
    if row is None:
        raise ValueError("operational-item-missing")
    return row[0]


def _relationship_for(
    fixture: OperationalEvidenceFixture,
    item_id: str,
    observation_id: str,
    predicate: str,
) -> str | None:
    rows = fixture.conn.execute(
        "SELECT entity_relationship_id,relation_type FROM entity_relationship "
        "WHERE source_evidence_item_id=? AND dataset_observation_id=? "
        "ORDER BY entity_relationship_id",
        (item_id, observation_id),
    ).fetchall()
    matches = [row[0] for row in rows if row["relation_type"] == predicate]
    if len(matches) > 1:
        raise ValueError("operational-relationship-ambiguous")
    return matches[0] if matches else None


def _fact_id(payload: Mapping[str, object], row: Mapping[str, object]) -> str:
    fact = payload["fact"]
    temporal = payload["temporal"]
    assert isinstance(fact, Mapping) and isinstance(temporal, Mapping)
    return machine_id(
        "operational-fact",
        {
            "evidence_item_id": row["evidence_item_id"],
            "dataset_observation_id": row["dataset_observation_id"],
            "manager_entity_id": fact["manager_entity_id"],
            "domain": fact["domain"],
            "subject_entity_id": fact["subject_entity_id"],
            "predicate": fact["predicate"],
            "scope": fact["scope"],
            "typed_value": fact["typed_value"],
            "temporal_type": temporal["temporal_type"],
            "effective_at": temporal["effective_at"],
            "effective_from": temporal["effective_from"],
            "effective_to": temporal["effective_to"],
        },
    )


def _context_from_row(
    fixture: OperationalEvidenceFixture,
    row: Mapping[str, object],
    *,
    schemas: Mapping[str, object] | None = None,
) -> FactContext:
    payload = row["payload"]
    fact = payload["fact"]
    temporal = payload["temporal"]
    item_id = str(row["evidence_item_id"])
    schema_by_dataset = schemas or {
        manifest.dataset_id: manifest for manifest in fixture.manifest.source_schema_manifests
    }
    schema = schema_by_dataset[str(row["dataset_id"])]
    effective_at = _dt(temporal["effective_at"]) if temporal["effective_at"] else None
    effective_from = _dt(temporal["effective_from"]) if temporal["effective_from"] else None
    effective_to = _dt(temporal["effective_to"]) if temporal["effective_to"] else None
    if temporal["temporal_type"] == "point" and effective_at is None:
        raise ValueError("inferred-date-refused")
    if temporal["temporal_type"] == "interval" and effective_from is None:
        raise ValueError("inferred-date-refused")
    observation_version = fixture.conn.execute(
        "SELECT dataset_version_id FROM dataset_observation WHERE dataset_observation_id=?",
        (row["dataset_observation_id"],),
    ).fetchone()
    if observation_version is None:
        raise ValueError("operational-observation-missing")
    op_fact = OperationalFact(
        _fact_id(payload, row),
        str(fact["manager_entity_id"]),
        str(fact["domain"]),
        str(fact["subject_entity_id"]),
        str(fact["predicate"]),
        str(fact["scope"]),
        str(fact["typed_value"]),
        str(temporal["temporal_type"]),
        effective_at,
        effective_from,
        effective_to,
        str(fact["source_family"]),
        str(fact["independence_group"]),
        str(fact["assertion_kind"]),
        item_id,
        _span_for(fixture, item_id, schema.typed_value_pointer),
        str(row["dataset_observation_id"]),
        observation_version[0],
        _right_for(fixture, item_id),
        _relationship_for(
            fixture,
            item_id,
            str(row["dataset_observation_id"]),
            str(fact["predicate"]),
        ),
    )
    materiality = fact["incident_materiality"] or "unknown"
    return FactContext(
        op_fact,
        str(row["dataset_id"]),
        str(row["source_record_id"]),
        _dt(row["available_at"]),
        _dt(fact["freshness_at"]) if fact["freshness_at"] else None,
        str(materiality),
        str(row["observation_status"]),
        schema.payload_schema_id,
    )


def normalize_operational_rows(
    fixture: OperationalEvidenceFixture,
    bundles: Sequence[SnapshotBundle],
    *,
    include_unresolved: bool,
) -> tuple[tuple[FactContext, ...], tuple[OperationalExclusion, ...]]:
    schemas = {row.dataset_id: row for row in fixture.manifest.source_schema_manifests}
    contexts: dict[str, FactContext] = {}
    exclusions: dict[str, OperationalExclusion] = {}
    for bundle in bundles:
        if len(bundle.slices) != 1:
            raise ValueError("one-source-bundle-required")
        for row in bundle.slices[0].rows:
            item_id = row["evidence_item_id"]
            if row["canonical_entity_id"] is None:
                identifier = machine_id(
                    "operational-exclusion",
                    {"evidence_item_id": item_id, "reason_code": "canonical-entity-unresolved"},
                )
                exclusions[identifier] = OperationalExclusion(
                    identifier,
                    "canonical-entity-unresolved",
                    row["source_record_id"],
                    item_id,
                    f"/exclusions/{identifier}",
                    "",
                )
                continue
            if not include_unresolved and row["observation_status"] != "present":
                continue
            context = _context_from_row(fixture, row, schemas=schemas)
            contexts.setdefault(
                context.fact.fact_id,
                context,
            )
    return (
        tuple(sorted(contexts.values(), key=lambda item: item.fact.fact_id)),
        tuple(sorted(exclusions.values(), key=lambda item: item.exclusion_id)),
    )


def _current_at(fact: OperationalFact, decision_at: datetime) -> bool:
    if fact.temporal_type == "point":
        return fact.effective_at is not None and fact.effective_at <= decision_at
    assert fact.effective_from is not None
    return fact.effective_from <= decision_at and (
        fact.effective_to is None or decision_at < fact.effective_to
    )


def _compatible(contexts: Sequence[FactContext]) -> bool:
    values = {row.fact.typed_value for row in contexts}
    if len(values) <= 1:
        return True
    kinds = {row.fact.assertion_kind for row in contexts}
    if kinds <= {"remediation-assertion", "closure-assertion"}:
        return True
    return False


def _eligible_independence_groups(
    key: FactKey, contexts: Sequence[FactContext]
) -> tuple[str, ...]:
    groups = {row.fact.independence_group for row in contexts}
    provider_appointment = key[1] == "provider" and key[3] == "uses-provider"
    if not provider_appointment:
        groups.discard("provider-direct")
    return tuple(sorted(groups))


def classify_states(
    contexts: Sequence[FactContext], *, decision_at: datetime
) -> tuple[EvidenceState, ...]:
    grouped: dict[FactKey, list[FactContext]] = defaultdict(list)
    for context in contexts:
        if context.fact.assertion_kind == "method-boundary-policy":
            continue
        if _current_at(context.fact, decision_at):
            grouped[context.fact.fact_key].append(context)
    states: list[EvidenceState] = []
    for key, rows in grouped.items():
        newest = max((row.freshness_at for row in rows if row.freshness_at), default=None)
        age = age_days(newest, decision_at) if newest else None
        state, reasons = choose_state(
            compatible=_compatible(rows),
            age=age,
            stale_threshold=E4_STALE_DAYS[key[1]],
            independence_groups=_eligible_independence_groups(key, rows),
            source_families=tuple(row.fact.source_family for row in rows),
            assertion_kinds=tuple(row.fact.assertion_kind for row in rows),
            domain=key[1],
        )
        fact_ids = tuple(sorted(row.fact.fact_id for row in rows))
        states.append(
            EvidenceState(
                key,
                state,
                fact_ids if state != "conflicted" else (),
                fact_ids if state == "conflicted" else (),
                decision_at,
                reasons,
                "",
            )
        )
    order = {value: index for index, value in enumerate(STATE_PRECEDENCE)}
    return tuple(
        sorted(
            states, key=lambda row: (order[row.state], DOMAIN_ORDER[row.fact_key[1]], row.fact_key)
        )
    )


def derive_changes(contexts: Sequence[FactContext]) -> tuple[ChangeRecord, ...]:
    by_source: dict[str, list[FactContext]] = defaultdict(list)
    for context in contexts:
        by_source[context.source_record_id].append(context)
    changes: list[ChangeRecord] = []
    for source_id, rows in by_source.items():
        for removed in sorted(
            (row for row in rows if row.observation_status == "explicitly-removed"),
            key=lambda row: (row.available_at, row.fact.fact_id),
        ):
            identifier = machine_id(
                "operational-change",
                {
                    "source_record_id": source_id,
                    "before_fact_id": removed.fact.fact_id,
                    "after_fact_id": None,
                    "change_kind": "explicitly-removed",
                    "dataset_version_id": removed.fact.dataset_version_id,
                },
            )
            changes.append(
                ChangeRecord(
                    identifier,
                    removed.fact.fact_key,
                    "explicitly-removed",
                    removed.fact.fact_id,
                    None,
                    removed.available_at,
                    removed.available_at,
                    "",
                )
            )
        ordered = sorted(
            (row for row in rows if row.observation_status == "present"),
            key=lambda row: (row.fact.effective_time, row.available_at, row.fact.fact_id),
        )
        unique: list[FactContext] = []
        seen_items: set[str] = set()
        for row in ordered:
            if row.fact.evidence_item_id not in seen_items:
                unique.append(row)
                seen_items.add(row.fact.evidence_item_id)
        if len(unique) < 2:
            continue
        for before, after in zip(unique, unique[1:]):
            if (
                before.fact.typed_value == after.fact.typed_value
                and before.fact.fact_key == after.fact.fact_key
            ):
                continue
            kind = "corrected" if after.fact.assertion_kind == "closure-assertion" else "modified"
            identifier = machine_id(
                "operational-change",
                {
                    "source_record_id": source_id,
                    "before_fact_id": before.fact.fact_id,
                    "after_fact_id": after.fact.fact_id,
                    "change_kind": kind,
                },
            )
            changes.append(
                ChangeRecord(
                    identifier,
                    after.fact.fact_key,
                    kind,
                    before.fact.fact_id,
                    after.fact.fact_id,
                    after.fact.effective_time,
                    after.available_at,
                    "",
                )
            )
    return tuple(sorted(changes, key=lambda row: (row.effective_at, row.change_id)))


def _queue_bucket(
    state: EvidenceState,
    contexts: Sequence[FactContext],
    changes: Sequence[ChangeRecord],
) -> tuple[str, tuple[str, ...]]:
    rows = [
        row
        for row in contexts
        if row.fact.fact_id in state.supporting_fact_ids + state.conflicting_fact_ids
    ]
    if state.state == "conflicted":
        return "immediate-clarification", ("conflicting-operational-evidence",)
    if state.fact_key[1] == "incident" and any(row.fact.typed_value == "open" for row in rows):
        materialities = {row.incident_materiality for row in rows}
        if materialities.intersection({"critical", "material", "unknown"}):
            return "immediate-clarification", ("open-incident-clarification",)
        return "scheduled-reunderwrite", ("open-non-material-incident",)
    if any(change.fact_key == state.fact_key for change in changes) and state.fact_key[1] in {
        "provider",
        "organisation",
        "process",
        "control",
    }:
        return "scheduled-reunderwrite", ("explicit-operational-change",)
    if state.state == "stale":
        return "evidence-refresh", ("freshness-threshold-exceeded",)
    return "no-action-from-e4", ("no-e4-action-trigger",)


def build_queue(
    states: Sequence[EvidenceState],
    contexts: Sequence[FactContext],
    changes: Sequence[ChangeRecord],
) -> tuple[ReunderwritingItem, ...]:
    rows: list[ReunderwritingItem] = []
    effective_by_key: dict[FactKey, datetime] = {}
    for state in states:
        bucket, reasons = _queue_bucket(state, contexts, changes)
        identifier = machine_id(
            "operational-queue",
            {"fact_key": state.fact_key, "action_bucket": bucket, "reason_codes": reasons},
        )
        subject = state.fact_key[2]
        question = {
            "immediate-clarification": f"Clarify the conflicting or incomplete evidence for {subject}.",
            "scheduled-reunderwrite": f"Re-underwrite the dated operational change for {subject}.",
            "evidence-refresh": f"Obtain refreshed evidence for {subject}.",
            "no-action-from-e4": f"No action is triggered by E4 for {subject}.",
        }[bucket]
        rows.append(
            ReunderwritingItem(
                identifier,
                bucket,
                state.fact_key[1],
                state.fact_key,
                question,
                reasons,
                state.receipt_id,
            )
        )
        change_dates = [change.effective_at for change in changes if change.fact_key == state.fact_key]
        fact_dates = [
            context.fact.effective_time
            for context in contexts
            if context.fact.fact_key == state.fact_key
        ]
        effective_by_key[state.fact_key] = min(change_dates or fact_dates)
    bucket_order = {value: index for index, value in enumerate(ACTION_BUCKETS)}
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                bucket_order[row.action_bucket],
                DOMAIN_ORDER[row.domain],
                effective_by_key[row.fact_key],
                row.queue_id,
            ),
        )
    )


def boundary_refusals(
    contexts: Sequence[FactContext], exclusions: Sequence[OperationalExclusion]
) -> tuple[OperationalRefusal, ...]:
    values: dict[str, tuple[str, str]] = {}
    for exclusion in exclusions:
        values[
            exclusion.refusal_id if hasattr(exclusion, "refusal_id") else exclusion.exclusion_id
        ] = (
            exclusion.reason_code,
            exclusion.evidence_item_id,
        )
    for context in contexts:
        if (
            context.fact.predicate == "effective-date-source"
            and context.fact.typed_value == "filename-only"
        ):
            identifier = machine_id(
                "operational-refusal",
                {"reason_code": "inferred-date-refused", "affected_id": context.fact.fact_id},
            )
            values[identifier] = ("inferred-date-refused", context.fact.fact_id)
        source_count = len(
            {
                row.fact.evidence_item_id
                for row in contexts
                if row.source_record_id == context.source_record_id
            }
        )
        if (
            context.fact.predicate == "operates-process"
            and context.fact.assertion_kind == "current-state-assertion"
            and source_count == 1
        ):
            identifier = machine_id(
                "operational-refusal",
                {"reason_code": "unversioned-change-refused", "affected_id": context.fact.fact_id},
            )
            values.setdefault(identifier, ("unversioned-change-refused", context.fact.fact_id))
    return tuple(
        OperationalRefusal(
            identifier,
            reason,
            affected,
            f"/refusals/data-boundary/{identifier}",
            "",
        )
        for identifier, (reason, affected) in sorted(values.items())
    )


def analyze_operational_evidence(
    fixture: OperationalEvidenceFixture,
    *,
    analytic_bundles: Sequence[SnapshotBundle],
    audit_bundles: Sequence[SnapshotBundle],
    decision_at: datetime,
) -> OperationalAnalysis:
    analytic, _ = normalize_operational_rows(fixture, analytic_bundles, include_unresolved=False)
    audit, exclusions = normalize_operational_rows(fixture, audit_bundles, include_unresolved=True)
    states = classify_states(analytic, decision_at=decision_at)
    changes = derive_changes(audit)
    queue = build_queue(states, analytic, changes)
    refusals = boundary_refusals(audit, exclusions)
    state_order = {value: index for index, value in enumerate(STATE_PRECEDENCE)}
    state_by_key = {state.fact_key: state.state for state in states}
    facts = tuple(
        row.fact
        for row in sorted(
            analytic,
            key=lambda row: (
                state_order.get(state_by_key.get(row.fact.fact_key, ""), len(state_order)),
                DOMAIN_ORDER[row.fact.domain],
                row.fact.fact_key,
                row.fact.fact_id,
            ),
        )
    )
    return OperationalAnalysis(facts, analytic, changes, states, queue, exclusions, refusals)


def with_state_receipts(
    analysis: OperationalAnalysis,
    *,
    state_receipts: Mapping[FactKey, str],
    change_receipts: Mapping[str, str],
    exclusion_receipts: Mapping[str, str],
    refusal_receipts: Mapping[str, str],
) -> OperationalAnalysis:
    states = tuple(replace(row, receipt_id=state_receipts[row.fact_key]) for row in analysis.states)
    changes = tuple(
        replace(row, receipt_id=change_receipts[row.change_id]) for row in analysis.changes
    )
    exclusions = tuple(
        replace(row, receipt_id=exclusion_receipts[row.exclusion_id]) for row in analysis.exclusions
    )
    refusals = tuple(
        replace(row, receipt_id=refusal_receipts[row.refusal_id]) for row in analysis.refusals
    )
    queue = build_queue(states, analysis.fact_contexts, changes)
    return replace(
        analysis,
        changes=changes,
        states=states,
        queue=queue,
        exclusions=exclusions,
        refusals=refusals,
    )
