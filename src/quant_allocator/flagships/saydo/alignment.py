"""M5 §3.2 deterministic alignment scoring.

The LLM only reads text; the scoring is deterministic code — nothing
probabilistic touches the label (M5 spec §3). This module compares a stated
direction against the realized move of the measured series over the horizon,
using a per-instrument materiality dead-band delta.
"""

from __future__ import annotations

# M5 spec §3.1 stated-view directions.
DIRECTIONS = ("long/constructive", "short/cautious", "neutral-explicit")

# M5 spec §3.2: per-instrument-class materiality thresholds, declared in one
# table so a reviewer sees every rule at once. UNCALIBRATED demo constants
# (see the NUMERICS-GATE note in this task): factor beta in beta units, net in
# net-exposure units.
DELTA_TABLE: dict[str, float] = {
    "beta_market": 0.10,
    "beta_size": 0.10,
    "beta_value": 0.10,
    "beta_momentum": 0.10,
    "net": 0.05,
}

_DIRECTION_SIGN = {"long/constructive": 1.0, "short/cautious": -1.0}


def score_alignment(direction: str, move: float, delta: float) -> str:
    # M5 spec §3.2. neutral-explicit: aligned if the exposure stays within +/-delta
    # of its start; otherwise it moved away from the stated flat stance.
    if direction == "neutral-explicit":
        return "aligned" if abs(move) <= delta else "contradicted"
    if direction not in _DIRECTION_SIGN:
        raise ValueError(
            f"unknown direction {direction!r}; expected one of {DIRECTIONS}"
        )
    # Project the move onto the stated direction: positive = moved as stated.
    projected = _DIRECTION_SIGN[direction] * move
    if projected >= delta:  # aligned: moved in stated direction by >= delta
        return "aligned"
    if projected <= -delta:  # contradicted: moved against stated direction by >= delta
        return "contradicted"
    return "partial"  # |move| < delta: inside the dead-band, no material statement
