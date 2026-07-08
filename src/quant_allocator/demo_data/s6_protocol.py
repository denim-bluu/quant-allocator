"""S6 §3.5–§3.6 — the FROZEN test statistic, familywise discipline, and taxonomy.

Mann-Whitney AUC (= P(a random positive-class manager outranks a random negative
one); Hanley-McNeil 1982), the Westfall-Young max-statistic familywise permutation
test (control the probability of even ONE false 'this signature carries information'
claim across the six-signature family at alpha; Westfall-Young 1993), the
directional two-part ship rule, and the SHIP / WEAK TELL / NULL taxonomy. This is a
small, closed, PRE-COMMITTED family under FAMILYWISE control — NOT an FDR screen
over an open candidate pool (spec §2 / §6.1). Pure functions over per-class
signature arrays; no simulation, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- FROZEN protocol constants (§8.5) --------------------------------------
S6_AUC_MIN = 0.65            # usability bar a tell must clear to SHIP
S6_FAMILYWISE_ALPHA = 0.05   # familywise error target across the family
S6_N_PERM = 5000             # Westfall-Young permutations (confirmatory)
S6_N_PER_CLASS = 500         # managers per dial class (confirmatory; = X1 N_REPS)
S6_DECISION_T = 60           # deciding evaluation horizon (months)
S6_SECONDARY_T = 36          # reported secondary horizon; NEVER deciding (§8.5)
# Named integer RNG stream tag for the permutation relabeling (no hash()-seeds).
S6_PERMUTATION_STREAM = 6

# --- FROZEN direction table (§3.4) -----------------------------------------
# Only a declared ("+"/"-") cell may SHIP; None is computed and reported but can
# only ever be a WEAK TELL anomaly (§3.4). Two-sided significance is direction-free.
S6_DIRECTIONS: dict[str, dict[str, str | None]] = {
    "autocorr":         {"h_size": None, "h_decay": "-"},
    "vol_of_vol":       {"h_size": "+",  "h_decay": None},
    "skew":             {"h_size": None, "h_decay": None},
    "kurtosis":         {"h_size": "+",  "h_decay": None},
    "drawdown_shape":   {"h_size": "+",  "h_decay": "+"},
    "rolling_ir_slope": {"h_size": None, "h_decay": "-"},
}


@dataclass(frozen=True)
class FamilywiseResult:
    observed: dict[str, float]      # observed AUC per signature (raw, pos vs neg)
    adjusted_p: dict[str, float]    # Westfall-Young familywise-adjusted p per signature
    max_dev_null: np.ndarray        # per-permutation max_k |AUC_k - 0.5| (for the crit-dev mark)


def mann_whitney_auc(pos, neg) -> float:
    """P(a random positive outranks a random negative); ties count half.
    Rank form, O(n log n): AUC = (R_pos - n_pos(n_pos+1)/2) / (n_pos n_neg)."""
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    n_pos, n_neg = pos.size, neg.size
    allv = np.concatenate([pos, neg])
    order = allv.argsort()
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # Average ranks over ties (the Mann-Whitney tie convention).
    _, inverse, counts = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    u = ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u) / (n_pos * n_neg)


def hanley_mcneil_se(auc: float, n_pos: int, n_neg: int) -> float:
    """Hanley-McNeil (1982) SE of the AUC at the OBSERVED value (§8.3), for the
    page band. Q1 = A/(2-A), Q2 = 2A^2/(1+A)."""
    a = float(auc)
    q1 = a / (2.0 - a)
    q2 = 2.0 * a * a / (1.0 + a)
    var = (
        a * (1.0 - a)
        + (n_pos - 1) * (q1 - a * a)
        + (n_neg - 1) * (q2 - a * a)
    ) / (n_pos * n_neg)
    return float(np.sqrt(var)) if var > 0 else 0.0


def familywise_maxauc_test(sig_pos, sig_neg, *, seed: int, n_perm: int = S6_N_PERM) -> FamilywiseResult:
    """Westfall-Young max-statistic familywise-adjusted p-values (§3.6).

    Null: class labels are exchangeable (the dial leaves every signature's
    distribution unchanged). For each relabeling, take the MAX |AUC - 0.5| over
    the whole family; adj p_j = fraction of permutations whose max reaches
    signature j's observed |AUC - 0.5|. The max statistic absorbs the correlation
    among signatures (they share one return path) -> exact familywise control over
    the small pre-committed family, NOT an FDR screen. The +1s make it valid at
    finite n_perm.
    """
    names = list(sig_pos)
    observed = {n: mann_whitney_auc(sig_pos[n], sig_neg[n]) for n in names}
    observed_dev = {n: abs(observed[n] - 0.5) for n in names}
    combined = {n: np.concatenate([sig_pos[n], sig_neg[n]]) for n in names}
    n_pos = len(next(iter(sig_pos.values())))
    total = n_pos + len(next(iter(sig_neg.values())))
    rng = np.random.default_rng([seed, S6_PERMUTATION_STREAM])
    max_dev_null = np.empty(n_perm)
    exceed = {n: 0 for n in names}
    for b in range(n_perm):
        idx = rng.permutation(total)
        pos_idx, neg_idx = idx[:n_pos], idx[n_pos:]
        devs = {
            n: abs(mann_whitney_auc(combined[n][pos_idx], combined[n][neg_idx]) - 0.5)
            for n in names
        }
        m = max(devs.values())
        max_dev_null[b] = m
        for n in names:
            if m >= observed_dev[n]:
                exceed[n] += 1
    adjusted_p = {n: (exceed[n] + 1) / (n_perm + 1) for n in names}
    return FamilywiseResult(observed=observed, adjusted_p=adjusted_p, max_dev_null=max_dev_null)


def directional_auc(auc: float, direction: str | None) -> float | None:
    """Orient the AUC by the pre-declared direction so a declared tell reads > 0.5.
    '-' negates the statistic before ranking, i.e. 1 - auc. None cannot ship (§3.6)."""
    if direction == "+":
        return float(auc)
    if direction == "-":
        return float(1.0 - auc)
    return None


def classify_verdict(
    direction: str | None,
    worst_dir_auc: float | None,
    worst_adj_p: float,
    any_reversed: bool,
    *,
    auc_min: float = S6_AUC_MIN,
    alpha: float = S6_FAMILYWISE_ALPHA,
) -> str:
    """Frozen taxonomy (§3.6). Significance is the INTERSECTION over deciding cells
    (worst_adj_p = max over cells); the ship rule worst-cases the directional AUC.
    SHIP requires a declared direction, significance in every cell, no reversal, and
    the worst-cell directional AUC above the usability bar. Everything real-but-unusable
    -- below the bar, reversed, or undeclared -- is a WEAK TELL. A non-significant cell
    is a NULL (a first-class finding)."""
    if worst_adj_p > alpha:
        return "null"
    if direction is None:
        return "weak_tell"  # undeclared anomaly for a possible v2; never ships
    if any_reversed:
        return "weak_tell"  # significant in the direction opposite to the declaration
    if worst_dir_auc is not None and worst_dir_auc > auc_min:
        return "ship"
    return "weak_tell"      # statistically real, below the usability bar
