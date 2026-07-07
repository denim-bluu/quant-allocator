import numpy as np
import pytest

from quant_allocator.flagships.drift import bands


def test_band_for_class_uses_stated_band_and_delta():
    spec = bands.band_for_class("beta_market", stated=(-0.10, 0.10))
    assert spec.lower == -0.10
    assert spec.upper == 0.10
    assert spec.delta == bands.DELTA_BAND["beta_market"]
    assert spec.assumed is False
    assert spec.center == pytest.approx(0.0)
    assert spec.half_width == pytest.approx(0.10)


def test_band_for_class_falls_back_to_default_marked_assumed():
    spec = bands.band_for_class("beta_market", stated=None)
    assert (spec.lower, spec.upper) == bands.NET_BETA_BAND_DEFAULT
    assert spec.assumed is True


def test_band_for_class_unknown_class_raises():
    with pytest.raises(KeyError):
        bands.band_for_class("duration_10y", stated=(-1.0, 1.0))
