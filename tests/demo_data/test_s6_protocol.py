import numpy as np

from quant_allocator.demo_data import s6_protocol as p


def test_frozen_constants_and_direction_table_match_the_gate_rulings():
    assert (p.S6_AUC_MIN, p.S6_FAMILYWISE_ALPHA) == (0.65, 0.05)
    assert (p.S6_N_PERM, p.S6_N_PER_CLASS, p.S6_DECISION_T) == (5000, 500, 60)
    # §3.4 direction table, frozen (only the declared cells carry a sign).
    assert p.S6_DIRECTIONS["vol_of_vol"]["h_size"] == "+"
    assert p.S6_DIRECTIONS["kurtosis"]["h_size"] == "+"
    assert p.S6_DIRECTIONS["drawdown_shape"] == {"h_size": "+", "h_decay": "+"}
    assert p.S6_DIRECTIONS["autocorr"]["h_size"] is None
    assert p.S6_DIRECTIONS["autocorr"]["h_decay"] == "-"
    assert p.S6_DIRECTIONS["rolling_ir_slope"]["h_decay"] == "-"
    assert p.S6_DIRECTIONS["skew"] == {"h_size": None, "h_decay": None}


def test_mann_whitney_auc_reproduces_the_section_3_3_toy():
    # §3.3 worked example: 15 of 16 cross-class pairs ordered correctly -> 0.9375.
    pos = np.array([0.9, 1.4, 0.6, 1.1])
    neg = np.array([0.3, 0.8, -0.1, 0.5])
    assert abs(p.mann_whitney_auc(pos, neg) - 0.9375) < 1e-12


def test_mann_whitney_auc_ties_count_half_and_blind_is_half():
    assert p.mann_whitney_auc(np.array([1.0, 2.0]), np.array([1.0, 2.0])) == 0.5
    rng = np.random.default_rng(0)
    x = rng.standard_normal(500)
    y = rng.standard_normal(500)
    assert abs(p.mann_whitney_auc(x, y) - 0.5) < 0.06  # no separation


def test_hanley_mcneil_se_shrinks_with_n_and_is_zero_at_perfect_separation():
    se_small = p.hanley_mcneil_se(0.7, 50, 50)
    se_large = p.hanley_mcneil_se(0.7, 500, 500)
    assert se_large < se_small
    assert p.hanley_mcneil_se(1.0, 200, 200) == 0.0  # Q1=Q2=1, A=1 -> variance 0


def test_familywise_test_is_calibrated_under_the_null():
    # Two classes drawn from IDENTICAL distributions: labels are exchangeable, so no
    # signature should be familywise-significant (adj p small) more than ~alpha of the time.
    rng = np.random.default_rng(7)
    n = 200
    rejects = 0
    trials = 40
    for _ in range(trials):
        sig_pos = {"a": rng.standard_normal(n), "b": rng.standard_normal(n)}
        sig_neg = {"a": rng.standard_normal(n), "b": rng.standard_normal(n)}
        res = p.familywise_maxauc_test(sig_pos, sig_neg, seed=int(rng.integers(1e9)), n_perm=400)
        if min(res.adjusted_p.values()) <= 0.05:
            rejects += 1
    assert rejects <= 6  # ~5% of 40, with generous MC slack


def test_familywise_test_detects_a_strong_planted_separation():
    rng = np.random.default_rng(8)
    n = 300
    sig_pos = {"real": rng.normal(1.0, 1.0, n), "blind": rng.standard_normal(n)}
    sig_neg = {"real": rng.normal(0.0, 1.0, n), "blind": rng.standard_normal(n)}
    res = p.familywise_maxauc_test(sig_pos, sig_neg, seed=11, n_perm=1000)
    assert res.observed["real"] > 0.65
    assert res.adjusted_p["real"] <= 0.05
    assert res.adjusted_p["blind"] > 0.05  # the blind signature is not dragged along
    assert len(res.max_dev_null) == 1000


def test_directional_orientation():
    assert p.directional_auc(0.62, "+") == 0.62
    assert abs(p.directional_auc(0.38, "-") - 0.62) < 1e-12  # negated statistic reads > 0.5
    assert p.directional_auc(0.62, None) is None


def test_classify_verdict_covers_every_taxonomy_branch():
    A, alpha = p.S6_AUC_MIN, p.S6_FAMILYWISE_ALPHA
    # NULL: not significant in some cell.
    assert p.classify_verdict("+", 0.72, 0.20, False, auc_min=A, alpha=alpha) == "null"
    # SHIP: declared, significant everywhere, worst directional AUC clears the bar.
    assert p.classify_verdict("+", 0.70, 0.02, False, auc_min=A, alpha=alpha) == "ship"
    # WEAK TELL: significant but below the usability bar (the pilot's common case).
    assert p.classify_verdict("+", 0.58, 0.01, False, auc_min=A, alpha=alpha) == "weak_tell"
    # WEAK TELL: significant in the direction OPPOSITE to the declaration (the anomaly).
    assert p.classify_verdict("-", 0.40, 0.03, True, auc_min=A, alpha=alpha) == "weak_tell"
    # WEAK TELL: undeclared direction, significant -> anomaly for v2, never a ship.
    assert p.classify_verdict(None, 0.60, 0.01, False, auc_min=A, alpha=alpha) == "weak_tell"
    # NULL: undeclared and not significant.
    assert p.classify_verdict(None, 0.55, 0.30, False, auc_min=A, alpha=alpha) == "null"
