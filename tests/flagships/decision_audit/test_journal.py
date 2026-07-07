# tests/flagships/decision_audit/test_journal.py
import math

import pytest

from quant_allocator.flagships.decision_audit.journal import (
    DECISION_TYPES,
    JOURNAL_DEFAULT_HORIZON_YEARS,
    DecisionRecord,
)


def _valid(**overrides):
    base = dict(
        decision_type="fire",
        manager_id="M03",
        decision_date="2021-06",
        thesis="Trailing 3y bottom-decile; kill criterion tripped.",
        expected_alpha_annual=-0.01,
        horizon_years=JOURNAL_DEFAULT_HORIZON_YEARS,
        kill_criterion="Cut if trailing 2y factor-adjusted alpha < -2%/yr.",
        kill_alpha_threshold_annual=-0.02,
        counterfactual="M11",
    )
    base.update(overrides)
    return DecisionRecord(**base)


def test_default_horizon_is_three_years():
    # Goyal-Wahal evaluation window (spec 3.1).
    assert JOURNAL_DEFAULT_HORIZON_YEARS == 3


def test_valid_record_round_trips():
    rec = _valid()
    assert rec.decision_type in DECISION_TYPES
    assert rec.horizon_years == 3


@pytest.mark.parametrize("bad_type", ["hired", "sell", "", "HIRE"])
def test_rejects_unknown_type(bad_type):
    with pytest.raises(ValueError, match="decision_type"):
        _valid(decision_type=bad_type)


@pytest.mark.parametrize("bad_date", ["2021", "2021-6", "21-06", "2021/06", ""])
def test_rejects_malformed_date(bad_date):
    with pytest.raises(ValueError, match="decision_date"):
        _valid(decision_date=bad_date)


def test_rejects_nonpositive_horizon():
    with pytest.raises(ValueError, match="horizon_years"):
        _valid(horizon_years=0)


def test_rejects_nonfinite_expected_alpha():
    with pytest.raises(ValueError, match="expected_alpha_annual"):
        _valid(expected_alpha_annual=math.inf)


def test_rejects_empty_thesis_or_kill_or_counterfactual():
    with pytest.raises(ValueError, match="thesis"):
        _valid(thesis="  ")
    with pytest.raises(ValueError, match="kill_criterion"):
        _valid(kill_criterion="")
    with pytest.raises(ValueError, match="counterfactual"):
        _valid(counterfactual="")
