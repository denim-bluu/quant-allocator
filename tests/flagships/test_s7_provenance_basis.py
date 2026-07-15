"""Contract tests for S7 basis comparison and comparable-panel admission."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from quant_allocator.flagships.track_record_provenance.basis import (
    BasisBreak,
    BasisEvidenceBinding,
    BasisObservation,
    BasisSegment,
    BasisSignature,
    ComparablePanel,
    FxObservation,
    PanelDecision,
    PanelRow,
    build_basis_panel_from_s7_fixture,
    compare_basis,
    emit_comparable_panel,
)


def _total_return_basis() -> BasisSignature:
    return BasisSignature(
        entity_grain="composite",
        frequency="monthly",
        calendar_id="calendar-month-end",
        return_kind="total-return",
        gross_net_fee_basis="net",
        fee_schedule_version="net-of-management-and-incentive-fees",
        base_currency="USD",
        fx_treatment="native-base",
        fx_series_id=None,
        fx_series_version=None,
        benchmark_id="benchmark:s7-public",
        benchmark_version="v1",
        benchmark_return_kind="total-return",
        valuation_policy_id="valuation-policy:s7-liquid-v1",
        cashflow_convention_id="time-weighted-no-external-flows",
        composite_definition_id="composite-definition:s7-v1",
        composite_membership_version="membership:s7-v1",
    )


def test_compare_basis_refuses_silent_gross_to_net_stitch() -> None:
    left = BasisSegment(
        segment_id="segment:s7-net",
        observation_ids=("observation:s7-net",),
        basis=_total_return_basis(),
    )
    right = BasisSegment(
        segment_id="segment:s7-gross",
        observation_ids=("observation:s7-gross",),
        basis=replace(left.basis, gross_net_fee_basis="gross"),
    )

    assert compare_basis(left, right) == BasisBreak(
        left_segment_id="segment:s7-net",
        right_segment_id="segment:s7-gross",
        changed_fields=("gross_net_fee_basis",),
        disposition="refused",
        reason_codes=("fee-basis-incomparable", "silent-stitch-prohibited"),
    )


def _binding(suffix: str) -> BasisEvidenceBinding:
    return BasisEvidenceBinding(
        dataset_id="dataset:s7-hedge-composite",
        source_record_id=f"source-record:{suffix}",
        evidence_item_id=f"evidence-item:{suffix}",
        dataset_observation_id=f"dataset-observation:{suffix}",
        dataset_version_id="dataset-version:s7-hedge-early",
        evidence_right_id="evidence-right:s7-hedge",
        snapshot_digest="0" * 64,
        source_schema_id="schema:s7-periodic-return-v1",
        source_value_pointer="/return_value",
        mapping_ids=(f"mapping:s7-{suffix}", "mapping:x3-composite"),
        observation_membership_link_ids=(f"observation-membership:{suffix}",),
        membership_ids=("membership:x3-composite",),
        relationship_ids=("relationship:x3-composite-vehicle",),
    )


def test_total_return_panel_preserves_decimals_and_typed_inclusion_receipt() -> None:
    basis = _total_return_basis()
    observations = tuple(
        BasisObservation(
            observation_id=f"observation:s7-{month}",
            segment_id="segment:s7-net",
            canonical_entity_id="composite:x3-00",
            observed_at=date(2024, month, 29 if month == 2 else 31),
            value=Decimal(value),
            value_kind="periodic-return",
            basis=basis,
            source_currency="USD",
            evidence=_binding(str(month)),
        )
        for month, value in ((1, "0.0060"), (2, "0.0100"))
    )

    decision = emit_comparable_panel(
        observations,
        panel_kind="total-return-series",
        entity_grain="composite",
        bundle_digest="1" * 64,
        join_receipt_id="receipt:s7-hedge-join",
    )

    assert decision.refusal is None
    assert decision.panel == ComparablePanel(
        panel_kind="total-return-series",
        entity_grain="composite",
        canonical_entity_id="composite:x3-00",
        native_frequency="monthly",
        basis_signature=basis,
        rows=(
            PanelRow(
                "observation:s7-1",
                date(2024, 1, 31),
                Decimal("0.0060"),
                Decimal("0.0060"),
                None,
            ),
            PanelRow(
                "observation:s7-2",
                date(2024, 2, 29),
                Decimal("0.0100"),
                Decimal("0.0100"),
                None,
            ),
        ),
        row_ids=("observation:s7-1", "observation:s7-2"),
        excluded_row_ids=(),
        receipt_id=decision.receipt.receipt_id,
    )
    assert {
        reference.reference_id
        for reference in decision.receipt.references
        if reference.reference_type == "dataset-observation"
    } == {
        "dataset-observation:1",
        "dataset-observation:2",
    }
    assert all(
        reference.disposition == "included"
        for reference in decision.receipt.references
    )


def test_comparable_panel_refuses_multiple_exact_entities_at_same_grain() -> None:
    basis = _total_return_basis()
    left = BasisObservation(
        "observation:s7-entity-left",
        "segment:s7-entity-left",
        "composite:x3-00",
        date(2024, 1, 31),
        Decimal("0.0060"),
        "periodic-return",
        basis,
        "USD",
        _binding("entity-left"),
    )
    right = BasisObservation(
        "observation:s7-entity-right",
        "segment:s7-entity-right",
        "composite:x3-01",
        date(2024, 2, 29),
        Decimal("0.0100"),
        "periodic-return",
        basis,
        "USD",
        _binding("entity-right"),
    )

    decision = emit_comparable_panel(
        (left, right),
        panel_kind="total-return-series",
        entity_grain="composite",
        bundle_digest="1" * 64,
        join_receipt_id="receipt:s7-hedge-join",
    )

    assert decision.panel is None
    assert decision.refusal is not None
    assert decision.refusal.reason_code == "entity-grain-mismatch"
    assert decision.refusal.reason_codes[0] == "entity-grain-mismatch"
    assert decision.receipt.claim_id == "s7_comparable_panel_refusal"
    assert decision.receipt.output_locator == "/panel/refusal"
    assert not {
        reference.output_field
        for reference in decision.receipt.references
    } & {"/panel", "/panel/rows"}


def test_panel_receipt_binds_derived_exact_canonical_entity_identity() -> None:
    original = BasisObservation(
        "observation:s7-entity-substitution",
        "segment:s7-entity-substitution",
        "composite:x3-00",
        date(2024, 1, 31),
        Decimal("0.0060"),
        "periodic-return",
        _total_return_basis(),
        "USD",
        _binding("entity-substitution"),
    )
    substituted = replace(original, canonical_entity_id="composite:x3-01")

    original_decision = emit_comparable_panel(
        (original,),
        panel_kind="total-return-series",
        entity_grain="composite",
        bundle_digest="1" * 64,
        join_receipt_id="receipt:s7-hedge-join",
    )
    substituted_decision = emit_comparable_panel(
        (substituted,),
        panel_kind="total-return-series",
        entity_grain="composite",
        bundle_digest="1" * 64,
        join_receipt_id="receipt:s7-hedge-join",
    )

    assert original_decision.panel is not None
    assert substituted_decision.panel is not None
    assert original_decision.panel.canonical_entity_id == "composite:x3-00"
    assert substituted_decision.panel.canonical_entity_id == "composite:x3-01"
    assert original_decision.receipt.references == substituted_decision.receipt.references
    assert original_decision.receipt.input_digest != substituted_decision.receipt.input_digest
    assert (
        original_decision.receipt.parameters_sha256
        != substituted_decision.receipt.parameters_sha256
    )
    assert original_decision.receipt.value_sha256 != substituted_decision.receipt.value_sha256
    assert original_decision.receipt.receipt_id != substituted_decision.receipt.receipt_id


@pytest.mark.parametrize(
    ("panel_kind", "right_basis", "reason_code", "reason_codes"),
    (
        (
            "total-return-series",
            replace(_total_return_basis(), fee_schedule_version=None),
            "fee-basis-incomparable",
            ("fee-basis-incomparable", "silent-stitch-prohibited"),
        ),
        (
            "total-return-series",
            replace(_total_return_basis(), base_currency="EUR"),
            "fx-series-missing",
            ("fx-series-missing", "silent-stitch-prohibited"),
        ),
        (
            "excess-return-series",
            replace(_total_return_basis(), benchmark_version="v2"),
            "benchmark-basis-incomparable",
            ("benchmark-basis-incomparable", "silent-stitch-prohibited"),
        ),
        (
            "total-return-series",
            replace(
                _total_return_basis(),
                frequency="quarterly",
                calendar_id="calendar-quarter-end",
                return_kind="valuation-based-change",
                valuation_policy_id="valuation-policy:s7-credit-quarterly-v1",
            ),
            "frequency-calendar-incomparable",
            (
                "frequency-calendar-incomparable",
                "valuation-basis-incomparable",
                "comparison-kind-incompatible",
                "silent-stitch-prohibited",
            ),
        ),
    ),
)
def test_panel_refusal_precedence_is_typed_and_receipted(
    panel_kind: str,
    right_basis: BasisSignature,
    reason_code: str,
    reason_codes: tuple[str, ...],
) -> None:
    left = BasisObservation(
        "observation:s7-left",
        "segment:s7-left",
        "composite:x3-00",
        date(2024, 1, 31),
        Decimal("0.0060"),
        "periodic-return",
        _total_return_basis(),
        "USD",
        _binding("left"),
    )
    right = BasisObservation(
        "observation:s7-right",
        "segment:s7-right",
        "composite:x3-00",
        date(2024, 2, 29),
        Decimal("0.0100"),
        "periodic-return",
        right_basis,
        "USD",
        _binding("right"),
    )

    decision = emit_comparable_panel(
        (left, right),
        panel_kind=panel_kind,
        entity_grain="composite",
        bundle_digest="1" * 64,
        join_receipt_id="receipt:s7-hedge-join",
    )

    assert decision.panel is None
    assert decision.refusal is not None
    assert decision.refusal.reason_code == reason_code
    assert decision.refusal.reason_codes == reason_codes
    assert decision.refusal.receipt_id == decision.receipt.receipt_id
    assert all(
        reference.disposition == "refused"
        and reference.reason_code == reason_code
        for reference in decision.receipt.references
    )


def test_receipted_fx_conversion_uses_exact_decimal_formula() -> None:
    converted_basis = replace(
        _total_return_basis(),
        entity_grain="vehicle",
        base_currency="USD",
        fx_treatment="unhedged-converted",
        fx_series_id="s7-fx-eur-usd",
        fx_series_version="1",
        fx_rule_id="s7-fx-rule-v1",
    )
    local = BasisObservation(
        "observation:s7-eur",
        "segment:s7-eur",
        "vehicle:x3-00",
        date(2024, 2, 29),
        Decimal("0.0060"),
        "periodic-return",
        converted_basis,
        "EUR",
        _binding("eur"),
    )
    fx = FxObservation(
        observation_id="observation:s7-fx-v1",
        observed_at=date(2024, 2, 29),
        value=Decimal("0.0200"),
        series_id="s7-fx-eur-usd",
        version="1",
        source_currency="EUR",
        target_currency="USD",
        quotation_direction="base-per-quote",
        hedge_treatment="unhedged",
        rule_id="s7-fx-rule-v1",
        evidence=replace(
            _binding("fx-v1"),
            dataset_id="dataset:s7-fx",
            source_schema_id="schema:s7-fx-return-v1",
            source_value_pointer="/fx_return",
            mapping_ids=(),
            observation_membership_link_ids=(),
            membership_ids=(),
            relationship_ids=(),
        ),
    )

    decision = emit_comparable_panel(
        (local,),
        panel_kind="total-return-series",
        entity_grain="vehicle",
        bundle_digest="2" * 64,
        join_receipt_id="receipt:s7-public-join",
        fx_observations=(fx,),
    )

    assert decision.refusal is None
    assert decision.panel is not None
    assert decision.panel.rows == (
        PanelRow(
            "observation:s7-eur",
            date(2024, 2, 29),
            Decimal("0.0060"),
            Decimal("0.02612000"),
            "observation:s7-fx-v1",
        ),
    )
    assert {
        reference.reference_id
        for reference in decision.receipt.references
        if reference.reference_type == "dataset-observation"
    } == {
        "dataset-observation:eur",
        "dataset-observation:fx-v1",
    }


def test_cashflow_nav_panel_preserves_irregular_native_rows_without_estimator() -> None:
    basis = BasisSignature(
        entity_grain="vehicle",
        frequency="irregular-cashflow-plus-quarterly-nav",
        calendar_id="native-dated",
        return_kind="cashflow-nav-lineage",
        gross_net_fee_basis="not-applicable",
        fee_schedule_version=None,
        base_currency="USD",
        fx_treatment="native-base",
        fx_series_id=None,
        fx_series_version=None,
        benchmark_id=None,
        benchmark_version=None,
        benchmark_return_kind=None,
        valuation_policy_id="valuation-policy:s7-private-quarterly-v1",
        cashflow_convention_id="investor-perspective-signed-cashflow",
        composite_definition_id=None,
        composite_membership_version=None,
    )
    observations = (
        BasisObservation(
            "observation:s7-call",
            "segment:s7-private",
            "vehicle:x3-08",
            date(2024, 1, 17),
            Decimal("-12000000.00"),
            "cashflow",
            basis,
            "USD",
            _binding("call"),
        ),
        BasisObservation(
            "observation:s7-nav",
            "segment:s7-private",
            "vehicle:x3-08",
            date(2024, 3, 31),
            Decimal("85000000.00"),
            "nav",
            basis,
            "USD",
            _binding("nav"),
        ),
    )

    decision = emit_comparable_panel(
        observations,
        panel_kind="cashflow-nav-lineage",
        entity_grain="vehicle",
        bundle_digest="3" * 64,
        join_receipt_id="receipt:s7-private-join",
    )

    assert decision.refusal is None
    assert decision.panel is not None
    assert decision.panel.native_frequency == "irregular-cashflow-plus-quarterly-nav"
    assert tuple((row.observed_at, row.admitted_value) for row in decision.panel.rows) == (
        (date(2024, 1, 17), Decimal("-12000000.00")),
        (date(2024, 3, 31), Decimal("85000000.00")),
    )
    forbidden = {
        "alpha",
        "sharpe",
        "information_ratio",
        "irr",
        "pme",
        "skill_score",
        "manager_rank",
        "recommendation",
    }
    assert forbidden.isdisjoint(ComparablePanel.__dataclass_fields__)
    assert forbidden.isdisjoint(PanelRow.__dataclass_fields__)


def test_real_public_fx_panel_reconciles_selected_row_and_shared_receipt() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    decision = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="latest",
        panel_kind="total-return-series",
        source_product_key="s7-public-eur",
        base_currency="USD",
    )

    assert decision.refusal is None
    assert decision.panel is not None
    assert decision.panel.rows[0].source_value == Decimal("0.0060")
    assert decision.panel.rows[0].admitted_value == Decimal("0.02410800")
    assert decision.panel.rows[0].fx_observation_id is not None
    observation_references = {
        reference.reference_id
        for reference in decision.receipt.references
        if reference.reference_type == "dataset-observation"
    }
    assert observation_references == {
        decision.panel.row_ids[0],
        decision.panel.rows[0].fx_observation_id,
    }
    expected_version_references = {
        str(
            conn.execute(
                "SELECT dataset_version_id FROM dataset_observation "
                "WHERE dataset_observation_id=?",
                (observation_id,),
            ).fetchone()[0]
        )
        for observation_id in observation_references
    }
    version_references = {
        reference.reference_id
        for reference in decision.receipt.references
        if reference.reference_type == "dataset-version"
    }
    selected_public_version = str(
        conn.execute(
            "SELECT dataset_version_id FROM dataset_version "
            "WHERE dataset_id='dataset:s7-public-registered' AND version_label='latest'"
        ).fetchone()[0]
    )
    assert version_references == expected_version_references
    assert selected_public_version not in version_references
    assert conn.execute(
        "SELECT 1 FROM reconstruction_receipt WHERE receipt_id=?",
        (decision.receipt.receipt_id,),
    ).fetchone()


def test_real_panel_reconciles_and_authenticates_ambiguous_exclusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L8 is excluded with exact evidence, and L21 omission fails card verification."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.lineage import store_receipt, verify_receipt
    from quant_allocator.evidence.model import ReconstructionReceipt, digest_id
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance import basis as basis_module

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    mappings = {
        str(row["source_key"]): row
        for row in conn.execute(
            "SELECT mapping.source_key,mapping.entity_mapping_id,"
            "mapping.dataset_observation_id,mapping.mapping_status "
            "FROM entity_mapping mapping "
            "JOIN dataset_version version USING(dataset_version_id) "
            "WHERE version.dataset_id='dataset:s7-hedge-composite' "
            "AND mapping.source_key IN ('s7-hf-main:2024-01','s7-hf-ambiguous')"
        )
    }
    ambiguous = mappings["s7-hf-ambiguous"]
    valid = mappings["s7-hf-main:2024-01"]
    assert ambiguous["mapping_status"] == "ambiguous"

    captured_verification: dict[str, object] = {}
    verify_panel = getattr(basis_module, "verify_s7_panel_receipt", None)
    if verify_panel is not None:

        def capture_verification(
            connection: object, **kwargs: object
        ) -> None:
            captured_verification.update(kwargs)
            verify_panel(connection, **kwargs)

        monkeypatch.setattr(
            basis_module,
            "verify_s7_panel_receipt",
            capture_verification,
        )

    decision = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="hedge-fund",
        cutoff_name="latest",
        panel_kind="total-return-series",
        source_product_key=None,
        source_record_keys=("s7-hf-main:2024-01", "s7-hf-ambiguous"),
        base_currency="USD",
    )

    assert decision.refusal is None
    assert decision.panel is not None
    exclusions = getattr(decision.panel, "exclusions", ())
    assert len(exclusions) == 1
    exclusion = exclusions[0]
    ambiguous_id = str(ambiguous["dataset_observation_id"])
    assert decision.panel.row_ids == (str(valid["dataset_observation_id"]),)
    assert decision.panel.excluded_row_ids == (ambiguous_id,)
    assert exclusion.observation_id == ambiguous_id
    assert exclusion.reason_code == "entity-mapping-ambiguous"
    assert exclusion.evidence.mapping_ids == (str(ambiguous["entity_mapping_id"]),)
    assert set(decision.panel.row_ids).isdisjoint(decision.panel.excluded_row_ids)
    expected_excluded_references = {
        ("source-record", exclusion.evidence.source_record_id),
        ("evidence-item", exclusion.evidence.evidence_item_id),
        ("dataset-observation", exclusion.evidence.dataset_observation_id),
        ("dataset-version", exclusion.evidence.dataset_version_id),
        ("evidence-right", exclusion.evidence.evidence_right_id),
        ("snapshot", exclusion.evidence.snapshot_digest),
        ("entity-mapping", str(ambiguous["entity_mapping_id"])),
    }
    excluded_references = {
        (reference.reference_type, reference.reference_id)
        for reference in decision.receipt.references
        if reference.disposition == "excluded"
        and reference.reason_code == "entity-mapping-ambiguous"
    }
    assert excluded_references == expected_excluded_references
    assert verify_panel is not None
    assert captured_verification

    omitted_references = tuple(
        reference
        for reference in decision.receipt.references
        if reference.disposition != "excluded"
    )
    omitted_header = {
        "claim_id": decision.receipt.claim_id,
        "output_locator": decision.receipt.output_locator,
        "input_digest": decision.receipt.input_digest,
        "output_schema_id": decision.receipt.output_schema_id,
        "current_attestation": decision.receipt.current_attestation,
        "live_attestation_ceiling": decision.receipt.live_attestation_ceiling,
        "algorithm_id": decision.receipt.algorithm_id,
        "algorithm_version": decision.receipt.algorithm_version,
        "parameters_sha256": decision.receipt.parameters_sha256,
        "value_sha256": decision.receipt.value_sha256,
        "references": omitted_references,
    }
    omitted_receipt = ReconstructionReceipt(
        digest_id("receipt", omitted_header),
        decision.receipt.claim_id,
        decision.receipt.output_locator,
        decision.receipt.input_digest,
        decision.receipt.output_schema_id,
        decision.receipt.current_attestation,
        decision.receipt.live_attestation_ceiling,
        decision.receipt.algorithm_id,
        decision.receipt.algorithm_version,
        decision.receipt.parameters_sha256,
        decision.receipt.value_sha256,
        omitted_references,
    )
    store_receipt(conn, omitted_receipt)
    bundle = captured_verification["bundle"]
    verify_receipt(conn, omitted_receipt.receipt_id, bundle)

    verification_kwargs = {
        key: value
        for key, value in captured_verification.items()
        if key != "receipt_id"
    }
    with pytest.raises(ValueError, match="s7-panel-receipt-closure-mismatch"):
        verify_panel(
            conn,
            receipt_id=omitted_receipt.receipt_id,
            **verification_kwargs,
        )


def test_real_fx_and_private_nav_preserve_early_late_versions() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    def panel_version_ids(decision: PanelDecision) -> set[str]:
        return {
            reference.reference_id
            for reference in decision.receipt.references
            if reference.reference_type == "dataset-version"
        }

    early_fx = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="early",
        panel_kind="total-return-series",
        source_product_key="s7-public-eur",
        base_currency="USD",
    )
    late_fx = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="latest",
        panel_kind="total-return-series",
        source_product_key="s7-public-eur",
        base_currency="USD",
    )
    assert early_fx.panel is not None and late_fx.panel is not None
    assert early_fx.panel.rows[0].source_value == late_fx.panel.rows[0].source_value == Decimal(
        "0.0060"
    )
    assert early_fx.panel.rows[0].admitted_value == Decimal("0.02612000")
    assert late_fx.panel.rows[0].admitted_value == Decimal("0.02410800")
    assert early_fx.panel.rows[0].fx_observation_id != late_fx.panel.rows[0].fx_observation_id
    assert panel_version_ids(early_fx) != panel_version_ids(late_fx)

    early_private = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="private-market",
        cutoff_name="early",
        panel_kind="cashflow-nav-lineage",
        source_product_key="s7-private-main",
        base_currency="USD",
    )
    late_private = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="private-market",
        cutoff_name="latest",
        panel_kind="cashflow-nav-lineage",
        source_product_key="s7-private-main",
        base_currency="USD",
    )
    assert early_private.panel is not None and late_private.panel is not None
    early_nav = next(
        row for row in early_private.panel.rows if row.observed_at == date(2024, 3, 31)
    )
    late_nav = next(
        row for row in late_private.panel.rows if row.observed_at == date(2024, 3, 31)
    )
    assert early_nav.admitted_value == Decimal("85000000.00")
    assert late_nav.admitted_value == Decimal("80000000.00")
    assert early_nav.observation_id != late_nav.observation_id
    assert panel_version_ids(early_private) != panel_version_ids(late_private)

    for decision in (early_fx, late_fx, early_private, late_private):
        assert decision.refusal is None
        assert decision.panel is not None
        observation_ids = (
            *decision.panel.row_ids,
            *(
                row.fx_observation_id
                for row in decision.panel.rows
                if row.fx_observation_id is not None
            ),
        )
        expected_versions = {
            str(
                conn.execute(
                    "SELECT dataset_version_id FROM dataset_observation "
                    "WHERE dataset_observation_id=?",
                    (observation_id,),
                ).fetchone()[0]
            )
            for observation_id in observation_ids
        }
        assert panel_version_ids(decision) == expected_versions


def test_real_fixture_basis_cases_and_private_native_panel() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    fee = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="hedge-fund",
        cutoff_name="latest",
        panel_kind="total-return-series",
        source_product_key=None,
        source_record_keys=("s7-hf-fee-unresolved",),
        base_currency="USD",
    )
    benchmark = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="latest",
        panel_kind="excess-return-series",
        source_product_key=None,
        source_record_keys=("s7-public-benchmark-v1", "s7-public-benchmark-v2"),
        base_currency="USD",
    )
    credit = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="credit",
        cutoff_name="latest",
        panel_kind="total-return-series",
        source_product_key=None,
        source_record_keys=("s7-credit-liquid", "s7-credit-private"),
        base_currency="USD",
    )
    excess = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="latest",
        panel_kind="excess-return-series",
        source_product_key=None,
        source_record_keys=(
            "s7-public-main:2024-01",
            "s7-public-main:2024-02",
            "s7-public-main:2024-03",
        ),
        base_currency="USD",
    )
    private = build_basis_panel_from_s7_fixture(
        conn,
        manifest,
        scenario="private-market",
        cutoff_name="latest",
        panel_kind="cashflow-nav-lineage",
        source_product_key="s7-private-main",
        base_currency="USD",
    )

    assert fee.refusal is not None
    assert fee.refusal.reason_code == "fee-basis-incomparable"
    assert benchmark.refusal is not None
    assert benchmark.refusal.reason_code == "benchmark-basis-incomparable"
    assert credit.refusal is not None
    assert credit.refusal.reason_code == "frequency-calendar-incomparable"
    assert excess.panel is not None
    assert len(excess.panel.rows) == 3
    assert private.panel is not None
    assert tuple(row.observed_at for row in private.panel.rows) == (
        date(2024, 1, 17),
        date(2024, 2, 12),
        date(2024, 3, 8),
        date(2024, 3, 31),
    )
    assert tuple(row.admitted_value for row in private.panel.rows) == (
        Decimal("-12000000.00"),
        Decimal("-175000.00"),
        Decimal("3500000.00"),
        Decimal("80000000.00"),
    )
    for panel_decision in (excess, private):
        assert panel_decision.panel is not None
        expected_version_references = {
            str(
                conn.execute(
                    "SELECT dataset_version_id FROM dataset_observation "
                    "WHERE dataset_observation_id=?",
                    (observation_id,),
                ).fetchone()[0]
            )
            for observation_id in panel_decision.panel.row_ids
        }
        version_references = {
            reference.reference_id
            for reference in panel_decision.receipt.references
            if reference.reference_type == "dataset-version"
        }
        assert version_references == expected_version_references

    private_call_id = next(
        row.observation_id
        for row in private.panel.rows
        if row.observed_at == date(2024, 1, 17)
    )
    private_call_version = str(
        conn.execute(
            "SELECT dataset_version_id FROM dataset_observation "
            "WHERE dataset_observation_id=?",
            (private_call_id,),
        ).fetchone()[0]
    )
    selected_private_version = str(
        conn.execute(
            "SELECT dataset_version_id FROM dataset_version "
            "WHERE dataset_id='dataset:s7-private-cashflow-nav' AND version_label='latest'"
        ).fetchone()[0]
    )
    assert private_call_version != selected_private_version
