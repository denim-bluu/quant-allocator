"""P3 spec 3.1 — the prospective decision journal.

A DecisionRecord is filled AT THE DECISION MOMENT, before the outcome is known:
the thesis, expected alpha, horizon, and kill criterion are pre-commitments, and
pre-commitment is the only clean defense against outcome bias (spec 8, note 3).
Write-time validation only; no scoring lives here (that is ledger.py).

The repo uses frozen dataclasses for its schemas (roster.py, pipeline.py); this
follows that convention rather than adding a pydantic dependency the codebase
does not otherwise carry.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# spec 3.1: the decision journal records three event kinds. The hold-under-review
# is load-bearing — auditing only hires and fires survivorship-biases the decision
# set; the manager you considered firing and kept is the control arm.
DECISION_TYPES = ("hire", "fire", "hold-under-review")
# spec 3.3: when a decision is unpaired, the counterfactual is one of these rungs.
COUNTERFACTUAL_SENTINELS = ("peer-median", "benchmark")
# spec 3.1: horizon defaults to the Goyal-Wahal 3-year evaluation window.
JOURNAL_DEFAULT_HORIZON_YEARS = 3

_DATE_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class DecisionRecord:
    decision_type: str
    manager_id: str
    decision_date: str  # "YYYY-MM"
    thesis: str
    expected_alpha_annual: float
    horizon_years: int
    kill_criterion: str
    # spec 3.1: the human-readable kill criterion is free text; kill_alpha_threshold_annual
    # is its numeric pre-commitment, the bar the ledger evaluates the forward path against.
    kill_alpha_threshold_annual: float
    # spec 3.3: a manager id (replacement-paired) or a COUNTERFACTUAL_SENTINELS rung.
    counterfactual: str

    def __post_init__(self) -> None:
        if self.decision_type not in DECISION_TYPES:
            raise ValueError(
                f"decision_type must be one of {DECISION_TYPES}, got {self.decision_type!r}"
            )
        if not _DATE_RE.match(self.decision_date):
            raise ValueError(
                f"decision_date must be 'YYYY-MM', got {self.decision_date!r}"
            )
        if self.horizon_years < 1:
            raise ValueError(f"horizon_years must be >= 1, got {self.horizon_years}")
        if not math.isfinite(self.expected_alpha_annual):
            raise ValueError(
                f"expected_alpha_annual must be finite, got {self.expected_alpha_annual}"
            )
        if not math.isfinite(self.kill_alpha_threshold_annual):
            raise ValueError(
                "kill_alpha_threshold_annual must be finite, "
                f"got {self.kill_alpha_threshold_annual}"
            )
        for name in ("manager_id", "thesis", "kill_criterion", "counterfactual"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be a non-empty string")
