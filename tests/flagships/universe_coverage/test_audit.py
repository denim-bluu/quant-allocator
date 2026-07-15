from quant_allocator.flagships.universe_coverage.audit import (
    HiddenMember,
    TruthPair,
    entity_resolution_audit,
    synthetic_discovery_audit,
)


def test_entity_gate_rederives_wilson_floor() -> None:
    failing = entity_resolution_audit(
        tuple(TruthPair(f"p-{i}", True, True) for i in range(380)),
    )
    passing = entity_resolution_audit(
        tuple(TruthPair(f"p-{i}", True, True) for i in range(381)),
    )
    assert failing.precision_interval[0] < 0.99
    assert passing.precision_interval[0] >= 0.99
    assert not failing.gate_passes and passing.gate_passes


def test_discovery_audit_names_synthetic_denominator() -> None:
    audit = synthetic_discovery_audit(
        observed_ids=("strategy:1", "strategy:3"),
        hidden_universe=(HiddenMember("strategy:1", "cell:a"), HiddenMember("strategy:2", "cell:b")),
    )
    assert (audit.observed_hidden, audit.hidden_denominator, audit.recall) == (1, 2, 0.5)
    assert audit.label == "synthetic fixture recall"
