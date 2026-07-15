from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta

import pytest

from quant_allocator.flagships.operational_change import (
    CHANGE_KINDS,
    DOMAINS,
    E4_MIN_INDEPENDENT_GROUPS,
    E4_STALE_DAYS,
    METHOD_VERSION,
    STATE_PRECEDENCE,
    ChangeRecord,
    EvidenceState,
    OperationalFact,
    ReunderwritingItem,
    age_days,
    choose_state,
)


def test_controlled_contract_is_exact() -> None:
    assert METHOD_VERSION == "e4-operational-state/v1"
    assert DOMAINS == ("organisation", "process", "control", "provider", "incident")
    assert CHANGE_KINDS == (
        "added",
        "corrected",
        "explicitly-removed",
        "modified",
        "relationship-ended",
        "relationship-started",
    )
    assert STATE_PRECEDENCE == ("conflicted", "stale", "corroborated", "asserted")
    assert E4_MIN_INDEPENDENT_GROUPS == 2
    assert E4_STALE_DAYS == {
        "organisation": 180,
        "process": 180,
        "control": 365,
        "provider": 365,
        "incident": 90,
    }


def test_public_types_are_frozen_slotted_and_have_no_score_fields() -> None:
    forbidden = {"score", "odd_score", "rank", "recommendation", "clean", "approved"}
    for cls in (OperationalFact, ChangeRecord, EvidenceState, ReunderwritingItem):
        assert "__slots__" in cls.__dict__
        assert forbidden.isdisjoint(field.name for field in fields(cls))
    fact = OperationalFact(
        "fact:test",
        "manager:test",
        "control",
        "control:test",
        "tested-by",
        "nav-review",
        "test-completed",
        "point",
        datetime(2024, 1, 1, tzinfo=UTC),
        None,
        None,
        "control-test",
        "independent-control-test",
        "control-effectiveness-assertion",
        "item:test",
        "span:test",
        "observation:test",
        "version:test",
        "right:test",
        None,
    )
    with pytest.raises(FrozenInstanceError):
        fact.scope = "changed"  # type: ignore[misc]


def test_staleness_boundary_is_strict() -> None:
    freshness = datetime(2024, 1, 1, tzinfo=UTC)
    assert age_days(freshness, freshness + timedelta(days=90)) == 90
    assert choose_state(
        compatible=True,
        age=90,
        stale_threshold=90,
        independence_groups=("manager-self",),
        source_families=("manager-document",),
        assertion_kinds=("incident-notice",),
        domain="incident",
    ) == ("asserted", ("single-independence-group",))
    assert (
        choose_state(
            compatible=True,
            age=91,
            stale_threshold=90,
            independence_groups=("manager-self",),
            source_families=("manager-document",),
            assertion_kinds=("incident-notice",),
            domain="incident",
        )[0]
        == "stale"
    )


def test_conflict_precedes_corroboration_and_copies_count_once() -> None:
    assert (
        choose_state(
            compatible=False,
            age=1,
            stale_threshold=365,
            independence_groups=("manager-self", "public-regulator"),
            source_families=("manager-document", "public-regulatory-record"),
            assertion_kinds=("change-assertion", "change-assertion"),
            domain="provider",
        )[0]
        == "conflicted"
    )
    assert (
        choose_state(
            compatible=True,
            age=1,
            stale_threshold=365,
            independence_groups=("manager-self", "manager-self"),
            source_families=("manager-document", "manager-document"),
            assertion_kinds=("control-existence-assertion",) * 2,
            domain="control",
        )[0]
        == "asserted"
    )
