"""Stated-band schema and per-class materiality dead-bands for the M1 drift monitor.

Every dead-band is declared in one table (the M5 §3.2 pattern) so a reviewer sees
each provisional δ at once. All values are UNCALIBRATED demo constants HELD FOR THE
NUMERICS GATE (M1 spec §3.2, §"constants"). Units follow the exposure class:
net/gross in exposure units, factor betas in beta units.
"""

from __future__ import annotations

from dataclasses import dataclass

# NUMERICS-GATE: band assumed when a mandate leaves net beta unstated (M1 spec §3.1);
# marked `assumed` so a reader never mistakes a default for a stated limit.
NET_BETA_BAND_DEFAULT: tuple[float, float] = (-0.10, 0.10)

# NUMERICS-GATE: per-class materiality dead-band δ_j — the move below which an excursion
# is disclosure noise, not a statement (M1 spec §3.2, §"constants" DELTA_BAND row).
# Only the classes the simulator emits are listed; sector (3 ppt) / duration (0.25 y)
# from the spec table are live-only and not exercised by the synthetic demo.
DELTA_BAND: dict[str, float] = {
    "net": 0.05,
    "gross": 0.15,
    "beta_market": 0.10,
    "beta_size": 0.10,
    "beta_value": 0.10,
    "beta_momentum": 0.10,
}


@dataclass(frozen=True)
class BandSpec:
    """A stated exposure band [lower, upper] with its materiality dead-band δ.

    assumed=True marks a band the monitor supplied from NET_BETA_BAND_DEFAULT because
    the mandate left the class unstated (M1 spec §3.1).
    """

    lower: float
    upper: float
    delta: float
    assumed: bool = False

    @property
    def center(self) -> float:
        return (self.lower + self.upper) / 2.0

    @property
    def half_width(self) -> float:
        return (self.upper - self.lower) / 2.0


def band_for_class(exposure_class: str, stated: tuple[float, float] | None = None) -> BandSpec:
    delta = DELTA_BAND[exposure_class]  # KeyError names an unmodelled class
    if stated is None:
        lower, upper = NET_BETA_BAND_DEFAULT
        return BandSpec(lower=lower, upper=upper, delta=delta, assumed=True)
    return BandSpec(lower=stated[0], upper=stated[1], delta=delta, assumed=False)
