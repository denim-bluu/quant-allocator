"""P1 allocation-band generator: certified S1 posteriors -> advisory capital bands -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The demo and any live build share the SAME
allocation pipeline (spec §5); only the inputs are synthetic. The posteriors are read from the
SAME roster build that emits s1_ledger.json (§8.5: build_skill_ledger_roster -> shrink_alphas,
imported verbatim), so the two pages can never disagree. The centerpiece (§5): Cinderbank
Capital (B10) — a lucky 36-month record — gets a naive point-optimizer weight that sits ABOVE its
whole honest band, on the roster's noisiest flattering estimate.

Constant residual vol (P1_SIGMA_DEMO = 0.08) isolates the posterior as the only driver of band
width. The τ-scale skepticism dial re-widens the posteriors at x0.5/x1/x2 (spec §6.7); the demo
proxy scales posterior width and reuses one set of standard-normal draws so the dial isolates the
width effect (NUMERICS-GATE P1_TAU_SCALES; live does a full tau-refit).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.roster import build_skill_ledger_roster
from quant_allocator.flagships.allocation.pipeline import (
    AllocationConfig,
    allocate_one_draw,
    band_action,
    band_from_posterior,
)
from quant_allocator.flagships.skill_ledger.empirical import advisory_band, shrink_alphas

# NUMERICS-GATE P1-DRAWSEED: posterior-draw base seed, decorrelated from the S1 roster seed
# (20260706) so the draw stream is independent of the data-generating stream.
P1_SEED = 20260707
# Named RNG stream tag for the posterior draws (no hash()-derived seeds).
P1_DRAW_STREAM = 17
# NUMERICS-GATE P1_TAU_SCALES: skepticism-dial states — the posterior-width scale (demo proxy for
# the tau-prior scale, §6.7). x1.0 is the canonical band read from the S1 build.
P1_TAU_SCALES = (0.5, 1.0, 2.0)


def _draw_bands(post_mean, post_sd, sigmas, config, scale):
    # Fresh rng per scale with the SAME seed => identical standard normals => the dial isolates the
    # width effect (§6.7). Pre-scale the posterior sd; the anchor mean is held fixed (demo proxy).
    rng = np.random.default_rng([P1_SEED, P1_DRAW_STREAM])
    return band_from_posterior(post_mean, post_sd * scale, sigmas, config, rng=rng)


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    config = AllocationConfig()

    # §8.5: identical roster->shrink call to s1_ledger.build (posteriors, not transcriptions).
    roster = build_skill_ledger_roster()
    groups = np.array([m.group for m in roster])
    ols = np.array([m.ols_alpha_annual for m in roster])
    ses = np.array([m.ols_se_annual for m in roster])
    result = shrink_alphas(ols, ses, groups)
    post_mean = result.posterior_alpha
    post_sd = result.posterior_sd

    sigmas = np.full(len(roster), config.sigma_demo)

    # The naive point-optimizer contrast columns: raw OLS (the exhibit's cautionary marker) and the
    # posterior mean (still a bare point). No draws — one confident weight each.
    naive_ols = allocate_one_draw(ols, sigmas, config.alloc_cap)
    naive_post = allocate_one_draw(post_mean, sigmas, config.alloc_cap)

    # Bands at each τ-scale; the x1.0 state is canonical.
    bands_by_scale = {scale: _draw_bands(post_mean, post_sd, sigmas, config, scale)
                      for scale in P1_TAU_SCALES}
    canonical = bands_by_scale[1.0]

    managers = []
    for i, m in enumerate(roster):
        band = canonical.manager(i)
        action = band_action(float(naive_ols[i]), band, prev_state=None)
        fund_or_not = band.floor == 0.0 and band.anchor > config.funded_eps
        fan = [
            {
                "scale": scale,
                "floor": float(bands_by_scale[scale].floor[i]),
                "anchor": float(bands_by_scale[scale].anchor[i]),
                "ceil": float(bands_by_scale[scale].ceil[i]),
                "prob_zero": float(bands_by_scale[scale].prob_zero[i]),
            }
            for scale in P1_TAU_SCALES
        ]
        managers.append(
            {
                "code": m.code,
                "name": m.name,
                "group": m.group,
                "months": m.months,
                "post_mean": float(post_mean[i]),
                "post_sd": float(post_sd[i]),
                "prob_positive": float(result.prob_positive[i]),
                "advisory_band": advisory_band(float(result.posterior_t_ratio[i])),
                "floor": band.floor,
                "q25": band.q25,
                "anchor": band.anchor,
                "q75": band.q75,
                "ceil": band.ceil,
                "prob_zero": band.prob_zero,
                "naive_ols": float(naive_ols[i]),
                "naive_post": float(naive_post[i]),
                "action": action.state,
                "fund_or_not": bool(fund_or_not),
                "fan": fan,
            }
        )
    managers.sort(key=lambda row: row["anchor"], reverse=True)

    # Precomputed headline + roster metrics (CI never computes — the page reads these).
    by_code = {row["code"]: row for row in managers}
    b10 = by_code["B10"]
    top3_naive = sum(sorted((row["naive_ols"] for row in managers), reverse=True)[:3])
    top3_anchor = sum(sorted((row["anchor"] for row in managers), reverse=True)[:3])
    funded = [row for row in managers if row["anchor"] > config.funded_eps]
    widths = np.array([row["ceil"] - row["floor"] for row in funded])
    sds = np.array([row["post_sd"] for row in funded])
    width_sd_corr = float(np.corrcoef(widths, sds)[0, 1])
    marginal = [row["code"] for row in managers if row["fund_or_not"]]

    payload = {
        "meta": {
            "generator": "p1_allocation",
            "n_managers": len(roster),
            "n_draws": config.n_draws,
            "band_pct": list(config.band_pct),
            "clear_pct": list(config.clear_pct),
            "sigma_demo": config.sigma_demo,
            "alloc_cap": config.alloc_cap,
            "tau_scales": list(P1_TAU_SCALES),
        },
        "headline": {
            "code": b10["code"],
            "name": b10["name"],
            "naive_ols": b10["naive_ols"],
            "floor": b10["floor"],
            "anchor": b10["anchor"],
            "ceil": b10["ceil"],
            "top3_naive": float(top3_naive),
            "top3_anchor": float(top3_anchor),
            "n_funded": len(funded),
            "width_sd_corr": width_sd_corr,
        },
        "matched_pair": {code: by_code[code] for code in ("B09", "B07")},
        "marginal_codes": marginal,
        "managers": managers,
    }
    return write_json(out_dir / "p1_allocation.json", payload)
