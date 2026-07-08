"""S5 short-book quality generator: two long/short managers -> pipeline -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. Demo numbers and any future live
numbers come from the SAME pipeline (S5 spec §5); only the input data is synthetic.
The centerpiece: two managers with identical structures (160 gross / 20 net, 40
longs, 25 shorts, same long-side skill) whose short sleeves are BOTH ~80% hedge by
variance and differ only in short-side signal quality — Saxbridge Capital (short
IC 0.06, a signal short) vs Drybrook Capital (short IC 0.00, a noise-picked hedge).
The fee-relevant difference lives entirely in the borrow-adjusted residual.

CI renders from JSON only; CI never computes (demo-layer doctrine).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.shortbook import pipeline as sb
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

# NUMERICS-GATE: demo world. n_assets=120 breadth matches the §4 teaching mock; T=120 is
# S5_DEMO_MONTHS (§8 ruling 2, deliberately generous). Seeds decorrelated from S1/S2/M3.
S5_MARKET_SEED = 20260710
# Re-scanned per Task 2 Step 6 (house _scan_seeds pattern): seed 41's Saxbridge alpha interval
# fell below zero partway up the 0-5% borrow dial, tripping the §5 "stays calibrated across the
# whole dial" invariant. Seed 108 is the pinned demo authoring choice where Saxbridge's 90%
# lower bound clears the full 5%/yr drag (HS 0.835) while Drybrook never calibrates (HS 0.843).
S5_MANAGER_SEED = 108
N_ASSETS = 120
S5_DEMO_MONTHS = 120
S5_TOGGLE_MONTHS = 60
N_LONG, N_SHORT = 40, 25
TARGET_GROSS, TARGET_NET = 1.6, 0.2
LONG_IC = 0.06                 # §6.5 demo dial: long IC = short IC = 0.06 for the alpha book.
HALF_LIFE = 6.0
TURNOVER = 0.25                # rebalance_fraction; the X1 independent-trade count uses it.
# NUMERICS-GATE: borrow-dial sweep, 0-5%/yr in 0.5% steps (§5, the Dietvorst control).
BORROW_DIAL_FEES = tuple(round(0.005 * i, 3) for i in range(11))
_FEE_LINE = (
    "this sleeve is priced as alpha and measures as hedge; an index overlay "
    "replicates the hedge component at near-zero fee and no borrow"
)
# The two demo managers (§5; §8 ruling 6 rename Kestrel Point -> Saxbridge).
_MANAGERS = (
    {"role": "alpha", "name": "Saxbridge Capital", "short_ic": 0.06},
    {"role": "hedge", "name": "Drybrook Capital", "short_ic": 0.00},
)


def _simulate(short_ic: float):
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=S5_DEMO_MONTHS, seed=S5_MARKET_SEED)
    )
    history = simulate_manager(
        market,
        ManagerConfig(
            n_long=N_LONG, n_short=N_SHORT, target_gross=TARGET_GROSS, target_net=TARGET_NET,
            information_coefficient=LONG_IC, short_information_coefficient=short_ic,
            alpha_half_life_months=HALF_LIFE, rebalance_fraction=TURNOVER, seed=S5_MANAGER_SEED,
        ),
    )
    return market, history


def _borrow_dial(alpha_pnl, short_gross, gross_ci) -> list[dict]:
    avg_short_gross = float(np.mean(short_gross))
    grid = []
    for fee in BORROW_DIAL_FEES:
        drag = fee * avg_short_gross
        lo, hi = gross_ci[0] - drag, gross_ci[1] - drag
        grid.append(
            {
                "fee": float(fee),
                "net": float(12.0 * np.mean(alpha_pnl) - drag),
                "net_ci_lo": float(lo),
                "net_ci_hi": float(hi),
                "calibrated": bool(lo > 0.0),
            }
        )
    return grid


def _panel(spec: dict, market, history) -> dict:
    betas = market.betas.to_numpy()
    factors = market.factor_returns.to_numpy()
    idio = market.idio_returns.to_numpy()
    weights = history.weights.to_numpy()
    asset_returns = market.asset_returns.to_numpy()
    market_col = list(market.config.factor_names).index("market")

    decomp = sb.decompose_short_sleeve(weights, betas, factors, idio)
    hs = sb.hedge_share(decomp)
    short_alpha = sb.borrow_adjusted_alpha(
        decomp.alpha_pnl, sb.BORROW_COST_ANNUAL, decomp.short_gross
    )
    verdict = sb.verdict_chip(short_alpha)
    fee_line = _FEE_LINE if (hs > sb.HEDGE_SHARE_HIGH and not short_alpha.calibrated) else None

    hit_full = sb.hit_rate_gate(
        weights, asset_returns, n_short=N_SHORT, turnover=TURNOVER, months=S5_DEMO_MONTHS
    )
    hit_reduced = sb.hit_rate_gate(
        weights[:S5_TOGGLE_MONTHS], asset_returns[:S5_TOGGLE_MONTHS],
        n_short=N_SHORT, turnover=TURNOVER, months=S5_TOGGLE_MONTHS,
    )
    rd = sb.regression_fallback(decomp.sleeve_pnl, factors, market.config.factor_names)

    def _gate(g):
        return {"hit_rate": g.hit_rate, "hit_t": g.hit_t, "trades": g.trades,
                "gate": g.gate, "renders": g.renders}

    return {
        "role": spec["role"],
        "name": spec["name"],
        "short_ic": spec["short_ic"],
        "hedge_share": hs,
        "hedge_share_gloss": f"~{round(hs * 100)}% of this sleeve's month-to-month behavior "
                             "is factor offset",
        "gross_alpha_annual": short_alpha.gross_annual,
        "gross_ci": list(short_alpha.gross_ci),
        "borrow_drag_annual": short_alpha.borrow_drag_annual,
        "net_alpha_annual": short_alpha.net_annual,
        "net_ci": list(short_alpha.net_ci),
        "verdict": verdict,
        "fee_line": fee_line,
        "cum_hedge": [float(x) for x in np.cumsum(decomp.hedge_pnl)],
        "cum_alpha": [float(x) for x in np.cumsum(decomp.alpha_pnl)],
        "exposure_market": [float(x) for x in decomp.exposure_path[:, market_col]],
        "borrow_dial": _borrow_dial(decomp.alpha_pnl, decomp.short_gross, short_alpha.gross_ci),
        "hit_full": _gate(hit_full),
        "hit_reduced": _gate(hit_reduced),
        "r_disclosed": {
            "alpha_annual": rd.alpha_annual,
            "ci": list(rd.ci),
            "r2": rd.r2,
            "chip": "manager-disclosed attribution",
        },
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    split = []
    for spec in _MANAGERS:
        market, history = _simulate(spec["short_ic"])
        split.append(_panel(spec, market, history))
    payload = {
        "meta": {
            "generator": "s5_shortbook",
            "months": S5_DEMO_MONTHS,
            "toggle_months": S5_TOGGLE_MONTHS,
            "n_long": N_LONG,
            "n_short": N_SHORT,
            "gross": TARGET_GROSS,
            "net": TARGET_NET,
            "short_gross_avg": (TARGET_GROSS - TARGET_NET) / 2.0,
            "turnover": TURNOVER,
            "borrow_cost_annual": sb.BORROW_COST_ANNUAL,
            "hedge_share_high": sb.HEDGE_SHARE_HIGH,
            "short_trade_gate": sb.SHORT_TRADE_GATE,
            "alpha_ci_level": sb.ALPHA_CI_LEVEL,
            "factor_names": list(MarketConfig().factor_names),
        },
        "split": split,
    }
    return write_json(out_dir / "s5_shortbook.json", payload)
