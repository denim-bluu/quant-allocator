"""Deterministic six-filer M6 13F long-book exhibit generator.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. All filers are synthetic managers on one
shared market. The generator consumes the simulator's authored eligibility mask, its
slot-based noneligible-long dial, and the pure quarter-end emitter. Coverage is measured
from gross positive weights after simulation; it is never inferred from the slot dial.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.holdings13f import pipeline as hp
from quant_allocator.simulator.manager import ManagerConfig, ManagerHistory, simulate_manager
from quant_allocator.simulator.market import FactorMarket, MarketConfig, simulate_market

N_ASSETS_M6 = 80
N_MONTHS_M6 = 18
INELIGIBLE_ASSET_FRACTION = 0.30
N_LONG_M6 = 10
N_SHORT_M6 = 2
REBALANCE_FRACTION_M6 = 0.01
MARKET_SEED_M6 = 20260708

# NUMERICS-GATE M6-D11: fixed seeds recovered with _scan_vesper_seed / bounded peer review.
# build() never scans, and no hash-derived seed is used.
VESPER_SEED = 68
PEER_SEEDS = (39, 123, 135, 158)
HENSLEY_SEED = 900

VESPER_NAME = "Vesper Lane Capital"
PEER_NAMES = (
    "Corbin Vale Capital",
    "Bexley Court Capital",
    "Tanager Hill Capital",
    "Kettering Partners",
)
HENSLEY_NAME = "Hensley Park Advisors"
APPROVED_NAMES = (VESPER_NAME, *PEER_NAMES, HENSLEY_NAME)


def _market() -> FactorMarket:
    return simulate_market(
        MarketConfig(
            n_assets=N_ASSETS_M6,
            n_months=N_MONTHS_M6,
            start_month="2023-01",
            seed=MARKET_SEED_M6,
            ineligible_asset_fraction=INELIGIBLE_ASSET_FRACTION,
        )
    )


def _manager(
    market: FactorMarket, seed: int, *, noneligible_share: float, sizing_discipline: float
) -> ManagerHistory:
    return simulate_manager(
        market,
        ManagerConfig(
            n_long=N_LONG_M6,
            n_short=N_SHORT_M6,
            target_gross=1.0,
            target_net=0.8,
            information_coefficient=0.25,
            alpha_half_life_months=100.0,
            sizing_discipline=sizing_discipline,
            rebalance_fraction=REBALANCE_FRACTION_M6,
            seed=seed,
            noneligible_long_share=noneligible_share,
        ),
    )


def _quarter_ends(market: FactorMarket) -> pd.PeriodIndex:
    return market.idio_returns.index[2::3]


def _option_mask(market: FactorMarket) -> pd.Series:
    # The synthetic simulator has no option security type. The all-false authored mask keeps
    # the demo on equities; the pipeline's binding exclusion and >10% flag are unit-tested.
    return pd.Series(False, index=market.betas.index, name="option")


def _reported(
    history: ManagerHistory,
    market: FactorMarket,
    quarter_ends: pd.PeriodIndex,
    option_mask: pd.Series,
) -> pd.DataFrame:
    return hp.emit_13f_long_book(
        history.weights, quarter_ends, market.eligible, option_mask=option_mask
    )


def _date_receipt(period: pd.Period) -> tuple[str, str]:
    as_of = period.to_timestamp(how="end").normalize()
    known_at = as_of + pd.Timedelta(days=hp.M6_FILING_LAG_DAYS)
    return as_of.date().isoformat(), known_at.date().isoformat()


def _concentration_dict(value: hp.Concentration | None) -> dict | None:
    if value is None:
        return None
    return {
        "top5_weight": value.top_n_weight,
        "hhi": value.hhi,
        "effective_names": value.effective_names,
    }


def _timeline(panel: pd.DataFrame) -> dict:
    latest = panel.iloc[-1]
    persistence = hp.conviction_persistence(panel)
    names = list(latest[latest > 0.0].sort_values(ascending=False, kind="stable").index)
    leader = names[0]
    quarters = []
    first_crossing = None
    for i, (period, row) in enumerate(panel.iterrows(), 1):
        descriptor = hp.concentration(row)
        as_of, known_at = _date_receipt(period)
        leader_share = float(row[leader])
        quarter = {
            "label": f"Q{i}",
            "period": str(period),
            "as_of": as_of,
            "known_at": known_at,
            "lag_days": hp.M6_FILING_LAG_DAYS,
            "top5_weight": descriptor.top_n_weight,
            "hhi": descriptor.hhi,
            "effective_names": descriptor.effective_names,
            "leader_share": leader_share,
        }
        quarters.append(quarter)
        if first_crossing is None and leader_share > 0.50:
            first_crossing = {
                "label": quarter["label"],
                "share": leader_share,
                "name": leader,
                "as_of": as_of,
                "known_at": known_at,
                "lag_days": hp.M6_FILING_LAG_DAYS,
            }
    positions = [
        {
            "name": str(name),
            "shares": [float(value) for value in panel[name]],
            "quarters_held": persistence[str(name)],
        }
        for name in names
    ]
    return {
        "leader": str(leader),
        "quarters": quarters,
        "positions": positions,
        "first_majority_crossing": first_crossing,
    }


def _audit(true_weights: pd.Series, reported_book: pd.Series, eligible: pd.Series) -> dict:
    true_longs = true_weights.clip(lower=0.0)
    true_book = true_longs / true_longs.sum()
    true_c = hp.concentration(true_book)
    crop_c = hp.concentration(reported_book)
    return {
        "coverage": hp.coverage_ratio(true_weights, eligible),
        "true_hhi": true_c.hhi,
        "crop_hhi": crop_c.hhi,
        "hhi_distortion": crop_c.hhi - true_c.hhi,
        "true_effective_names": true_c.effective_names,
        "crop_effective_names": crop_c.effective_names,
        "exact_45_day_staleness_audit": False,
    }


def _filer_payload(
    name: str,
    history: ManagerHistory,
    panel: pd.DataFrame,
    market: FactorMarket,
    option_mask: pd.Series,
    *,
    peer_book: pd.Series | None,
) -> dict:
    latest_period = panel.index[-1]
    as_of, known_at = _date_receipt(latest_period)
    true_weights = history.weights.loc[latest_period]
    verdict = hp.holdings_view(
        panel,
        true_weights,
        market.eligible,
        peer_book=peer_book,
        option_mask=option_mask,
        as_of=pd.Timestamp(as_of),
        known_at=pd.Timestamp(known_at),
    )
    return {
        "name": name,
        "coverage": verdict.coverage,
        "gate": {"pass": verdict.coverage_pass, "threshold": hp.M6_COVERAGE_MIN},
        "concentration": _concentration_dict(verdict.concentration),
        "overlap": verdict.overlap,
        "persistence": verdict.persistence,
        "option_share": verdict.option_share,
        "option_heavy": verdict.option_heavy,
        "as_of": as_of,
        "known_at": known_at,
        "timeline": _timeline(panel),
        "audit": _audit(true_weights, panel.iloc[-1], market.eligible),
    }


def _payload() -> dict:
    market = _market()
    quarter_ends = _quarter_ends(market)
    option_mask = _option_mask(market)
    vesper_history = _manager(
        market, VESPER_SEED, noneligible_share=0.10, sizing_discipline=1.0
    )
    peer_histories = [
        _manager(market, seed, noneligible_share=0.10, sizing_discipline=1.0)
        for seed in PEER_SEEDS
    ]
    hensley_history = _manager(
        market, HENSLEY_SEED, noneligible_share=0.80, sizing_discipline=0.0
    )
    vesper_panel = _reported(vesper_history, market, quarter_ends, option_mask)
    peer_panels = [
        _reported(history, market, quarter_ends, option_mask) for history in peer_histories
    ]
    hensley_panel = _reported(hensley_history, market, quarter_ends, option_mask)
    pooled_peer = pd.concat(
        [panel.iloc[-1] for panel in (*peer_panels, hensley_panel)], axis=1
    ).mean(axis=1)
    vesper = _filer_payload(
        VESPER_NAME,
        vesper_history,
        vesper_panel,
        market,
        option_mask,
        peer_book=pooled_peer,
    )
    hensley = _filer_payload(
        HENSLEY_NAME,
        hensley_history,
        hensley_panel,
        market,
        option_mask,
        peer_book=None,
    )
    top_longs = [row["name"] for row in vesper["timeline"]["positions"][:5]]
    return {
        "meta": {
            "generator": "m6_holdings",
            "held_for_gate": True,
            "n_assets": N_ASSETS_M6,
            "n_months": N_MONTHS_M6,
            "market_seed": MARKET_SEED_M6,
            "manager_seeds": [VESPER_SEED, *PEER_SEEDS, HENSLEY_SEED],
            "coverage_min": hp.M6_COVERAGE_MIN,
            "option_flag_share": hp.M6_OPTION_FLAG_SHARE,
            "top_n": hp.M6_TOP_N,
            "persistence_topk": hp.M6_PERSISTENCE_TOPK,
            "overlap_depth": hp.M6_OVERLAP_DEPTH,
            "eligibility_assignment": "round-count, floored-stride, authored without RNG",
            "noneligible_dial_basis": "long slots; gross coverage measured ex post",
        },
        "filers": {name: "synthetic" for name in APPROVED_NAMES},
        "vesper": vesper,
        "hensley": hensley,
        "peers": [
            {"name": name, "latest_reported_names": int((panel.iloc[-1] > 0.0).sum())}
            for name, panel in zip(PEER_NAMES, peer_panels, strict=True)
        ],
        "caveats": list(hp.M6_CAVEATS),
        "short_interest": {"status": "requires FINRA adapter", "top_longs": top_longs},
        "validation": {
            "crop_vs_true": [vesper["audit"], hensley["audit"]],
            "staleness_note": (
                "The monthly simulator cannot run an exact 45-calendar-day distortion audit; "
                "the statutory receipt is rendered, and the exact-lag audit remains deferred."
            ),
        },
    }


def _scan_vesper_seed(start: int = 0, stop: int = 5000) -> int:
    """Development-only bounded recovery helper; never called by build()."""
    market = _market()
    quarter_ends = _quarter_ends(market)
    options = _option_mask(market)
    for seed in range(start, stop):
        history = _manager(market, seed, noneligible_share=0.10, sizing_discipline=1.0)
        panel = _reported(history, market, quarter_ends, options)
        timeline = _timeline(panel)
        breadth = [q["effective_names"] for q in timeline["quarters"]]
        crossing = timeline["first_majority_crossing"]
        coverage = hp.coverage_ratio(history.weights.loc[quarter_ends[-1]], market.eligible)
        if (
            breadth[-1] < breadth[0] - 1.0
            and crossing is not None
            and all(row["quarters_held"] == 6 for row in timeline["positions"][:3])
            and 0.75 <= coverage <= 0.98
        ):
            return seed
    raise RuntimeError(f"no Vesper seed satisfies the exhibit in [{start}, {stop})")


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    return write_json(out_dir / "m6_holdings.json", _payload())
