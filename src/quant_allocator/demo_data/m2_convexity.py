"""M2 hidden-convexity generator: paired synthetic managers -> full screen -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. Demo numbers and any future
live numbers come from the SAME code path (`screen.run_screen`); only the input
data differs (synthetic here). Two managers share one market and one base return
stream; the overlaid one wears a WrittenPutOverlay whose flat premium is set
RICH OF FAIR (fair_premium=False, DK-7 gate ruling 2026-07-07) — above the
actuarial cost of its payouts — so both books report the SAME healthy Sharpe to
two decimals while the overlaid left tail fattens: the classic carry seduction.
The screen separates them; the stress months are the receipts. Overlay params +
seed are pinned by `_scan_overlay` (recovery helper), analogous to S2's
`_scan_manager_seeds`.

DISCLOSURE (binding, two-sided per the DK-7 ruling): (a) the demo premium is
calibrated in-sample, rich of fair, so the pair matches at a healthy Sharpe — a
deliberate look-ahead for a controlled demo, NOT live methodology (a real
short-vol book's premium is ex-ante); (b) the atlas detection rows measure at
FAIR premium (zero in-sample carry), the conservative case. The page carries
both sides.
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
# DK-7 RULING (numerics gate, 2026-07-07): the fair-premium demo was a degenerate
# corner — with fair_premium=True the Sharpe gap is SR_h * (1 - sigma_h/sigma_o),
# so matched 2-dp Sharpe at a composite-flagging overlay was only reachable at a
# near-zero-Sharpe honest seed. The demo now uses fair_premium=False with
# DEMO_PREMIUM_ANNUAL set RICH of the payouts' actuarial cost, calibrated
# in-sample so both books land at the spec's healthy Sharpe (1.10): the carry
# offsets the vol drag. Detection atlas rows stay at FAIR premium (conservative).
# Pinned hit: smallest kappa whose honest book records zero short-vol votes.
DEMO_MANAGER_SEED = 302
DEMO_KAPPA = 2.2
DEMO_STRIKE_MONEYNESS = 0.85
DEMO_PREMIUM_ANNUAL = 0.1827  # NUMERICS-GATE M2-DEMO: rich-of-fair flat carry (fair value 0.1245). Docket DK-7.
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
        strike_moneyness=DEMO_STRIKE_MONEYNESS,
        overlay_notional=DEMO_KAPPA,
        premium_annual=DEMO_PREMIUM_ANNUAL,
        fair_premium=False,  # DK-7 ruling: rich-of-fair carry, not the fair look-ahead
    )
    overlaid = apply_written_put_overlay(honest, mkt, overlay)
    return honest, overlaid, mkt, overlay


def _fair_value_annual(mkt, overlay) -> float:
    # Actuarial cost of the overlay's payouts (the fair flat carry), annualized —
    # emitted so the page's rich-of-fair disclosure has its benchmark on record.
    f = mkt.to_numpy()
    strike = -overlay.strike_moneyness * float(mkt.std())
    payout = overlay.overlay_notional * np.maximum(strike - f, 0.0)
    return float(payout.mean() * MONTHS_PER_YEAR)


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
            "premium_annual": overlay.premium_annual,
            "fair_value_annual": _fair_value_annual(mkt, overlay),
        },
        "managers": {
            "honest": _manager_block(HONEST_CODE, honest.to_numpy(), mkt.to_numpy()),
            "overlaid": _manager_block(OVERLAID_CODE, overlaid.to_numpy(), mkt.to_numpy()),
        },
        "stress_months": _stress_months(honest, overlaid, mkt, overlay),
    }
    return write_json(out_dir / "m2_convexity.json", payload)


def _scan_overlay(
    seeds=range(0, 1500),
    kappas=(2.0, 2.2, 2.4, 2.6, 2.8),
    moneynesses=(0.85, 0.9, 1.0),
    target_sharpe=1.10,
) -> None:
    # Recovery helper (see the header): print (seed, kappa, moneyness, premium)
    # whose paired managers satisfy the authored outcome. NOT part of the build.
    # Pin a hit into DEMO_MANAGER_SEED / DEMO_KAPPA / DEMO_STRIKE_MONEYNESS /
    # DEMO_PREMIUM_ANNUAL (prefer the smallest kappa whose honest book records
    # zero short-vol votes).
    #
    # DK-7 ruling mechanics: for each combo the flat premium has a closed form
    # that matches the pair's Sharpe exactly —
    #   prem_monthly = mean(payout) + mean_h * (sigma_overlaid / sigma_h - 1)
    # (rich of fair whenever mean_h > 0, since the carry must pay for the vol
    # drag). Only seeds whose honest Sharpe rounds to `target_sharpe` are
    # screened, and the cheap Sharpe checks run BEFORE the expensive screens.
    global DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS, DEMO_PREMIUM_ANNUAL  # noqa: PLW0603
    saved = (DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS, DEMO_PREMIUM_ANNUAL)
    rf = RF_ANNUAL / MONTHS_PER_YEAR
    for seed in seeds:
        DEMO_MANAGER_SEED = seed
        honest, _, mkt, _ = _simulate_pair()
        h = honest.to_numpy()
        sr_h = _annual_sharpe(h)
        if round(sr_h, 2) != round(target_sharpe, 2):
            continue
        f = mkt.to_numpy()
        sigma_f = float(mkt.std())
        for kappa in kappas:
            for moneyness in moneynesses:
                payout = kappa * np.maximum(-moneyness * sigma_f - f, 0.0)
                if not (payout > 0.0).any():
                    continue
                sigma_o = (h - payout).std(ddof=1)
                prem_annual = round(
                    MONTHS_PER_YEAR * (payout.mean() + h.mean() * (sigma_o / h.std(ddof=1) - 1.0)), 4
                )
                if prem_annual <= MONTHS_PER_YEAR * payout.mean():
                    continue  # not rich of fair (needs mean_h > 0)
                DEMO_KAPPA, DEMO_STRIKE_MONEYNESS, DEMO_PREMIUM_ANNUAL = kappa, moneyness, prem_annual
                _, overlaid, mkt, overlay = _simulate_pair()
                sr_o = _annual_sharpe(overlaid.to_numpy())
                gap = abs(sr_h - sr_o)
                if gap >= DEMO_SHARPE_TOL or round(sr_h, 2) != round(sr_o, 2):
                    continue
                o_screen = run_screen(overlaid.to_numpy(), f, rf, t=MANAGER_MONTHS, seed=BASE_SEED)
                if o_screen.composite_chip != "shrink":
                    continue
                h_screen = run_screen(h, f, rf, t=MANAGER_MONTHS, seed=BASE_SEED)
                if h_screen.composite_chip == "noise":
                    print(f"seed={seed} kappa={kappa} moneyness={moneyness} "
                          f"prem_annual={prem_annual} gap={gap:.4f} "
                          f"o_votes={o_screen.short_vol_count} h_votes={h_screen.short_vol_count}")
    DEMO_MANAGER_SEED, DEMO_KAPPA, DEMO_STRIKE_MONEYNESS, DEMO_PREMIUM_ANNUAL = saved
