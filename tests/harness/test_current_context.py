from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".harness" / "current.yaml"
PRODUCT = ROOT / "docs" / "PRODUCT.md"
ROADMAP = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-10-external-manager-roadmap-implementation.md"
)
P4_CARD = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-external-manager-p4a-fees-terms.md"
)
P4_FIXTURE = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-p4-shared-terms-fixture-seam.md"
)
RESET_PLAN = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-15-editorial-site-harness-reset.md"
)


def _current() -> dict:
    return yaml.safe_load(CURRENT.read_text(encoding="utf-8"))


def _assert_active_plan_is_eligible(current: dict) -> None:
    active_plan = current["scheduler"]["active_plan"]
    if active_plan is None:
        return

    assert isinstance(active_plan, str) and active_plan.strip()
    candidate = (ROOT / active_plan).resolve()
    assert candidate.is_relative_to(ROOT.resolve())
    assert candidate.is_file()
    opening = candidate.read_text(encoding="utf-8")[:800]
    assert "SUPERSEDED PRODUCT SCOPE" not in opening
    assert "PARKED OPTIONAL RESEARCH" not in opening


def test_product_charter_is_the_canonical_editorial_objective():
    text = PRODUCT.read_text(encoding="utf-8")
    assert "Canonical product authority" in text
    assert "editorial research publication and project-idea bank" in text
    assert "Deep engineering follows explicit approval" in text
    assert "Aligrithm" in text
    assert "Interval" in text
    assert "not a production allocator platform" in text
    assert "Plans may add articles, exhibits, and supporting code" in text
    assert "A charter amendment is required only when changing" in text


def test_current_context_selects_editorial_website_and_no_platform_plan():
    current = _current()
    assert current["version"] == 1
    assert current["product_charter"] == "docs/PRODUCT.md"
    assert set(current["objective"]) >= {"id", "mode", "outcome"}
    assert current["objective"]["id"] == "editorial-site"
    assert current["objective"]["mode"] == "website-first"
    assert current["objective"]["outcome"].strip()
    assert current["scheduler"]["active_plan"] is None
    assert current["scheduler"]["current_task"].startswith("WEBSITE-")
    assert current["scheduler"]["next_action"].strip()
    _assert_active_plan_is_eligible(current)
    assert set(current["authority"]) == {"merge", "push", "publish"}
    assert all(type(value) is bool for value in current["authority"].values())
    assert "scoped-publication-canary" in current["verification"]["required"]


@pytest.mark.parametrize("plan", [ROADMAP, P4_CARD, P4_FIXTURE])
def test_active_plan_guard_rejects_superseded_or_parked_plans(plan: Path):
    current = _current()
    current["scheduler"]["active_plan"] = plan.relative_to(ROOT).as_posix()
    with pytest.raises(AssertionError):
        _assert_active_plan_is_eligible(current)


def test_active_plan_guard_accepts_an_existing_unparked_plan():
    current = _current()
    current["scheduler"]["active_plan"] = RESET_PLAN.relative_to(ROOT).as_posix()
    _assert_active_plan_is_eligible(current)


def test_p4_is_parked_with_exact_recovery_tips():
    parked = _current()["parked_work"]["p4"]
    assert parked["status"] == "parked"
    assert parked["website_prerequisite"] is False
    assert parked["resume_requires"] == "explicit-user-approval-and-product-fit-review"
    assert parked["fixture_branch"] == "codex/roadmap-p4-terms-fixture-impl"
    assert parked["fixture_tip"] == "b0596db"
    assert parked["card_branch"] == "codex/roadmap-p4-impl"
    assert parked["card_tip"] == "7c2964f"


def test_agent_guide_routes_through_product_and_current_context():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Direct current-task user instruction" in text
    assert "Read `docs/PRODUCT.md` first" in text
    assert "Read `.harness/current.yaml` second" in text
    assert "may not broaden" in text
    assert "historical evidence" in text
    assert "A false authority flag is a prohibition" in text
    assert "Merge, push, and publication each require" in text


def test_platform_roadmap_and_p4_plans_are_not_active_instructions():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    p4_card = P4_CARD.read_text(encoding="utf-8")
    p4_fixture = P4_FIXTURE.read_text(encoding="utf-8")
    assert "SUPERSEDED PRODUCT SCOPE" in roadmap[:800]
    assert "not an active implementation plan" in roadmap[:800]
    assert "PARKED OPTIONAL RESEARCH" in p4_card[:800]
    assert "PARKED OPTIONAL RESEARCH" in p4_fixture[:800]
    assert "not a website prerequisite" in p4_card[:800]
    assert "not a website prerequisite" in p4_fixture[:800]


def test_harness_readme_keeps_history_out_of_normal_initialization():
    text = (ROOT / ".harness" / "README.md").read_text(encoding="utf-8")
    assert "Normal initialization" in text
    assert "Do not initialize from" in text
    assert ".superpowers/sdd/progress.md" in text


def test_public_readme_matches_the_editorial_contract():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "public editorial research publication and project-idea bank" in text
    assert "Every allocator analytic" in text
