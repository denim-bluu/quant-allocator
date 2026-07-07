"""Pack honesty invariants (spec §3.3, §3.4) as build-failing lint checks.

Placement ruling (spec method review + dispatch): the generic checks INV-1
and INV-2 would ideally extend the shared gallery lint, but that lives in the
prohibited seam build.py:_lint_outputs. So for this plan ALL pack invariants —
INV-1..INV-4, numeric faithfulness, gate-respect — live here in E2's own builder
module. Migration of the generic checks into the shared lint is a docket item.

Numeric faithfulness is the load-bearing check and is zero-tolerance: a single
numeral in narration prose that is not in its section's certified display-number
set fails the pack. This is the RAG-faithfulness posture — the model (or the
hand author, in the demo) is grounded to a retrieved context (the payload) and
scored on not departing from it (spec §4, §8).
"""

from __future__ import annotations

import re

# NUMERICS-GATE E2-01: numeric faithfulness gate. 1.00 = zero tolerance — a single
# invented number fails the pack, because a plausible wrong number in a client
# document is worse than a missing sentence (spec §4.1; ruled 1.0, not 0.95).
PACK_FAITHFULNESS_MIN: float = 1.00
# NUMERICS-GATE E2-02: hallucinated-claim budget, per pack (spec §4.2).
PACK_HALLUCINATION_MAX: int = 0
# NUMERICS-GATE E2-03: gate-respect accuracy — never assert a gated-out claim (spec §4.3).
PACK_GATE_RESPECT_MIN: float = 1.00
# NUMERICS-GATE E2-04: prompt/model iterations before the narration stage is cut
# and the pack ships deterministic captions only (spec §4; mirrors M5's kill).
PACK_EVAL_ITERATIONS: int = 2

# A numeral token: optional sign, digits, optional decimal, optional percent.
_NUMERAL = re.compile(r"[+-]?\d+(?:\.\d+)?%?")

# A refused section's narration must hedge; these markers prove it withholds the
# claim rather than asserting it (spec §3.4 gate-respect check).
_REFUSAL_MARKERS = ("cannot", "not yet", "would need", "gated", "no tenure", "not a number")


class PackLintError(Exception):
    """Raised when a composed pack violates an honesty invariant.

    The message always names the section and the invariant that failed.
    """


def numerals(text: str) -> list[str]:
    return _NUMERAL.findall(text or "")


def _is_interval(stat: dict) -> bool:
    return stat.get("kind") == "interval" and {"point", "ci_lo", "ci_hi"} <= stat.keys()


def _is_verdict(stat: dict) -> bool:
    return stat.get("kind") == "verdict" and {"verdict", "chip"} <= stat.keys()


def _lint_no_bare_point(section: dict) -> None:  # INV-1
    for stat in section.get("stats", []) or []:
        if not (_is_interval(stat) or _is_verdict(stat)):
            raise PackLintError(
                f"{section['section_id']}: INV-1 bare point — every stat must be an "
                f"IntervalStat (point+ci_lo+ci_hi) or a VerdictChip (verdict+chip): {stat!r}"
            )


def _lint_provenance(section: dict) -> None:  # INV-2
    prov = section.get("provenance") or {}
    if not ({"card", "metric", "as_of"} <= prov.keys()):
        raise PackLintError(
            f"{section['section_id']}: INV-2 provenance — a section must trace to "
            f"a payload provenance naming card, metric and as_of: {prov!r}"
        )


def _lint_faithfulness(section: dict) -> None:  # numeric faithfulness (zero-tolerance)
    allowed = set(section.get("display_numbers", []) or [])
    invented = [n for n in numerals(section.get("narration", "")) if n not in allowed]
    if invented:
        raise PackLintError(
            f"{section['section_id']}: faithfulness — narration numerals not in the "
            f"certified display set {sorted(allowed)}: {invented}"
        )


def _lint_gate_respect(section: dict) -> None:  # INV-3 (refused sections)
    if section.get("state") != "refused":
        return
    text = (section.get("narration") or "").lower()
    if not any(marker in text for marker in _REFUSAL_MARKERS):
        raise PackLintError(
            f"{section['section_id']}: INV-3 gate-respect — a refused section's "
            f"narration must withhold the claim (one of {_REFUSAL_MARKERS})"
        )
    # Faithfulness already bounds refused numerals to the gate's display_numbers,
    # so no measured claim can be smuggled in as a number.
    _lint_faithfulness(section)


def _lint_summary(pack: dict) -> None:
    allowed: set[str] = set()
    for section in pack["sections"]:
        allowed.update(section.get("display_numbers", []) or [])
    invented = [n for n in numerals(pack.get("summary", "")) if n not in allowed]
    if invented:
        raise PackLintError(
            f"summary: faithfulness — numerals not certified by any section "
            f"{sorted(allowed)}: {invented}"
        )


def lint_pack(pack: dict) -> None:
    for section in pack["sections"]:
        state = section.get("state")
        _lint_provenance(section)
        if state == "rendered":
            _lint_no_bare_point(section)
            _lint_faithfulness(section)
        elif state == "refused":
            _lint_gate_respect(section)
        elif state == "omitted":
            continue
        else:
            raise PackLintError(f"{section['section_id']}: unknown state {state!r}")
    _lint_summary(pack)
