"""M2 hidden-convexity generator: paired synthetic managers -> full screen -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. Demo numbers and any future
live numbers come from the SAME code path (`screen.run_screen`); only the input
data differs (synthetic here). Two managers share one market and one base return
stream; the overlaid one wears a WrittenPutOverlay with an in-sample fair
premium (M2_OVERLAY_FAIR) so their REPORTED Sharpe matches to two decimals while
the overlaid left tail fattens. The screen separates them; the stress months are
the receipts. Overlay params + seed are pinned by `_scan_overlay` (recovery
helper), analogous to S2's `_scan_manager_seeds`.

DISCLOSURE (binding, wave-2 dials plan): the overlay's in-sample fair-premium is
a deliberate look-ahead for a controlled demo, NOT live methodology — a real
short-vol book's premium is ex-ante. The page carries this note.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.roster import MANAGER_NAMES
from quant_allocator.flagships.convexity.render import pack_screen
from quant_allocator.flagships.convexity.screen import run_screen
from quant_allocator.flagships.tearsheet.pipeline import MONTHS_PER_YEAR
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.overlays import WrittenPutOverlay, apply_written_put_overlay

BASE_SEED = 20260707
MANAGER_MONTHS = 48
N_ASSETS = 300
MANAGER_IC = 0.05
# FICTIONAL display names (repo rule; banner discloses). Paired managers.
HONEST_CODE = "B05"      # Wrenmoor Partners
OVERLAID_CODE = "B06"    # Gullwing Point Capital
STRATEGY = "equity_long_short"
RF_ANNUAL = 0.02         # NUMERICS-GATE D-21 convention: synthetic risk-free constant.

# NUMERICS-GATE M2-DEMO: overlay params + manager seed PINNED by _scan_overlay so the
# authored outcome holds (matched 2-dp Sharpe; overlaid flags, honest does not;
# ≥1 stress month). Provisional pending the numerics gate. Docket DK-7.
# NOTE for the gate: matched Sharpe at a composite-flagging overlay is only
# reachable on this simulator where the honest manager's realized Sharpe is
# near zero — the gap is SR_h * (1 - sigma_h / sigma_o), so only a low-SR seed
# absorbs the overlay's added vol without moving the 2-dp rounding. The pinned
# pair reports Sharpe 0.01; kappa is correspondingly large (2.6x book, strike
# at 0.9 market sigma). Whether that pair is an honest demonstration or a
# degenerate corner is a DK-7 ruling.
DEMO_MANAGER_SEED = 1839
DEMO_KAPPA = 2.6
DEMO_STRIKE_MONEYNESS = 0.9
DEMO_SHARPE_TOL = 0.005  # NUMERICS-GATE M2-DEMO: max |Sharpe gap| so both round equal. Docket DK-8.


def _annual_sharpe(series: np.ndarray) -> float:
    return float(series.mean() / series.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR))


def _sharpe_stat(series: np.ndarray) -> dict:
    # Reuse S2's Lo-SE Sharpe interval so the pair is interval-reported, not bare.
    from quant_allocator.flagships.tearsheet.pipeline import sharpe_intervals
    s = sharpe_intervals(series, seed=BASE_SEED)
    return {"point": s.sharpe_annual, "ci_lo": s.boot_ci[0], "ci_hi": s.boot_ci[1]}


def _simulate_pair():
    market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=MANAGER_MONTHS, seed=BASE_SEED))
    history = simulate_manager(
        market, ManagerConfig(information_coefficient=MANAGER_IC, seed=DEMO_MANAGER_SEED)
    )
    mkt = market.factor_returns["market"]
    honest = history.monthly_returns
    honest.index = mkt.index
    overlay = WrittenPutOverlay(
        strike_moneyness=DEMO_STRIKE_MONEYNESS, overlay_notional=DEMO_KAPPA, fair_premium=True
    )
    overlaid = apply_written_put_overlay(honest, mkt, overlay)
    return honest, overlaid, mkt, overlay


def _manager_block(code: str, series: np.ndarray, mkt: np.ndarray) -> dict:
    rf = RF_ANNUAL / MONTHS_PER_YEAR
    result = run_screen(series, mkt, rf, t=MANAGER_MONTHS, seed=BASE_SEED)
    return {
        "code": code,
        "name": MANAGER_NAMES[code],
        "sharpe": _sharpe_stat(np.asarray(series)),
        "theta": list(result.theta),
        "screen": pack_screen(result),
        "monthly_returns": [float(x) for x in np.asarray(series)],
    }


def _stress_months(honest, overlaid, mkt, overlay) -> list[dict]:
    months = [str(p) for p in honest.index]
    f = mkt.to_numpy()
    sigma = float(mkt.std())
    strike = -overlay.strike_moneyness * sigma
    payout = overlay.overlay_notional * np.maximum(strike - f, 0.0)
    rows = []
    for i, month in enumerate(months):
        if payout[i] > 0.0:
            rows.append({
                "month": month,
                "market_factor": float(f[i]),
                "honest_return": float(honest.to_numpy()[i]),
                "overlaid_return": float(overlaid.to_numpy()[i]),
                "payout": float(payout[i]),
            })
    return rows


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    honest, overlaid, mkt, overlay = _simulate_pair()
    payload = {
        "meta": {
            "generator": "m2_convexity",
            "strategy": STRATEGY,
            "months": MANAGER_MONTHS,
            "tier": "R",
            "rf_annual": RF_ANNUAL,
        },
        "overlay": {
            "kappa": overlay.overlay_notional,
            "strike_moneyness": overlay.strike_moneyness,
            "fair_premium": overlay.fair_premium,
        },
        "managers": {
            "honest": _manager_block(HONEST_CODE, honest.to_numpy(), mkt.to_numpy()),
            "overlaid": _manager_block(OVERLAID_CODE, overlaid.to_numpy(), mkt.to_numpy()),
        },
        "stress_months": _stress_months(honest, overlaid, mkt, overlay),
    }
    return write_json(out_dir / "m2_convexity.json", payload)


def _scan_overlay(
    seeds=range(0, 3000),
    kappas=(0.9, 1.1, 1.4, 1.7, 2.0, 2.3, 2.6, 2.8),
    moneynesses=(0.75, 0.9, 1.0, 1.1),
) -> None:
    # Recovery helper (see the header): print (seed, kappa, moneyness) whose paired
    # managers satisfy the authored outcome. NOT part of the build. Pin the first
    # hit into DEMO_MANAGER_SEED / DEMO_KAPPA / DEMO_STRIKE_MONEYNESS.
    #
    # The original 40-seed grid was empty: matched 2-dp Sharpe plus a composite
    # flag needs a near-zero-Sharpe honest seed (rare) wearing a large overlay,
    # so the grid is wide and the cheap Sharpe-gap check runs BEFORE the two
    # expensive screens (same predicate, orders of magnitude fewer screens).
    global DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS  # noqa: PLW0603
    saved = (DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS)
    for seed in seeds:
        for kappa in kappas:
            for moneyness in moneynesses:
                DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS = seed, kappa, moneyness
                honest, overlaid, mkt, overlay = _simulate_pair()
                sr_h = _annual_sharpe(honest.to_numpy())
                sr_o = _annual_sharpe(overlaid.to_numpy())
                gap = abs(sr_h - sr_o)
                if gap >= DEMO_SHARPE_TOL or round(sr_h, 2) != round(sr_o, 2):
                    continue
                stress = _stress_months(honest, overlaid, mkt, overlay)
                if not stress:
                    continue
                o_screen = run_screen(overlaid.to_numpy(), mkt.to_numpy(), RF_ANNUAL / MONTHS_PER_YEAR,
                                      t=MANAGER_MONTHS, seed=BASE_SEED)
                if o_screen.composite_chip != "shrink":
                    continue
                h_screen = run_screen(honest.to_numpy(), mkt.to_numpy(), RF_ANNUAL / MONTHS_PER_YEAR,
                                      t=MANAGER_MONTHS, seed=BASE_SEED)
                if h_screen.composite_chip == "noise":
                    print(f"seed={seed} kappa={kappa} moneyness={moneyness} gap={gap:.4f} "
                          f"o_votes={o_screen.short_vol_count}")
    DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS = saved
