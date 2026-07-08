"""PowerGate registry generator: writes site/data/powergate_registry.json.

The registry is the shared gate table demo generators read to decide whether a
PowerGate renders a statistic or refuses. S3's sizing lab (s3_lab.py) reads the
`hit_rate` and `sizing_slope` thresholds from this file so Thornwood Select's
refusal arithmetic quotes a registry value, never a hardcoded number.

NUMERICS-GATE: the two thresholds are AUTHORED INTERIM constants, not computed
from the X1 atlas cells. They are flagged `status: "interim"` at the top level and
per-metric `provenance` so the numerics gate reads them as provisional. The X1
atlas's own reference-effect thresholds are inf/null ("no measured tenure clears
the gate within T<=120"; x_grid.py ~lines 77-89 and x1_atlas.json's null-threshold
registry_snippet), so there is no finite reference row to carry verbatim — this
registry emits only the two interim rows.
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json

REGISTRY_VERSION = 1
# Both gates are counted in independent trades (x_grid.GATE_UNITS; the X1 registry
# snippet uses the same quantity), so the threshold's units are self-documenting.
GATE_QUANTITY = "independent_trades"
INTERIM_PROVENANCE = "interim: NUMERICS-GATE, pending S3 atlas cells"

# NUMERICS-GATE: authored interim thresholds in independent trades. Provisional
# pending the S3 atlas cells (wave 3); NOT computed. See module docstring.
HIT_RATE_THRESHOLD = 780
SIZING_SLOPE_THRESHOLD = 780


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    payload = {
        "version": REGISTRY_VERSION,
        "status": "interim",
        "metrics": {
            "hit_rate": {
                "gate_quantity": GATE_QUANTITY,
                "threshold": HIT_RATE_THRESHOLD,
                "provenance": INTERIM_PROVENANCE,
            },
            "sizing_slope": {
                "gate_quantity": GATE_QUANTITY,
                "threshold": SIZING_SLOPE_THRESHOLD,
                "provenance": INTERIM_PROVENANCE,
            },
        },
    }
    return write_json(out_dir / "powergate_registry.json", payload)
