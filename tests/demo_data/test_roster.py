import numpy as np

from quant_allocator.demo_data.roster import (
    RosterManager,
    build_skill_ledger_roster,
    ols_alpha_and_se,
)


def test_ols_recovers_planted_intercept_and_positive_se():
    rng = np.random.default_rng(0)
    T = 60
    factors = rng.normal(0.0, 0.04, size=(T, 3))
    true_betas = np.array([0.8, -0.3, 0.5])
    y = 0.01 + factors @ true_betas + rng.normal(0.0, 0.02, size=T)
    alpha, se = ols_alpha_and_se(y, factors)
    assert abs(alpha - 0.01) < 0.01
    assert se > 0.0


def test_roster_has_twenty_managers_in_two_groups_of_ten():
    roster = build_skill_ledger_roster()
    assert len(roster) == 20
    assert all(isinstance(m, RosterManager) for m in roster)
    groups = [m.group for m in roster]
    assert groups.count("A") == 10 and groups.count("B") == 10
    codes = [m.code for m in roster]
    assert codes == sorted(set(codes))  # unique, sorted
    assert all(m.months in (36, 48, 60) for m in roster)
    assert all(np.isfinite(m.ols_alpha_annual) and m.ols_se_annual > 0 for m in roster)


def test_roster_is_deterministic():
    a = build_skill_ledger_roster()
    b = build_skill_ledger_roster()
    assert [m.code for m in a] == [m.code for m in b]
    assert [m.ols_alpha_annual for m in a] == [m.ols_alpha_annual for m in b]
    assert [m.true_alpha_annual for m in a] == [m.true_alpha_annual for m in b]
