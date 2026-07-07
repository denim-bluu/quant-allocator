"""Seeded synthetic roster for the S1 skill ledger.

Two strategy groups of ten managers each. Per manager: a ground-truth
annualized alpha (from the simulator's known idiosyncratic contribution) and an
OLS alpha estimate + standard error from regressing the manager's monthly
returns on the simulator's factor returns. Track lengths vary across managers
so shorter records earn more shrinkage in Task 4.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

MONTHS_PER_YEAR = 12
BASE_SEED = 20260706
GROUP_CODES = ("A", "B")
_N_PER_GROUP = 10
_MARKET_MONTHS = 60
_N_ASSETS = 300
_T_CYCLE = (36, 48, 60)  # track length per manager, cycled within a group
# Per-group max information coefficient sets the true-skill dispersion spread.
_GROUP_IC_MAX = {"A": 0.12, "B": 0.08}


# FICTIONAL fund names for display (repo rule: no real manager names, ever).
# Authored constants, deliberately invented; any resemblance to real firms is
# coincidental and the site banner says so. Keyed by code (code stays the
# stable internal ID).
MANAGER_NAMES: dict[str, str] = {
    "A01": "Alderbrook Partners",
    "A02": "Foxglove Capital",
    "A03": "Stonereach Advisors",
    "A04": "Pellbridge Capital",
    "A05": "Quillhaven Partners",
    "A06": "Marrowgate Capital",
    "A07": "Thistledown Advisors",
    "A08": "Coldbrook Point",
    "A09": "Fernwick Capital",
    "A10": "Osprey Hollow Partners",
    "B01": "Bramblegate Capital",
    "B02": "Saltmere Partners",
    "B03": "Duskfield Advisors",
    "B04": "Harrowdale Capital",
    "B05": "Wrenmoor Partners",
    "B06": "Gullwing Point Capital",
    "B07": "Ashfen Advisors",
    "B08": "Loomridge Capital",
    "B09": "Petrelwood Partners",
    "B10": "Cinderbank Capital",
}


@dataclass(frozen=True)
class RosterManager:
    code: str
    name: str
    group: str
    months: int
    true_alpha_annual: float
    ols_alpha_annual: float
    ols_se_annual: float


def ols_alpha_and_se(returns: np.ndarray, factors: np.ndarray) -> tuple[float, float]:
    # S1 spec §3.1 observation model: y = alpha + beta·f + eps. Intercept is alpha.
    design = np.column_stack([np.ones(len(returns)), factors])
    coef, *_ = np.linalg.lstsq(design, returns, rcond=None)
    residual = returns - design @ coef
    dof = len(returns) - design.shape[1]
    sigma2 = float(residual @ residual) / dof
    cov = sigma2 * np.linalg.inv(design.T @ design)
    alpha = float(coef[0])
    se_alpha = float(np.sqrt(cov[0, 0]))
    return alpha, se_alpha


def build_skill_ledger_roster(base_seed: int = BASE_SEED) -> list[RosterManager]:
    roster: list[RosterManager] = []
    for group_index, group in enumerate(GROUP_CODES):
        market = simulate_market(
            MarketConfig(n_assets=_N_ASSETS, n_months=_MARKET_MONTHS, seed=base_seed + group_index)
        )
        factor_returns = market.factor_returns.to_numpy()
        ic_max = _GROUP_IC_MAX[group]
        for i in range(_N_PER_GROUP):
            ic = ic_max * i / (_N_PER_GROUP - 1)  # spread from 0 (noise) to ic_max (skill)
            months = _T_CYCLE[i % len(_T_CYCLE)]
            manager_seed = base_seed * 10 + group_index * 100 + i
            history = simulate_manager(
                market, ManagerConfig(information_coefficient=ic, seed=manager_seed)
            )
            returns = history.monthly_returns.to_numpy()[:months]
            factors = factor_returns[:months]
            alpha, se = ols_alpha_and_se(returns, factors)
            true_alpha = float(history.true_alpha_returns.to_numpy()[:months].mean())
            code = f"{group}{i + 1:02d}"
            roster.append(
                RosterManager(
                    code=code,
                    name=MANAGER_NAMES[code],
                    group=group,
                    months=months,
                    # S1 spec §3.1: reporting annualizes alpha by ×12 (and its se linearly).
                    true_alpha_annual=true_alpha * MONTHS_PER_YEAR,
                    ols_alpha_annual=alpha * MONTHS_PER_YEAR,
                    ols_se_annual=se * MONTHS_PER_YEAR,
                )
            )
    return roster
