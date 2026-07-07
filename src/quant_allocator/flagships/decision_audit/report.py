"""P3 spec 5 — pack the ledger + posterior into the demo JSON schema.

Rendering only; no math. Every displayed statistic is shaped for an IntervalStat
(the posterior), a VerdictChip (the per-event value verdict and the aggregate
verdict), or a PowerGate (the refused raw mean). The per-event forward gaps are
deterministic accounting receipts, passed through as facts.
"""

from __future__ import annotations

# spec 3.5 gate ruling: the aggregate panel refuses a raw average below the
# effective-events gate and shows the individual decisions instead.
GATE_BANNER = (
    "N too small for an average — these are individual decisions, not a track record."
)
# spec 3.5: the VerdictChip that IS the product when the posterior straddles zero.
_VERDICT_CHIP = {
    "indistinguishable": "indistinguishable from the base rate",
    "distinguishable": "distinguishable from the base rate",
}


def _event_row(ev) -> dict:
    return {
        "decision_type": ev.decision_type,
        "manager_id": ev.manager_id,
        "decision_date": ev.decision_date,
        "horizon_years": ev.horizon_years,
        "counterfactual_rung": ev.counterfactual_rung,
        "subject_forward": ev.subject_forward,
        "counterfactual_forward": ev.counterfactual_forward,
        "forward_gap_raw": ev.forward_gap_raw,
        "forward_gap_factor_adj": ev.forward_gap_factor_adj,
        "value_verdict": ev.value_verdict,
        "kill_criterion_met": ev.kill_criterion_met,
        "thesis": ev.thesis,
        "kill_criterion": ev.kill_criterion,
        "expected_alpha_annual": ev.expected_alpha_annual,
    }


def pack_report(*, meta, events, posterior, scorecard, cohort_paths, detectability) -> dict:
    p = posterior
    sc = scorecard["event"]
    return {
        "meta": meta,
        "aggregate": {
            "n_events": p.n_events,
            "n_cohorts": p.n_cohorts,
            "events_per_cohort": p.events_per_cohort,
            "intra_cohort_rho": p.intra_cohort_rho,
            "design_effect": p.design_effect,
            "n_effective": p.n_effective,
            "raw_mean": p.raw_mean,
            "raw_mean_ci": {"lo": p.raw_mean_ci[0], "hi": p.raw_mean_ci[1]},
            "raw_mean_gated": p.raw_mean_gated,
            "gate_banner": GATE_BANNER,
            "posterior": {
                "point": p.posterior_mean,
                "ci_lo": p.posterior_ci[0],
                "ci_hi": p.posterior_ci[1],
            },
            "shrinkage_weight": p.shrinkage_weight,
            "prob_positive": p.prob_positive,
            "verdict": p.verdict,
            "verdict_chip": _VERDICT_CHIP[p.verdict],
            "events_to_detect": detectability,
        },
        "events": [_event_row(ev) for ev in events],
        "scorecard": {
            "decision_type": sc.decision_type,
            "manager_id": sc.manager_id,
            "decision_date": sc.decision_date,
            "horizon_years": sc.horizon_years,
            "thesis": sc.thesis,
            "kill_criterion": sc.kill_criterion,
            "kill_criterion_met": sc.kill_criterion_met,
            "expected_alpha_annual": sc.expected_alpha_annual,
            "counterfactual_rung": sc.counterfactual_rung,
            "counterfactual_forward": sc.counterfactual_forward,
            "realized_forward": scorecard["realized_forward"],
            "realized_factor_alpha_annual": scorecard["realized_factor_alpha_annual"],
            "value_verdict": sc.value_verdict,
            "forward_gap_raw": sc.forward_gap_raw,
        },
        "cohort_paths": cohort_paths,
    }
