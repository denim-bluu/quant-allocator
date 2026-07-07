"""M2 §3.6 composite: de-smooth, run the five diagnostics, tally the playable
ones, consult the PowerGate. The composite is an evidence tally, never a scalar
score and never a p-value ("converging evidence, not a p-value" — gate).

De-smoothing (Stage 0, M2 §2) imports S2's `unsmooth`; the drawdown-band reuse
is inside `drawdown_vol_signature`. This module reimplements neither.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.convexity.diagnostics import (
    DiagnosticStat,
    drawdown_vol_signature,
    market_coskew,
    straddle_loading,
    treynor_mazuy,
    updown_beta,
)
from quant_allocator.flagships.tearsheet.pipeline import (
    MONTHS_PER_YEAR,
    DrawdownHypothesis,
    unsmooth,
)

M2_COMPOSITE_K = 3          # NUMERICS-GATE: min playable diagnostics agreeing to flag (M2 §3.6). Docket DK-4.
M2_MIN_T_FLAG = 48          # NUMERICS-GATE: PowerGate threshold; live-sourced from the X1 registry (M2 §4). Docket DK-5.
M2_FALSE_ALARM_MAX = 0.10   # NUMERICS-GATE: composite false-alarm ceiling at T=48 (M2 §4 gate 1). Docket DK-6.
M2_KILL_FALSE_ALARM = 0.20  # NUMERICS-GATE: kill line, 1-in-5 at T=48 (M2 §7). Docket DK-6.

_INVESTIGATE_LABEL = "SHORT-VOL POSTURE — INVESTIGATE"
_UNRESOLVED_LABEL = "NOT RESOLVABLE AT THIS TRACK LENGTH"


@dataclass(frozen=True)
class ScreenResult:
    diagnostics: dict[str, DiagnosticStat]
    playable_count: int
    short_vol_count: int
    gate_open: bool
    min_t_flag: int
    t: int
    composite_verdict: str   # "investigate" | "inconclusive"
    composite_chip: str      # verdict-chip token: "shrink" | "noise"
    composite_label: str
    theta: tuple[float, float, float]
    desmoothed: np.ndarray


def run_screen(returns, mkt, rf_monthly, *, t: int, ptfs=None, seed: int) -> ScreenResult:
    returns = np.asarray(returns, dtype=float)
    mkt = np.asarray(mkt, dtype=float)

    # Stage 0 (M2 §2): de-smooth first, so mark-smoothing autocorrelation is not
    # misread as convexity. The screen runs on the de-smoothed EXCESS return.
    uns = unsmooth(returns)
    series = uns.desmoothed if uns.applied else returns
    excess = series - rf_monthly

    hyp = DrawdownHypothesis(
        sharpe_annual=float(series.mean() / series.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR)),
        vol_annual=float(series.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR)),
    )

    diagnostics = {
        "treynor_mazuy": treynor_mazuy(excess, mkt, seed=seed),
        "updown_beta": updown_beta(excess, mkt, seed=seed),
        "market_coskew": market_coskew(excess, mkt, seed=seed),
        "drawdown_vol": drawdown_vol_signature(series, hyp, seed=seed),
        "straddle_loading": straddle_loading(excess, ptfs, seed=seed),
    }

    playable = [d for d in diagnostics.values() if d.played]
    short_vol = [d for d in playable if d.verdict == "short-vol-consistent"]
    gate_open = t >= M2_MIN_T_FLAG
    flagged = gate_open and len(short_vol) >= M2_COMPOSITE_K
    return ScreenResult(
        diagnostics=diagnostics,
        playable_count=len(playable),
        short_vol_count=len(short_vol),
        gate_open=gate_open,
        min_t_flag=M2_MIN_T_FLAG,
        t=t,
        composite_verdict="investigate" if flagged else "inconclusive",
        composite_chip="shrink" if flagged else "noise",
        composite_label=_INVESTIGATE_LABEL if flagged else _UNRESOLVED_LABEL,
        theta=(float(uns.theta[0]), float(uns.theta[1]), float(uns.theta[2])),
        desmoothed=series,
    )
