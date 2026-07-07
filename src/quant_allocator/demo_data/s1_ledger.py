"""S1 skill-ledger generator: roster -> closed-form shrinkage -> site/data/s1_ledger.json.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
until the numbers are certified. The page (gallery design §5 "S1 · Posterior
strip") reshuffles managers between OLS and posterior rank; that reshuffle is the
visual.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.roster import (
    GROUP_CODES,
    build_skill_ledger_roster,
)
from quant_allocator.flagships.skill_ledger.empirical import advisory_band, shrink_alphas

CREDIBLE_LEVEL = 0.90
# 90% two-sided normal quantile: P(Z <= _Z90) = 0.95. Stdlib, no magic literal.
_Z90 = statistics.NormalDist().inv_cdf(0.95)


def _ranks_descending(values: list[float], codes: list[str]) -> dict[str, int]:
    # Rank 1 = largest alpha; ties broken by code for determinism.
    order = sorted(range(len(values)), key=lambda i: (-values[i], codes[i]))
    return {codes[i]: rank for rank, i in enumerate(order, start=1)}


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    roster = build_skill_ledger_roster()
    codes = [m.code for m in roster]
    groups = np.array([m.group for m in roster])
    ols = np.array([m.ols_alpha_annual for m in roster])
    ses = np.array([m.ols_se_annual for m in roster])

    result = shrink_alphas(ols, ses, groups)

    ols_points = ols.tolist()
    post_points = result.posterior_alpha.tolist()
    ols_ranks = _ranks_descending(ols_points, codes)
    post_ranks = _ranks_descending(post_points, codes)

    managers = []
    for i, m in enumerate(roster):
        managers.append(
            {
                "code": m.code,
                "name": m.name,
                "group": m.group,
                "months": m.months,
                "true_alpha_annual": float(m.true_alpha_annual),
                "ols_alpha": {
                    "point": float(ols[i]),
                    "ci_lo": float(ols[i] - _Z90 * ses[i]),
                    "ci_hi": float(ols[i] + _Z90 * ses[i]),
                },
                "posterior_alpha": {
                    "point": float(result.posterior_alpha[i]),
                    "ci_lo": float(result.posterior_alpha[i] - _Z90 * result.posterior_sd[i]),
                    "ci_hi": float(result.posterior_alpha[i] + _Z90 * result.posterior_sd[i]),
                },
                "prob_positive": float(result.prob_positive[i]),
                "shrinkage_weight": float(result.shrinkage_weight[i]),
                "ols_rank": ols_ranks[m.code],
                "posterior_rank": post_ranks[m.code],
                "advisory_band": advisory_band(float(result.posterior_t_ratio[i])),
            }
        )

    groups_out = []
    for group in GROUP_CODES:
        idx = next(i for i, m in enumerate(roster) if m.group == group)
        groups_out.append(
            {
                "group": group,
                "n": sum(1 for m in roster if m.group == group),
                "mu_hat_annual": float(result.group_mean[idx]),
                "tau_hat_annual": float(np.sqrt(result.group_tau2[idx])),
            }
        )

    payload = {
        "meta": {
            "generator": "s1_ledger",
            "n_managers": len(roster),
            "n_groups": len(GROUP_CODES),
            "credible_level": CREDIBLE_LEVEL,
        },
        "groups": groups_out,
        "managers": managers,
    }
    return write_json(out_dir / "s1_ledger.json", payload)
