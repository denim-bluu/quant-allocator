"""Circular block bootstrap harness shared by the M2 diagnostics (M2 spec §3.3).

Adopts S2 §3.3's method — block length ≈ T^{1/3}, circular wrap — so the
reported uncertainty carries the serial dependence the third-moment and
interaction estimators are especially fragile to. The interval is the
percentile interval, clipped to contain the point estimate.

NOTE (docket DK-9): S2's pipeline bootstraps (Sharpe, alpha) are estimator-
specific private helpers with closed-form SEs, so they are not directly
reusable for M2's new estimators. This harness deliberately does NOT refactor
pipeline.py into a shared primitive — that extraction would collide, in a
parallel worktree, with the M3 plan's authorised pipeline.py edit. Full
studentization (a per-replicate SE) is deferred: M2's estimators have no
closed-form SE and a double bootstrap is disproportionate for the demo; the
percentile interval still carries the serial dependence, which is the property
§3.3 cares about.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np


def block_bootstrap_ci(
    estimator: Callable[..., float],
    arrays: Sequence[np.ndarray],
    *,
    level: float,
    n_boot: int,
    seed: int,
    stream_tag: int,
) -> tuple[float, float]:
    """Percentile circular-block-bootstrap CI for an arbitrary estimator.

    ``arrays`` are resampled jointly by circular blocks so pairing (e.g. return
    with its market factor) is preserved. The returned interval is clipped to
    contain ``estimator(*arrays)`` so ``ci_lo <= point <= ci_hi`` always holds.
    """
    t = len(arrays[0])
    if any(len(a) != t for a in arrays):
        raise ValueError("all bootstrap arrays must share length T")
    block = max(1, round(t ** (1.0 / 3.0)))
    n_blocks = int(np.ceil(t / block))
    rng = np.random.default_rng([seed, stream_tag])
    point = float(estimator(*arrays))
    reps = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, t, size=n_blocks)
        offsets = (starts[:, None] + np.arange(block)[None, :]) % t  # circular wrap
        idx = offsets.ravel()[:t]
        reps[b] = estimator(*(np.asarray(a)[idx] for a in arrays))
    lo_q, hi_q = np.quantile(reps, [(1 - level) / 2, 1 - (1 - level) / 2])
    return (min(float(lo_q), point), max(float(hi_q), point))
