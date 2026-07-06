"""M5 say-do generator: simulator exposure paths + three authored views -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
until certified. The exposure paths are measured from the simulator; the letter
excerpts, directions, themes, convictions and horizons are AUTHORED constants
(gallery design §5; M5 spec §4 "Demo vs. live"). Two views align with the book;
one contradicts it (the visual centerpiece). The page carries the honesty note
that the live build requires the synthetic-letter eval harness to pass.
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.saydo.alignment import DELTA_TABLE, score_alignment
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers

BASE_SEED = 20260706
MANAGER_CODE = "M07"
STRATEGY = "equity_long_short"
N_ASSETS = 300
N_MONTHS = 18
MANAGER_IC = 0.08
MANAGER_SEED = 1
LETTER_MONTH_INDEX = 3
HORIZON_MONTHS = 6
_PATH_INSTRUMENTS = ("beta_market", "beta_value", "beta_momentum", "net")

# Authored letter excerpts. Each view maps to a measurable exposure the simulator
# emits (M5 spec §3.1 instrument mapping). Directions/themes/quotes are fixed
# constants; the label is computed by the deterministic engine from the measured
# move (M5 spec §3.2).
VIEWS = [
    {
        "view_id": 1,
        "direction": "neutral-explicit",
        "theme": "disciplined net exposure",
        "instrument": "net",
        "conviction": 3,
        # gate: quote must be a stance-persistence claim only (that is
        # what the engine measures, M5 spec §3.2) — no level claim like
        # "near-flat", which the plotted net path (0.20) would contradict.
        "quote": (
            "We continue to run the book at our disciplined net exposure "
            "and have not chased the rally."
        ),
    },
    {
        "view_id": 2,
        "direction": "long/constructive",
        "theme": "value factor tilt",
        "instrument": "beta_value",
        "conviction": 2,
        "quote": (
            "We have leaned further into cheaper, higher-quality names, "
            "adding to our value tilt over the coming two quarters."
        ),
    },
    {
        "view_id": 3,
        "direction": "short/cautious",
        "theme": "trimmed momentum risk",
        "instrument": "beta_momentum",
        "conviction": 2,
        "quote": (
            "Given how crowded momentum has become, we have been trimming "
            "our exposure to the factor and expect to stay cautious."
        ),
    },
]


def _exposure_paths():
    market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=N_MONTHS, seed=BASE_SEED))
    history = simulate_manager(
        market, ManagerConfig(information_coefficient=MANAGER_IC, seed=MANAGER_SEED)
    )
    exposures = emit_tiers(market, history).exposures
    exposures.index = exposures.index.astype(str)  # PeriodIndex -> "YYYY-MM"
    return exposures


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    exposures = _exposure_paths()
    months = list(exposures.index)
    start_i = LETTER_MONTH_INDEX
    end_i = LETTER_MONTH_INDEX + HORIZON_MONTHS
    letter_date = months[start_i]

    views_out = []
    for view in VIEWS:
        instrument = view["instrument"]
        delta = DELTA_TABLE[instrument]
        series = exposures[instrument]
        start = float(series.iloc[start_i])
        end = float(series.iloc[end_i])
        move = end - start
        views_out.append(
            {
                "view_id": view["view_id"],
                "letter_date": letter_date,
                "direction": view["direction"],
                "theme": view["theme"],
                "instrument": instrument,
                "horizon_months": HORIZON_MONTHS,
                "conviction": view["conviction"],
                "quote": view["quote"],
                "measured": {"start": start, "end": end, "move": move, "delta": delta},
                "label": score_alignment(view["direction"], move, delta),
            }
        )

    exposure_paths = {
        instrument: [
            {"month": month, "value": float(exposures[instrument].iloc[i])}
            for i, month in enumerate(months)
        ]
        for instrument in _PATH_INSTRUMENTS
    }

    payload = {
        "meta": {
            "generator": "m5_saydo",
            "manager_code": MANAGER_CODE,
            "strategy": STRATEGY,
            "horizon_months": HORIZON_MONTHS,
        },
        "delta_table": {k: DELTA_TABLE[k] for k in _PATH_INSTRUMENTS},
        "views": views_out,
        "exposure_paths": exposure_paths,
    }
    return write_json(out_dir / "m5_saydo.json", payload)


def _scan_seeds(seeds=range(0, 100)) -> None:
    # Recovery helper (see the NUMERICS-GATE note): print seeds whose three authored
    # views yield exactly {aligned, aligned, contradicted}. Not part of the build.
    from collections import Counter

    for seed in seeds:
        market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=N_MONTHS, seed=seed))
        history = simulate_manager(
            market, ManagerConfig(information_coefficient=MANAGER_IC, seed=MANAGER_SEED)
        )
        exposures = emit_tiers(market, history).exposures
        labels = Counter()
        for view in VIEWS:
            series = exposures[view["instrument"]]
            move = float(series.iloc[LETTER_MONTH_INDEX + HORIZON_MONTHS]) - float(
                series.iloc[LETTER_MONTH_INDEX]
            )
            labels[score_alignment(view["direction"], move, DELTA_TABLE[view["instrument"]])] += 1
        if labels["aligned"] == 2 and labels["contradicted"] == 1:
            print(f"seed {seed}: {dict(labels)}")
