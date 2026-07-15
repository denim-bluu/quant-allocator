from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".harness" / "current.yaml"
PRODUCT = ROOT / "docs" / "PRODUCT.md"
EDITORIAL_SYSTEM = ROOT / "docs" / "EDITORIAL_SYSTEM.md"
READER_AUDIT = ROOT / "docs" / "audits" / "2026-07-15-reader-journey-audit.md"
READER_PLAN = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-15-reader-first-editorial-restructure.md"
)
ROADMAP = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-10-external-manager-roadmap-implementation.md"
)
P4_CARD = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-external-manager-p4a-fees-terms.md"
)
P4_FIXTURE = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-p4-shared-terms-fixture-seam.md"
)
PUBLICATION_CHECK = ROOT / "tools" / "publication_check.sh"
PUBLICATION_GRANDFATHER = ROOT / "tools" / (
    "publication_history_grandfather.yaml"
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
    assert "COMPLETED HISTORICAL PLAN" not in opening
    assert "HISTORICAL FIRST REDESIGN" not in opening


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
    assert current["editorial_system"] == "docs/EDITORIAL_SYSTEM.md"
    assert current["evidence_record"] == (
        "docs/audits/2026-07-15-reader-journey-audit.md"
    )
    assert set(current["objective"]) >= {"id", "mode", "outcome"}
    assert current["objective"]["id"] == "editorial-site"
    assert current["objective"]["mode"] == "website-first"
    assert current["objective"]["outcome"].strip()
    assert current["scheduler"]["active_plan"] is None
    assert current["scheduler"]["current_task"] == (
        "WEBSITE-EDITORIAL-PUBLISH-R1-COMPLETE"
    )
    assert "repository hygiene are complete" in current["scheduler"][
        "next_action"
    ].lower()
    assert "no outward action is authorized" in current["scheduler"][
        "next_action"
    ].lower()
    _assert_active_plan_is_eligible(current)
    assert set(current["authority"]) == {"merge", "push", "publish"}
    assert all(type(value) is bool for value in current["authority"].values())
    assert current["authority"] == {
        "merge": False,
        "push": False,
        "publish": False,
    }
    assert current["verification"]["current_level"] == (
        "reader-first-site-live-and-main-integrated"
    )
    assert "targeted-site-tests" in current["verification"]["required"]
    assert "output-integrity" in current["verification"]["required"]
    assert "scoped-publication-canary" in current["verification"]["required"]


def test_reader_first_context_links_binding_documents():
    current = _current()
    editorial_path = ROOT / current["editorial_system"]
    audit_path = ROOT / current["evidence_record"]

    assert editorial_path == EDITORIAL_SYSTEM
    assert audit_path == READER_AUDIT
    assert editorial_path.is_file()
    assert audit_path.is_file()
    assert current["scheduler"]["active_plan"] is None
    assert READER_PLAN.is_file()

    plan = READER_PLAN.read_text(encoding="utf-8")
    assert "docs/EDITORIAL_SYSTEM.md" in plan
    assert "docs/audits/2026-07-15-reader-journey-audit.md" in plan


@pytest.mark.parametrize("plan", [ROADMAP, P4_CARD, P4_FIXTURE])
def test_active_plan_guard_rejects_superseded_or_parked_plans(plan: Path):
    current = _current()
    current["scheduler"]["active_plan"] = plan.relative_to(ROOT).as_posix()
    with pytest.raises(AssertionError):
        _assert_active_plan_is_eligible(current)


def test_active_plan_guard_accepts_an_existing_unparked_plan():
    current = _current()
    current["scheduler"]["active_plan"] = READER_PLAN.relative_to(ROOT).as_posix()
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
    assert "reader-facing website task" in text
    assert "editorial_system" in text
    assert "may not broaden" in text
    assert "historical evidence" in text
    assert "A false authority flag is a prohibition" in text
    assert "Merge, push, and publication each require" in text


def test_publication_history_grandfather_is_exact_and_frozen():
    policy = yaml.safe_load(PUBLICATION_GRANDFATHER.read_text(encoding="utf-8"))
    assert policy["version"] == 1
    assert policy["baseline_commit"] == (
        "11d8c7fba0444356d2d1d4575ec74885866baf59"
    )

    pairs: set[tuple[str, str]] = set()
    commits: set[str] = set()
    paths: set[str] = set()
    for group in policy["groups"]:
        for commit in group["commits"]:
            assert len(commit) == 40
            assert set(commit) <= set("0123456789abcdef")
            commits.add(commit)
            for path in group["paths"]:
                assert path.startswith("docs/superpowers/plans/")
                assert not set(path) & set("*?[]")
                assert (commit, path) not in pairs
                pairs.add((commit, path))
                paths.add(path)

    assert len(pairs) == 101
    assert len(commits) == 20
    assert len(paths) == 6

    guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "`tools/publication_history_grandfather.yaml`" in guide
    assert "does not authorize current-tree or new-history matches" in guide


def test_publication_scan_uses_only_reachable_head_history():
    text = PUBLICATION_CHECK.read_text(encoding="utf-8")
    assert "git rev-list HEAD" in text
    assert "git rev-list --all" not in text


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
    assert "editorial_system" in text
    assert "active_plan" in text


def test_public_readme_matches_the_editorial_contract():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "public editorial research publication and project-idea bank" in text
    assert "Every allocator analytic" in text
