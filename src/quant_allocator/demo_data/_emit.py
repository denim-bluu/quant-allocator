"""Deterministic JSON writer shared by every demo-data generator.

Sorted keys + fixed float precision + trailing newline make committed JSON a
stable PR diff — that diff is the artifact the numerics gate reviews
(gallery design §8).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# site/data/ resolved relative to this file: demo_data/_emit.py -> repo/site/data
SITE_DATA_DIR = Path(__file__).resolve().parents[3] / "site" / "data"


def round_floats(obj: Any, ndigits: int = 6) -> Any:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {key: round_floats(value, ndigits) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_floats(value, ndigits) for value in obj]
    return obj


def write_json(path: Path, data: dict, *, ndigits: int = 6) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(round_floats(data, ndigits), sort_keys=True, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
    return path
