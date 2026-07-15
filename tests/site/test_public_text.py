from __future__ import annotations

from pathlib import Path

import yaml

from quant_allocator.site.build import build
from quant_allocator.site.public_text import public_text_violations


CARD_IDS = {"S1", "E3", "X3"}
CLAIM_IDS = {"S1-alpha-posterior", "E3-retrieval-gate"}
ACCESS_SEMANTICS = {"exact-per-dataset", "synthetic-fixture-only"}
REPO_ROOT = Path(__file__).resolve().parents[2]


def _violations(html: str):
    return public_text_violations(
        html,
        card_ids=CARD_IDS,
        claim_ids=CLAIM_IDS,
        access_semantics=ACCESS_SEMANTICS,
    )


def test_public_text_scan_catches_card_ids_and_suffixed_card_ids():
    violations = _violations("<main>S1 compares a result with E3-owned evidence.</main>")

    assert {violation.rule for violation in violations} == {"card-id"}
    assert any("S1" in violation.excerpt for violation in violations)
    assert any("E3-owned" in violation.excerpt for violation in violations)


def test_public_text_scan_catches_workflow_governance_and_raw_identifiers():
    html = """
    <main>
      Current D; Live ceiling B; access semantics; claim ID; state key; reason code.
      The wave-3 PILOT reads repository history, a ship rule, committed JSON, and a fixture.
      E3-retrieval-gate exact-per-dataset receipt:sha256:abcdef0123456789
    </main>
    """

    rules = {violation.rule for violation in _violations(html)}

    assert {
        "readiness-grade",
        "governance-language",
        "workflow-language",
        "claim-id",
        "access-semantics",
        "raw-hash",
    } <= rules


def test_public_text_scan_checks_accessible_hidden_and_collapsed_copy():
    html = """
    <main>
      <img alt="S1 result" title="Current D">
      <input placeholder="claim ID">
      <p hidden>repository history</p>
      <noscript>ship rule</noscript>
      <details><summary>Technical evidence</summary>E3-retrieval-gate</details>
    </main>
    """

    assert len(_violations(html)) >= 6


def test_public_text_scan_ignores_scripts_data_attributes_and_teaching_code():
    html = """
    <main data-card-id="S1" data-state-key="E3-retrieval-gate">
      <script>const internal = 'S1 claim ID';</script>
      <style>.S1 { content: 'Current D'; }</style>
      <template>E3-owned</template>
      <pre>receipt:sha256:abcdef0123456789</pre>
      <a href="/S1/E3-retrieval-gate">Reader-facing link</a>
    </main>
    """

    assert _violations(html) == ()


def test_public_text_scan_reports_short_normalized_excerpts():
    violations = _violations(
        "<p>" + "prefix " * 40 + "Current A" + " suffix" * 40 + "</p>"
    )

    assert len(violations) == 1
    assert len(violations[0].excerpt) <= 160
    assert "Current A" in violations[0].excerpt


def test_all_generated_public_pages_pass_internal_language_lint(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    cards = yaml.safe_load(
        (REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8")
    )
    card_ids = {card["id"].upper() for card in cards}
    access_semantics = {
        claim["access_semantics"] for card in cards for claim in card["claims"]
    }
    claim_ids = set()
    for card in cards:
        reader_fields = " ".join(
            (
                card["title"],
                card["one_liner"],
                card["decision_question"],
                card["minimum_data"],
            )
        ).lower()
        claim_ids.update(
            claim["id"]
            for claim in card["claims"]
            if claim["id"].lower() not in reader_fields
        )

    pages = [out / "index.html", out / "exhibits.html"]
    pages.extend(out / f"{card['id']}.html" for card in cards)
    pages.extend(out / "specs" / f"{card['id']}.html" for card in cards)

    failures = []
    for page in pages:
        violations = public_text_violations(
            page.read_text(encoding="utf-8"),
            card_ids=card_ids,
            claim_ids=claim_ids,
            access_semantics=access_semantics,
        )
        failures.extend(
            f"{page.relative_to(out)} [{violation.rule}] {violation.excerpt}"
            for violation in violations
        )

    assert not failures, "\n" + "\n".join(failures)
