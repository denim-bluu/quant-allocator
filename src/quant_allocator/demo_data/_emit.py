"""Deterministic JSON writer shared by every demo-data generator.

Sorted keys + fixed float precision + trailing newline make committed JSON a
stable PR diff — that diff is the artifact the numerics gate reviews
(gallery design §8).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# site/data/ resolved relative to this file: demo_data/_emit.py -> repo/site/data
SITE_DATA_DIR = Path(__file__).resolve().parents[3] / "site" / "data"


def round_floats(obj: Any, ndigits: int = 6) -> Any:
    if isinstance(obj, float):
        # + 0.0 normalizes IEEE -0.0 (a tiny negative rounding to zero) to 0.0,
        # so no generator can emit "-0.0" into committed JSON (numerics gate).
        return round(obj, ndigits) + 0.0
    if isinstance(obj, dict):
        return {key: round_floats(value, ndigits) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_floats(value, ndigits) for value in obj]
    return obj


def round_sigfigs(obj: Any, sigfigs: int = 4) -> Any:
    # X2 spec §5: playground JSON rounds every value to 4 significant figures
    # (round_floats' fixed-decimal rounding would waste bytes on small values
    # and under-round large ones). inf/-inf/nan pass through unrounded — a
    # generator maps its own sentinel values (e.g. "no threshold reached") to
    # JSON null *before* calling this, since json.dumps cannot emit inf/nan.
    if isinstance(obj, float):
        if obj == 0.0:
            # +0.0 normalizes IEEE -0.0 to 0.0, matching round_floats (numerics gate).
            return 0.0
        if not math.isfinite(obj):
            return obj
        digits = sigfigs - int(math.floor(math.log10(abs(obj)))) - 1
        return round(obj, digits) + 0.0
    if isinstance(obj, dict):
        return {key: round_sigfigs(value, sigfigs) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_sigfigs(value, sigfigs) for value in obj]
    return obj


def write_json(path: Path, data: dict, *, ndigits: int = 6, sig: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rounded = round_sigfigs(data, sig) if sig is not None else round_floats(data, ndigits)
    text = json.dumps(rounded, sort_keys=True, indent=2)
    # "</" -> "<\/" (identical JSON: \/ is the escaped solidus) so committed
    # data can never terminate the <script> block the demo pages inline it into.
    text = text.replace("</", "<\\/")
    path.write_text(text + "\n", encoding="utf-8")
    return path
