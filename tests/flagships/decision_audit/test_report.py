# tests/flagships/decision_audit/test_report.py
from quant_allocator.flagships.decision_audit import report
from quant_allocator.flagships.decision_audit.ledger import EventResult
from quant_allocator.flagships.decision_audit.aggregate import PosteriorResult


def _event(**kw):
    base = dict(
        decision_type="fire", manager_id="M03", decision_date="2021-06",
        horizon_years=3, counterfactual_rung="replacement-paired",
        subject_forward=-0.02, counterfactual_forward=0.01,
        forward_gap_raw=0.03, forward_gap_factor_adj=0.01,
        value_verdict="helped", kill_criterion_met=True,
        thesis="t", kill_criterion="k", expected_alpha_annual=-0.01,
    )
    base.update(kw)
    return EventResult(**base)


def _posterior():
    return PosteriorResult(
        n_events=15, n_cohorts=5, events_per_cohort=3.0, intra_cohort_rho=0.4,
        design_effect=1.8, n_effective=8.3, raw_mean=0.004, raw_se=0.03,
        raw_mean_ci=(-0.05, 0.06), raw_mean_gated=True, posterior_mean=0.001,
        posterior_sd=0.015, posterior_ci=(-0.024, 0.026), shrinkage_weight=0.3,
        prob_positive=0.53, verdict="indistinguishable",
    )


def test_pack_report_shapes_all_sections():
    doc = report.pack_report(
        meta={"generator": "p3_hirefire", "n_events": 15, "strategy": "equity_long_short"},
        events=[_event(), _event(decision_type="hire", counterfactual_rung="peer-median")],
        posterior=_posterior(),
        scorecard={"event": _event(decision_type="hire"), "realized_forward": -0.02,
                   "realized_factor_alpha_annual": -0.005},
        cohort_paths={"trailing_window_months": 36, "fired": [0.0, 0.01], "replacement": [0.0, -0.01]},
        detectability={"true_gap": 0.02, "rho": 0.4, "events_per_cohort": 3.0, "n": 240.0},
    )
    assert doc["meta"]["n_events"] == 15
    assert len(doc["events"]) == 2
    assert doc["aggregate"]["raw_mean_gated"] is True
    assert doc["aggregate"]["verdict_chip"] == "indistinguishable from the base rate"
    assert doc["aggregate"]["posterior"]["ci_lo"] == -0.024
    assert doc["scorecard"]["decision_type"] == "hire"
    assert doc["cohort_paths"]["fired"] == [0.0, 0.01]
    assert doc["aggregate"]["events_to_detect"]["n"] == 240.0
    # A refused raw mean carries the no-average banner, not a value.
    assert "not a track record" in doc["aggregate"]["gate_banner"]
