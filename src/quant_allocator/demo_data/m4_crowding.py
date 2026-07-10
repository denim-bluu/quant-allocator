"""Deterministic P-tier crowding radar over one shared synthetic market.

NUMERIC OUTPUT IS HELD FOR THE BATCH NUMERICS GATE.  The generator consumes
final position transparency through ``emit_tiers`` and sends every analytic
quantity through the M4 flagship pipeline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.crowding import pipeline as crowding
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers

# M4 numerics docket D6-D9: deterministic authored demo world.
N_ASSETS_M4 = 240
N_MONTHS_M4 = 96
MARKET_SEED_M4 = 17
MANAGER_SEEDS_M4 = (101, 202, 303, 404, 505, 606)
CROWD_SEED_M4 = 77
CROWD_PARTICIPATION_M4 = 0.60
PAIR_AUM_MILLIONS = 500.0
STRESS_GRID_M4 = (1.00, 0.75, 0.50, 0.35, 0.25)
TRADING_DAYS_PER_MONTH = 21

# All names are fictional. Hollowmere and Brackenford are M4's gate-approved first claims.
MANAGERS = (
    {
        "code": "HM",
        "name": "Hollowmere Capital",
        "strategy": "concentrated long/short",
        "seed": MANAGER_SEEDS_M4[0],
        "n_long": 24,
        "n_short": 12,
        "aum_millions": PAIR_AUM_MILLIONS,
        "crowd_participation": CROWD_PARTICIPATION_M4,
        "crowd_seed": CROWD_SEED_M4,
    },
    {
        "code": "BP",
        "name": "Brackenford Partners",
        "strategy": "event-driven equity",
        "seed": MANAGER_SEEDS_M4[1],
        "n_long": 30,
        "n_short": 10,
        "aum_millions": PAIR_AUM_MILLIONS,
        "crowd_participation": CROWD_PARTICIPATION_M4,
        "crowd_seed": CROWD_SEED_M4,
    },
    {
        "code": "CA",
        "name": "Copperleigh Advisors",
        "strategy": "quality equity",
        "seed": MANAGER_SEEDS_M4[2],
        "n_long": 32,
        "n_short": 8,
        "aum_millions": 350.0,
        "crowd_participation": 0.0,
        "crowd_seed": 0,
    },
    {
        "code": "NP",
        "name": "Northmarsh Point",
        "strategy": "market-neutral equity",
        "seed": MANAGER_SEEDS_M4[3],
        "n_long": 20,
        "n_short": 16,
        "aum_millions": 425.0,
        "crowd_participation": 0.0,
        "crowd_seed": 0,
    },
    {
        "code": "TC",
        "name": "Ternwick Capital",
        "strategy": "systematic equity",
        "seed": MANAGER_SEEDS_M4[4],
        "n_long": 26,
        "n_short": 12,
        "aum_millions": 300.0,
        "crowd_participation": 0.15,
        "crowd_seed": 88,
    },
    {
        "code": "RP",
        "name": "Redwillow Partners",
        "strategy": "fundamental equity",
        "seed": MANAGER_SEEDS_M4[5],
        "n_long": 28,
        "n_short": 10,
        "aum_millions": 375.0,
        "crowd_participation": 0.0,
        "crowd_seed": 0,
    },
)


def _latest_weights(transparency: pd.DataFrame, assets: pd.Index) -> pd.Series:
    """Reconstruct the final signed book from the emitted P-tier long table."""
    final_month = transparency["month"].max()
    latest = transparency.loc[transparency["month"] == final_month, ["asset", "weight"]]
    weights = latest.set_index("asset")["weight"].reindex(assets, fill_value=0.0)
    return pd.Series(crowding.gross_normalize(weights), index=assets, name="weight")


def _manager_books(market) -> tuple[pd.DataFrame, list[dict]]:
    rows: list[pd.Series] = []
    metadata: list[dict] = []
    for spec in MANAGERS:
        history = simulate_manager(
            market,
            ManagerConfig(
                n_long=spec["n_long"],
                n_short=spec["n_short"],
                target_gross=1.0,
                target_net=0.4,
                information_coefficient=0.1,
                seed=spec["seed"],
                crowd_participation=spec["crowd_participation"],
                crowd_seed=spec["crowd_seed"],
            ),
        )
        transparency = emit_tiers(market, history).transparency
        weights = _latest_weights(transparency, market.betas.index)
        dollars = weights * spec["aum_millions"] * 1_000_000.0
        dollars.name = spec["name"]
        rows.append(dollars)
        metadata.append(
            {
                "code": spec["code"],
                "name": spec["name"],
                "strategy": spec["strategy"],
                "aum_millions": spec["aum_millions"],
            }
        )
    return pd.DataFrame(rows), metadata


def _row_payload(row: crowding.UnwindRow) -> dict:
    return {
        "asset": row.asset,
        "direction": row.direction,
        "holder_count": row.holder_count,
        "combined_dollars": row.combined_dollars,
        "days_stressed_volume": row.days_stressed_volume,
        "illustrative": {"impact_rate": row.illustrative_impact_rate},
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS_M4, n_months=N_MONTHS_M4, seed=MARKET_SEED_M4)
    )
    positions, managers = _manager_books(market)
    radar = crowding.roster_overlap_matrix(positions, market.adv_dollar)
    pair_names = (MANAGERS[0]["name"], MANAGERS[1]["name"])
    pair_positions = positions.loc[list(pair_names)]
    pair = crowding.pair_overlap(
        pair_positions.iloc[0], pair_positions.iloc[1], market.adv_dollar
    )
    daily_vol = market.asset_returns.std() / np.sqrt(TRADING_DAYS_PER_MONTH)

    scenarios = []
    for stress_delta in STRESS_GRID_M4:
        report = crowding.unwind_stress(
            pair_positions,
            market.adv_dollar,
            daily_vol=daily_vol,
            stress_delta=stress_delta,
        )
        scenarios.append(
            {
                "stress_delta": stress_delta,
                "rows": [_row_payload(row) for row in report.rows],
                "worst": None if report.worst is None else _row_payload(report.worst),
            }
        )
    headline = next(row for row in scenarios if row["stress_delta"] == 0.50)
    worst = headline["worst"]
    payload = {
        "meta": {
            "generator": "m4_crowding",
            "tier": "P",
            "source": "emit_tiers().transparency",
            "as_of": str(market.factor_returns.index[-1]),
            "n_assets": N_ASSETS_M4,
            "n_months": N_MONTHS_M4,
            "n_managers": len(MANAGERS),
            "market_seed": MARKET_SEED_M4,
            "participation_limit": crowding.PARTICIPATION_LIMIT_M4,
        },
        "managers": managers,
        "pair_centerpiece": {
            "manager_a": pair_names[0],
            "manager_b": pair_names[1],
            "raw": pair.raw,
            "cosine": pair.cosine,
            "liquidity": pair.liquidity,
            "alert_threshold": crowding.OVERLAP_ALERT_THRESHOLD,
            "crowded": pair.liquidity >= crowding.OVERLAP_ALERT_THRESHOLD,
            "worst_asset": worst["asset"],
            "worst_direction": worst["direction"],
            "worst_days_stressed_volume": worst["days_stressed_volume"],
        },
        "heatmap": {
            "managers": list(radar.managers),
            "raw": radar.raw.to_numpy().tolist(),
            "cosine": radar.cosine.to_numpy().tolist(),
            "liquidity": radar.liquidity.to_numpy().tolist(),
            "alert_threshold": crowding.OVERLAP_ALERT_THRESHOLD,
        },
        "stress_scenarios": scenarios,
        "power_gate": {
            "predictive_supported": False,
            "gate_2_status": "missing",
            "public_filings_view": False,
            "gate_3_status": "missing",
        },
    }
    return write_json(out_dir / "m4_crowding.json", payload)
