import numpy as np
import pytest

from quant_allocator.flagships.drift import bands, detector


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


def _band():
    return bands.BandSpec(lower=-0.10, upper=0.10, delta=0.05)


def test_breach_flags_respect_dead_band():
    band = _band()  # breach when x < -0.15 or x > 0.15
    path = np.array([0.0, 0.12, 0.16, -0.16, 0.10])
    flags = detector.breach_flags(path, band)
    assert flags.tolist() == [False, False, True, True, False]


def test_cusum_does_not_fire_on_transient_pokes_over_edge():
    # A book poking a hair over U for single isolated months must not accumulate to h.
    band = _band()
    path = np.array([0.0, 0.13, 0.0, 0.12, 0.0, 0.11, 0.0])
    alarm = detector.cusum_alarm(path, band, k=0.0125, h=0.30)
    assert alarm.fired is False
    assert alarm.alarm_month is None


def test_cusum_fires_on_sustained_walk_beyond_edge():
    # A sustained walk past U out-accumulates k and climbs past h.
    band = _band()
    path = np.concatenate([np.full(5, 0.0), np.linspace(0.15, 0.45, 12)])
    alarm = detector.cusum_alarm(path, band, k=0.0125, h=0.30)
    assert alarm.fired is True
    assert alarm.side == "upper"
    assert alarm.alarm_month >= 5  # only after the walk begins
    assert alarm.s_plus.shape == path.shape


def test_cusum_lower_side_fires_below_band():
    band = _band()
    path = np.concatenate([np.full(3, 0.0), np.linspace(-0.15, -0.45, 12)])
    alarm = detector.cusum_alarm(path, band, k=0.0125, h=0.30)
    assert alarm.fired is True
    assert alarm.side == "lower"


def test_detection_delay_is_alarm_minus_onset():
    assert detector.detection_delay(9, 5) == 4
    assert detector.detection_delay(None, 5) is None


def test_run_length_rung_fires_k_of_m_outside_band():
    band = _band()  # outside means < -0.15 or > 0.15
    path = np.array([0.0, 0.16, 0.0, 0.16, 0.16])  # 3-of-4 in the last window at t=4
    fired_at = detector.run_length_rung(path, band, k_consec=3, m_window=4)
    assert fired_at == 4


def test_run_length_rung_silent_when_below_k():
    band = _band()
    path = np.array([0.0, 0.16, 0.0, 0.0, 0.16])
    assert detector.run_length_rung(path, band, k_consec=3, m_window=4) is None


def test_factor_share_rises_as_betas_grow():
    cov = np.diag([0.02, 0.01, 0.01, 0.01])  # monthly factor variances
    small = detector.factor_share(np.array([0.1, 0.0, 0.0, 0.0]), cov, idio_var=0.01)
    large = detector.factor_share(np.array([0.6, 0.0, 0.0, 0.0]), cov, idio_var=0.01)
    assert 0.0 <= small <= 1.0
    assert large > small


def test_rolling_beta_recovers_a_known_market_beta():
    rng = np.random.default_rng(0)
    factors = rng.normal(0.0, 0.04, size=(40, 4))
    true_beta = 0.7
    returns = true_beta * factors[:, 0] + rng.normal(0.0, 0.001, size=40)
    path = detector.rolling_beta_path(returns, factors, window=24)
    assert np.isnan(path[:23]).all()
    assert path[-1] == pytest.approx(true_beta, abs=0.05)
