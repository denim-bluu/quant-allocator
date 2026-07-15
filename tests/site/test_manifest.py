from pathlib import Path

import yaml

import pytest

from quant_allocator.site.build import BuildError, load_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
ACCESS_SEMANTICS = {
    "exact-per-dataset",
    "exact-per-selected-dataset",
    "all-required-per-selected-dataset",
    "all-required-per-dataset",
    "synthetic-fixture-only",
    "refusal-in-every-context",
    "refusal-per-inadmissible-input",
}


def _write_manifest(tmp_path, entries):
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    manifest = site_dir / "cards.yaml"
    manifest.write_text(yaml.safe_dump(entries), encoding="utf-8")
    return manifest


def _make_live_files(tmp_path):
    site_dir = tmp_path / "site"
    (site_dir / "templates" / "pages").mkdir(parents=True, exist_ok=True)
    (site_dir / "templates" / "pages" / "t1.html.j2").write_text("x", encoding="utf-8")
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "t1.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "t1.md").write_text("# t1", encoding="utf-8")


def _planned_entry():
    return {
        "id": "s1",
        "title": "Skill ledger",
        "lane": "S",
        "one_liner": "Posterior alpha across the roster.",
        "decisions": ["select", "size"],
        "tiers": ["R", "E", "P"],
        "status": "planned",
        **_phase1_metadata(),
    }


def _live_entry():
    return {
        "id": "t1",
        "title": "Test card",
        "lane": "S",
        "one_liner": "A live card.",
        "decisions": ["select"],
        "tiers": ["R"],
        "status": "live",
        "demo": "pages/t1.html.j2",
        "data": "t1.json",
        "spec": "t1.md",
        "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
        **_phase1_metadata(),
    }


def _phase1_metadata():
    return {
        "decision_question": "Is the reported edge robust enough to underwrite?",
        "primary_stage": "underwrite",
        "stages": ["underwrite", "construct"],
        "asset_classes": ["cross-asset"],
        "vehicle_types": ["pooled-fund"],
        "access_contexts": ["shortlisted-nda", "funded-commingled"],
        "supported_data_modalities": ["returns", "documents"],
        "minimum_data_modalities": ["returns"],
        "decision_readiness": "data-conditional",
        "evidence_roles": ["operational-analysis"],
        "minimum_data": "Monthly net returns with historical vintages.",
        "validation_status": "live-calibration-required",
        "claims": [
            {
                "id": "posterior_interval",
                "output_type": "interval",
                "access_contexts": ["shortlisted-nda", "funded-commingled"],
                "access_semantics": "synthetic-fixture-only",
                "current_attestation": "D",
                "live_attestation_ceiling": "B",
                "validation_status": "live-calibration-required",
                "receipt_required": True,
                "refusal": "Historical vintages or comparable peers are missing.",
            }
        ],
    }


def test_phase1_decision_and_evidence_metadata_loads(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    entry.update(_phase1_metadata())
    manifest = _write_manifest(tmp_path, [entry])

    cards = load_manifest(manifest)

    assert cards[0]["primary_stage"] == "underwrite"
    assert cards[0]["claims"][0]["current_attestation"] == "D"


def test_decision_metadata_is_required_independently_of_publication_status(tmp_path):
    entry = _planned_entry()
    del entry["decision_question"]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="missing required keys.*decision_question"):
        load_manifest(manifest)


def test_primary_stage_must_be_controlled_and_present_in_stages(tmp_path):
    entry = _planned_entry()
    entry["primary_stage"] = "select"
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="invalid primary_stage"):
        load_manifest(manifest)


def test_minimum_modalities_must_be_supported(tmp_path):
    entry = _planned_entry()
    entry["minimum_data_modalities"] = ["holdings"]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="must be a subset"):
        load_manifest(manifest)


def test_controlled_token_lists_reject_duplicates(tmp_path):
    entry = _planned_entry()
    entry["stages"] = ["underwrite", "underwrite"]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="stages contains duplicate values"):
        load_manifest(manifest)


def test_claim_ids_are_unique(tmp_path):
    entry = _planned_entry()
    entry["claims"] = [entry["claims"][0], dict(entry["claims"][0])]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="empty or duplicate claim id"):
        load_manifest(manifest)


def test_a_or_b_attestation_ceiling_requires_reconstruction_receipt(tmp_path):
    entry = _planned_entry()
    entry["claims"][0]["receipt_required"] = False
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="A/B ceiling requires a receipt"):
        load_manifest(manifest)


def test_claim_access_semantics_is_required(tmp_path):
    entry = _planned_entry()
    del entry["claims"][0]["access_semantics"]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="access_semantics"):
        load_manifest(manifest)


@pytest.mark.parametrize("value", ["unknown-semantics", 7])
def test_claim_access_semantics_rejects_unknown_or_non_string_values(tmp_path, value):
    entry = _planned_entry()
    entry["claims"][0]["access_semantics"] = value
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="invalid access_semantics"):
        load_manifest(manifest)


def test_all_controlled_claim_access_semantics_load(tmp_path):
    for semantic in ACCESS_SEMANTICS:
        entry = _planned_entry()
        entry["claims"][0]["access_semantics"] = semantic
        manifest = _write_manifest(tmp_path / semantic, [entry])

        assert load_manifest(manifest)[0]["claims"][0]["access_semantics"] == semantic


def test_wave_a_manifest_rows_preserve_reviewed_claim_contracts():
    cards = {
        card["id"]: card
        for card in yaml.safe_load(
            (REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8")
        )
    }
    expected = {
        "x3": {
            "title": "Manager-universe & sourcing-funnel coverage map",
            "primary_stage": "discover",
            "tiers": ["P", "E", "R"],
            "stages": ["discover", "underwrite", "govern"],
            "asset_classes": ["cross-asset"],
            "vehicle_types": [
                "pooled-fund",
                "fund-of-funds",
                "segregated-mandate",
                "drawdown-fund",
            ],
            "supported_data_modalities": ["documents", "filings", "operating-data"],
            "minimum_data_modalities": ["filings"],
            "claim_ids": [
                "public_source_membership",
                "prehire_source_membership",
                "entity_resolution_state",
                "target_cell_observation",
                "source_union_novelty",
                "funnel_stage_counts",
                "funnel_conversion",
                "research_cell_queue",
                "synthetic_entity_recall",
                "synthetic_discovery_recall",
                "global_universe_coverage",
                "manager_quality_ranking",
            ],
            "output_types": [
                "exact-measurement",
                "exact-measurement",
                "exact-measurement",
                "exact-measurement",
                "exact-measurement",
                "exact-measurement",
                "interval",
                "verdict",
                "interval",
                "exact-measurement",
                "refusal",
                "refusal",
            ],
            "semantics": [
                "exact-per-dataset",
                "exact-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-dataset",
                "all-required-per-dataset",
                "all-required-per-dataset",
                "all-required-per-dataset",
                "all-required-per-dataset",
                "synthetic-fixture-only",
                "synthetic-fixture-only",
                "refusal-in-every-context",
                "refusal-in-every-context",
            ],
            "ceilings": ["A", "B", "B", "B", "B", "B", "B", "C", "D", "D", "D", "D"],
        },
        "e4": {
            "title": "Operational evidence & change graph",
            "primary_stage": "underwrite",
            "tiers": ["R", "E", "P"],
            "stages": ["underwrite", "monitor", "govern"],
            "asset_classes": ["cross-asset"],
            "vehicle_types": ["pooled-fund", "segregated-mandate", "drawdown-fund"],
            "supported_data_modalities": ["documents", "filings", "holdings", "mandate-terms"],
            "minimum_data_modalities": ["documents"],
            "claim_ids": [
                "public_operational_facts",
                "operational_change_graph",
                "operational_evidence_state",
                "reunderwriting_queue",
                "operational_data_boundary_refusals",
                "operational_method_boundary_refusal",
                "synthetic_state_validation",
            ],
            "output_types": [
                "evidence-graph",
                "evidence-graph",
                "verdict",
                "exact-measurement",
                "refusal",
                "refusal",
                "exact-measurement",
            ],
            "semantics": [
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "refusal-per-inadmissible-input",
                "refusal-in-every-context",
                "synthetic-fixture-only",
            ],
            "ceilings": ["C", "B", "B", "B", "D", "D", "D"],
        },
        "s7": {
            "title": "Track-record provenance inspector",
            "primary_stage": "underwrite",
            "tiers": ["R", "E", "P"],
            "stages": ["discover", "underwrite", "monitor", "govern"],
            "asset_classes": [
                "public-equity",
                "hedge-funds",
                "fixed-income-credit",
                "private-credit",
                "private-equity",
            ],
            "vehicle_types": ["pooled-fund", "segregated-mandate", "drawdown-fund"],
            "supported_data_modalities": [
                "returns",
                "cashflows-nav",
                "documents",
                "filings",
                "mandate-terms",
            ],
            "minimum_data_modalities": ["returns"],
            "claim_ids": [
                "track_lineage",
                "point_in_time_vintage_audit",
                "basis_breaks",
                "comparable_native_panel",
                "predecessor_portability_evidence",
                "historical_selection_refusal",
                "performance_estimator_refusal",
            ],
            "output_types": [
                "exact-measurement",
                "exact-measurement",
                "verdict",
                "exact-measurement",
                "verdict",
                "refusal",
                "refusal",
            ],
            "semantics": [
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "all-required-per-selected-dataset",
                "refusal-in-every-context",
            ],
            "ceilings": ["B", "B", "B", "B", "C", "B", "D"],
        },
    }
    for card_id, contract in expected.items():
        card = cards[card_id]
        for field in (
            "title",
            "primary_stage",
            "tiers",
            "stages",
            "asset_classes",
            "vehicle_types",
            "supported_data_modalities",
            "minimum_data_modalities",
        ):
            assert card[field] == contract[field]
        claims = card["claims"]
        assert [claim["id"] for claim in claims] == contract["claim_ids"]
        assert [claim["output_type"] for claim in claims] == contract["output_types"]
        assert [claim["access_semantics"] for claim in claims] == contract["semantics"]
        assert [claim["current_attestation"] for claim in claims] == ["D"] * len(claims)
        assert [claim["live_attestation_ceiling"] for claim in claims] == contract["ceilings"]
        assert card["access_contexts"] == list(
            dict.fromkeys(
                context
                for claim in claims
                for context in claim["access_contexts"]
            )
        )


def test_legacy_fixture_entry_is_upgraded_for_compatibility(tmp_path):
    legacy = {
        "id": "s1",
        "title": "Legacy card",
        "lane": "S",
        "one_liner": "A pre-migration fixture.",
        "decisions": ["select"],
        "tiers": ["R"],
        "status": "planned",
    }
    manifest = _write_manifest(tmp_path, [legacy])

    card = load_manifest(manifest, allow_legacy=True)[0]

    assert card["primary_stage"] == "underwrite"
    assert card["decision_readiness"] == "prototype"
    assert card["claims"][0]["current_attestation"] == "D"
    assert card["claims"][0]["access_semantics"] == "all-required-per-selected-dataset"


def test_legacy_fixture_is_rejected_without_explicit_opt_in(tmp_path):
    entry = _planned_entry()
    for key in _phase1_metadata():
        del entry[key]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="missing required keys.*access_contexts"):
        load_manifest(manifest)


def test_production_row_with_phase1_fields_deleted_is_rejected(tmp_path):
    entry = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))[0]
    for key in _phase1_metadata():
        del entry[key]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="missing required keys.*access_contexts"):
        load_manifest(manifest)


def test_production_claim_with_access_semantics_deleted_is_rejected(tmp_path):
    entry = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))[0]
    del entry["claims"][0]["access_semantics"]
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="access_semantics"):
        load_manifest(manifest)


def test_card_access_contexts_must_equal_claim_access_union(tmp_path):
    entry = _planned_entry()
    entry["access_contexts"].append("segregated-mandate")
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="must exactly equal claim access_contexts union"):
        load_manifest(manifest)


def test_valid_planned_entry_loads(tmp_path):
    manifest = _write_manifest(tmp_path, [_planned_entry()])
    cards = load_manifest(manifest)
    assert cards[0]["id"] == "s1"


def test_valid_live_entry_loads(tmp_path):
    _make_live_files(tmp_path)
    manifest = _write_manifest(tmp_path, [_live_entry()])
    cards = load_manifest(manifest)
    assert cards[0]["status"] == "live"


def test_valid_optional_public_article_source_loads(tmp_path):
    _make_live_files(tmp_path)
    articles = tmp_path / "docs" / "ideas" / "articles"
    articles.mkdir(parents=True, exist_ok=True)
    (articles / "t1-public.md").write_text("## The decision", encoding="utf-8")
    entry = _live_entry()
    entry["article"] = "t1-public.md"
    manifest = _write_manifest(tmp_path, [entry])

    cards = load_manifest(manifest)

    assert cards[0]["article"] == "t1-public.md"


def test_live_public_article_source_must_exist(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    entry["article"] = "missing-public.md"
    manifest = _write_manifest(tmp_path, [entry])

    with pytest.raises(BuildError, match="missing article file"):
        load_manifest(manifest)


def test_missing_required_key_raises(tmp_path):
    entry = _planned_entry()
    del entry["one_liner"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_invalid_lane_raises(tmp_path):
    entry = _planned_entry()
    entry["lane"] = "Z"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid lane"):
        load_manifest(manifest)


def test_invalid_status_raises(tmp_path):
    entry = _planned_entry()
    entry["status"] = "shipped"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid status"):
        load_manifest(manifest)


def test_unknown_key_raises(tmp_path):
    entry = _planned_entry()
    entry["surprise"] = True
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="unknown keys"):
        load_manifest(manifest)


def test_live_missing_required_key_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["spec"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_live_missing_data_file_raises(tmp_path):
    _make_live_files(tmp_path)
    (tmp_path / "site" / "data" / "t1.json").unlink()
    manifest = _write_manifest(tmp_path, [_live_entry()])
    with pytest.raises(BuildError, match="missing data file"):
        load_manifest(manifest)


def test_live_dangling_spec_raises(tmp_path):
    _make_live_files(tmp_path)
    (tmp_path / "docs" / "ideas" / "specs" / "t1.md").unlink()
    manifest = _write_manifest(tmp_path, [_live_entry()])
    with pytest.raises(BuildError, match="missing spec file"):
        load_manifest(manifest)


def test_live_standing_note_satisfies_golive(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    entry["standing_note"] = "this page never goes live"
    manifest = _write_manifest(tmp_path, [entry])
    cards = load_manifest(manifest)
    assert cards[0]["standing_note"] == "this page never goes live"


def test_live_missing_golive_and_standing_note_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_invalid_theme_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    entry["theme"] = "sepia"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid theme"):
        load_manifest(manifest)


def test_duplicate_id_raises(tmp_path):
    entry = _planned_entry()
    manifest = _write_manifest(tmp_path, [entry, dict(entry)])
    with pytest.raises(BuildError, match="duplicate card id 's1'"):
        load_manifest(manifest)
