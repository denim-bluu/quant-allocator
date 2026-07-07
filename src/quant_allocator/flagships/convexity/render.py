"""Pure packers: a ScreenResult -> render-ready JSON payload dicts (IntervalStat
/ VerdictChip / PowerGate shapes). No I/O; the generator writes the file.
"""

from __future__ import annotations

import math

from quant_allocator.flagships.convexity.diagnostics import DiagnosticStat
from quant_allocator.flagships.convexity.screen import M2_COMPOSITE_K, ScreenResult


def _num(value: float):
    # NaN (the unplayed rung) serializes as null, never a fabricated number.
    return None if value is None or math.isnan(value) else float(value)


def pack_diagnostic(stat: DiagnosticStat) -> dict:
    return {
        "name": stat.name,
        "point": _num(stat.point),
        "ci_lo": _num(stat.ci_lo),
        "ci_hi": _num(stat.ci_hi),
        "verdict": stat.verdict,
        "played": stat.played,
    }


def pack_power_gate(result: ScreenResult) -> dict:
    if result.gate_open:
        reason = f"Composite renders at T ≥ {result.min_t_flag} months; this track is {result.t}."
    else:
        reason = (
            f"Track length {result.t} < {result.min_t_flag}-month threshold — "
            f"composite withheld; individual interval stats shown instead."
        )
    return {"open": result.gate_open, "min_t_flag": result.min_t_flag, "t": result.t, "reason": reason}


def pack_screen(result: ScreenResult) -> dict:
    return {
        "diagnostics": {name: pack_diagnostic(stat) for name, stat in result.diagnostics.items()},
        "composite": {
            "verdict": result.composite_verdict,
            "chip": result.composite_chip,
            "label": result.composite_label,
            "short_vol_count": result.short_vol_count,
            "playable_count": result.playable_count,
            "k": M2_COMPOSITE_K,
        },
        "power_gate": pack_power_gate(result),
    }
