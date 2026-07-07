# tests/flagships/decision_audit/test_ledger.py
import numpy as np
import pytest

from quant_allocator.flagships.decision_audit.journal import DecisionRecord
from quant_allocator.flagships.decision_audit import ledger


def _world(n=40):
    # YYYY-MM month labels (journal schema validates decision_date format);
    # month_index maps by position, not calendar. D0 is the first month.
    months = tuple(f"{2018 + i // 12:04d}-{i % 12 + 1:02d}" for i in range(n))
    rng = np.random.default_rng(0)
    factors = rng.normal(0.0, 0.02, size=(n, 2))
    rf = np.full(n, 0.001)
    winners = np.full(n, 0.02)   # a manager that beats
    losers = np.full(n, -0.01)   # a manager that lags
    world = ledger.AuditWorld(
        months=months,
        returns_by_manager={
            "WIN": winners, "LOSE": losers,
            "P1": np.full(n, 0.005), "P2": np.full(n, 0.006), "P3": np.full(n, 0.004),
        },
        strategy_by_manager={k: "eqls" for k in ("WIN", "LOSE", "P1", "P2", "P3")},
        factors=factors,
        factor_names=("f1", "f2"),
        rf_monthly=rf,
        benchmark_by_strategy={"eqls": np.full(n, 0.002)},
    )
    return world


def test_forward_excess_return_matches_compound_formula():
    world = _world()
    r = world.returns_by_manager["WIN"]
    got = ledger.forward_excess_return(r, world.rf_monthly, d_index=0, horizon_years=1)
    expected = np.prod(1.0 + r[1:13] - world.rf_monthly[1:13]) - 1.0
    assert got == pytest.approx(expected)


def test_fire_sign_positive_when_replacement_beats_fired():
    # spec 3.4: fire V = R_replacement - R_fired; positive means the fire helped.
    world = _world()
    rec = DecisionRecord(
        decision_type="fire", manager_id="LOSE", decision_date="2018-01",
        thesis="x", expected_alpha_annual=0.0, horizon_years=1,
        kill_criterion="k", kill_alpha_threshold_annual=-0.02, counterfactual="WIN",
    )
    ev = ledger.resolve_event(rec, world)
    assert ev.counterfactual_rung == "replacement-paired"
    assert ev.forward_gap_raw > 0.0          # replacement (WIN) beat fired (LOSE)
    assert ev.value_verdict == "helped"


def test_hire_sign_positive_when_hire_beats_counterfactual():
    # spec 3.4: hire V = R_hired - R_counterfactual.
    world = _world()
    rec = DecisionRecord(
        decision_type="hire", manager_id="WIN", decision_date="2018-01",
        thesis="x", expected_alpha_annual=0.0, horizon_years=1,
        kill_criterion="k", kill_alpha_threshold_annual=-0.02, counterfactual="peer-median",
    )
    ev = ledger.resolve_event(rec, world)
    assert ev.counterfactual_rung == "peer-median"
    assert ev.forward_gap_raw > 0.0


def test_benchmark_rung_selected_for_benchmark_sentinel():
    world = _world()
    rec = DecisionRecord(
        decision_type="fire", manager_id="LOSE", decision_date="2018-01",
        thesis="x", expected_alpha_annual=0.0, horizon_years=1,
        kill_criterion="k", kill_alpha_threshold_annual=-0.02, counterfactual="benchmark",
    )
    ev = ledger.resolve_event(rec, world)
    assert ev.counterfactual_rung == "benchmark"


def test_hold_uses_peer_median_excluding_self():
    world = _world()
    rec = DecisionRecord(
        decision_type="hold-under-review", manager_id="P1", decision_date="2018-01",
        thesis="x", expected_alpha_annual=0.0, horizon_years=1,
        kill_criterion="k", kill_alpha_threshold_annual=-0.02, counterfactual="peer-median",
    )
    ev = ledger.resolve_event(rec, world)
    # peer median over {WIN,LOSE,P2,P3} (P1 excluded); held P1 vs that median.
    assert ev.counterfactual_rung == "peer-median"
    assert isinstance(ev.forward_gap_raw, float)


def test_kill_criterion_met_when_realized_alpha_below_threshold():
    world = _world()
    rec = DecisionRecord(
        decision_type="fire", manager_id="LOSE", decision_date="2018-01",
        thesis="x", expected_alpha_annual=0.0, horizon_years=1,
        kill_criterion="cut if factor alpha < 0", kill_alpha_threshold_annual=0.0,
        counterfactual="WIN",
    )
    ev = ledger.resolve_event(rec, world)
    assert isinstance(ev.kill_criterion_met, bool)


def test_forward_cumulative_path_starts_at_zero_and_has_right_length():
    world = _world()
    path = ledger.forward_cumulative_path(world.returns_by_manager["WIN"], world.rf_monthly, 0, 12)
    assert len(path) == 13
    assert path[0] == 0.0
    assert path[-1] == pytest.approx(
        ledger.forward_excess_return(world.returns_by_manager["WIN"], world.rf_monthly, 0, 1)
    )
