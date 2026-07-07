"""P3 hire/fire audit generator: a synthetic Goyal-Wahal allocator -> ledger ->
aggregate -> site/data/p3_hirefire.json.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
until certified (cards.yaml stays 'planned'; the integration task flips it). The
allocator follows the Goyal-Wahal behavioral rule (hire on trailing 3y
outperformance, fire on underperformance) over a simulator roster whose managers
all share ONE small information coefficient, so trailing rank is luck: winners are
lucky, losers unlucky, forward gaps mean-revert, and the round-trip value-add
posterior sits at ~0. Demo and live share the SAME ledger/aggregate code path
(spec 5); only the input decision log differs (synthetic here).

Goyal & Wahal (2008), "The Selection and Termination of Investment Management
Firms by Plan Sponsors," Journal of Finance 63(4): 1805-1847. DECISION_VALUE_PRIOR_SCALE
(2%/yr) is provisionally sourced from the cross-sponsor dispersion of round-trip
return differentials in that paper; the exact figure is confirmed at the numerics
gate (docket P3-D1).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.decision_audit import aggregate as agg
from quant_allocator.flagships.decision_audit import ledger, report
from quant_allocator.flagships.decision_audit.journal import (
    JOURNAL_DEFAULT_HORIZON_YEARS,
    DecisionRecord,
)
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

BASE_SEED = 20260707
STRATEGY = "equity_long_short"
DEMO_MONTHS = 132  # 11y: room for trailing 36 + forward 36 around the last review
N_ASSETS = 300
N_MANAGERS = 16
# NUMERICS-GATE P3-D5: one shared small IC for every manager, so trailing-3y rank is
# luck (the Goyal-Wahal precondition). Provisional 0.03; _scan_seeds recovers a
# value/seed reproducing the stylized facts if the gate revises it.
MANAGER_IC = 0.03
# NUMERICS-GATE P3-D6: five review months (one per calendar quarter -> five cohorts),
# each emitting three same-month events (m_bar=3). Chosen so trailing-36 and
# forward-36 windows both fit inside DEMO_MONTHS.
REVIEW_INDICES = (42, 54, 66, 78, 90)
TRAILING_MONTHS = 36
RF_ANNUAL = 0.02  # NUMERICS-GATE P3-D7: synthetic risk-free constant (no real rf in the demo).
COHORT_PATH_WINDOW = 36
_FACTOR_NAMES = ("market", "size", "value", "momentum")

# FICTIONAL fund names (repo rule: no real manager names, ever; banner discloses).
# Authored constants in the roster.MANAGER_NAMES house style.
MANAGER_NAMES: dict[str, str] = {
    "P01": "Harrowmere Capital", "P02": "Kelp Point Advisors",
    "P03": "Bittern Row Partners", "P04": "Sable Creek Capital",
    "P05": "Windlass Partners", "P06": "Cormorant Ridge",
    "P07": "Alderfen Capital", "P08": "Thornevale Advisors",
    "P09": "Marsh Harrier Partners", "P10": "Quill & Reed Capital",
    "P11": "Slateford Partners", "P12": "Nettlebed Advisors",
    "P13": "Gannet Cove Capital", "P14": "Wychelm Partners",
    "P15": "Redstart Capital", "P16": "Fen Ottersby Advisors",
}
_CODES = tuple(sorted(MANAGER_NAMES))

# Authored thesis fragments (spec 3.1: free-text pre-commitments). Assembled with
# the measured trailing number at the decision moment; the ledger never reads them.
_THESIS = {
    "fire": "Trailing 3y in the bottom of the book ({trailing:+.0%}); kill criterion tripped, funding a fresh mandate.",
    "hire": "Trailing 3y top-of-book ({trailing:+.0%}); underwriting continued outperformance over the window.",
    "hold-under-review": "Weak trailing 3y ({trailing:+.0%}) but thesis intact; retained under review rather than fired.",
}
_KILL = "Cut if trailing 2y factor-adjusted alpha < -2%/yr."
KILL_ALPHA_THRESHOLD_ANNUAL = -0.02  # NUMERICS-GATE P3-D8: numeric kill bar (matches _KILL text).
EXPECTED_ALPHA = {"hire": 0.03, "fire": -0.01, "hold-under-review": 0.0}  # NUMERICS-GATE P3-D9


def _simulate_world(seed=BASE_SEED, ic=MANAGER_IC):
    market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=DEMO_MONTHS, seed=seed))
    months = tuple(str(p) for p in market.factor_returns.index)  # "YYYY-MM"
    factors = market.factor_returns.to_numpy()
    returns_by_manager, true_alpha = {}, {}
    for i, code in enumerate(_CODES):
        hist = simulate_manager(
            market, ManagerConfig(information_coefficient=ic, seed=seed * 10 + i)
        )
        returns_by_manager[code] = hist.monthly_returns.to_numpy()
        true_alpha[code] = float(hist.true_alpha_returns.to_numpy().mean())
    rf = np.full(DEMO_MONTHS, RF_ANNUAL / ledger.MONTHS_PER_YEAR)
    benchmark = {STRATEGY: factors[:, 0]}  # market factor as the strategy index proxy
    world = ledger.AuditWorld(
        months=months,
        returns_by_manager=returns_by_manager,
        strategy_by_manager={c: STRATEGY for c in _CODES},
        factors=factors,
        factor_names=_FACTOR_NAMES,
        rf_monthly=rf,
        benchmark_by_strategy=benchmark,
    )
    return world, true_alpha


def _trailing_return(returns, d_index) -> float:
    window = returns[d_index - TRAILING_MONTHS : d_index]
    return float(np.prod(1.0 + window) - 1.0)


def _record(decision_type, code, date, trailing, counterfactual) -> DecisionRecord:
    return DecisionRecord(
        decision_type=decision_type,
        manager_id=code,
        decision_date=date,
        thesis=_THESIS[decision_type].format(trailing=trailing),
        expected_alpha_annual=EXPECTED_ALPHA[decision_type],
        horizon_years=JOURNAL_DEFAULT_HORIZON_YEARS,
        kill_criterion=_KILL,
        kill_alpha_threshold_annual=KILL_ALPHA_THRESHOLD_ANNUAL,
        counterfactual=counterfactual,
    )


def _build_records(world) -> list[DecisionRecord]:
    # Deterministic Goyal-Wahal allocator: rank active by trailing-3y, fire worst /
    # hire best candidate (paired), hold second-worst, plus one unpaired event.
    active = list(_CODES[:8])
    candidates = list(_CODES[8:])
    records: list[DecisionRecord] = []
    for round_i, d in enumerate(REVIEW_INDICES):
        date = world.months[d]
        ranked_active = sorted(
            active, key=lambda c: _trailing_return(world.returns_by_manager[c], d)
        )
        ranked_cand = sorted(
            candidates, key=lambda c: -_trailing_return(world.returns_by_manager[c], d)
        )
        worst, second_worst, third_worst = ranked_active[0], ranked_active[1], ranked_active[2]
        best_cand = ranked_cand[0]

        # 1) Paired fire (round-trip): fire worst, replacement = best candidate.
        records.append(_record("fire", worst, date,
                               _trailing_return(world.returns_by_manager[worst], d), best_cand))
        # 2) Hold-under-review: retain second-worst (the control arm), peer-median.
        records.append(_record("hold-under-review", second_worst, date,
                               _trailing_return(world.returns_by_manager[second_worst], d), "peer-median"))
        # 3) One unpaired event, alternating rung so all three appear across rounds.
        if round_i % 2 == 0:
            records.append(_record("hire", best_cand, date,
                                   _trailing_return(world.returns_by_manager[best_cand], d), "peer-median"))
        else:
            records.append(_record("fire", third_worst, date,
                                   _trailing_return(world.returns_by_manager[third_worst], d), "benchmark"))

        active.remove(worst)
        active.append(best_cand)
        candidates.remove(best_cand)
        candidates.append(worst)
    return records


def _cohort_paths(world, events, records) -> dict:
    fired, replacement = [], []
    for ev, rec in zip(events, records):
        if ev.decision_type == "fire" and ev.counterfactual_rung == "replacement-paired":
            d = ledger.month_index(world, ev.decision_date)
            fired.append(ledger.forward_cumulative_path(
                world.returns_by_manager[ev.manager_id], world.rf_monthly, d, COHORT_PATH_WINDOW))
            replacement.append(ledger.forward_cumulative_path(
                world.returns_by_manager[rec.counterfactual], world.rf_monthly, d, COHORT_PATH_WINDOW))
    return {
        "trailing_window_months": COHORT_PATH_WINDOW,
        "fired": [float(x) for x in np.mean(fired, axis=0)],
        "replacement": [float(x) for x in np.mean(replacement, axis=0)],
    }


def _cohort_id(date: str) -> str:
    year, month = date.split("-")
    return f"{year}Q{(int(month) - 1) // 3 + 1}"


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    world, _true_alpha = _simulate_world()
    records = _build_records(world)
    events = ledger.resolve_events(records, world)

    values = np.array([ev.forward_gap_raw for ev in events])
    cohorts = np.array([_cohort_id(ev.decision_date) for ev in events])
    posterior = agg.aggregate_value_add(values, cohorts)

    per_event_sd = float(values.std(ddof=1))
    n_detect = agg.events_to_detectability(
        true_gap=agg.DECISION_VALUE_PRIOR_SCALE,  # detect an edge the size of the prior scale
        per_event_sd=per_event_sd,
        rho=posterior.intra_cohort_rho,
        events_per_cohort=posterior.events_per_cohort,
        prior_scale=agg.DECISION_VALUE_PRIOR_SCALE,
        level=agg.POSTERIOR_CI_LEVEL,
    )
    detectability = {
        "true_gap": agg.DECISION_VALUE_PRIOR_SCALE,
        "rho": posterior.intra_cohort_rho,
        "events_per_cohort": posterior.events_per_cohort,
        # spec 3.5 sentinel convention: an unattainable N maps to JSON null.
        "n": None if not np.isfinite(n_detect) else n_detect,
    }

    # Scorecard: the first paired hire (a replacement) with its 3y realized figures.
    sc_event = next(ev for ev in events if ev.decision_type == "hire")
    d = ledger.month_index(world, sc_event.decision_date)
    realized_fwd = ledger.forward_excess_return(
        world.returns_by_manager[sc_event.manager_id], world.rf_monthly, d, sc_event.horizon_years)
    realized_fa = ledger.forward_factor_alpha(
        world.returns_by_manager[sc_event.manager_id], world.factors, world.factor_names,
        world.rf_monthly, d, sc_event.horizon_years)
    realized_fa_annual = (1.0 + realized_fa) ** (1.0 / sc_event.horizon_years) - 1.0

    meta = {
        "generator": "p3_hirefire",
        "n_events": len(events),
        "n_managers": N_MANAGERS,
        "strategy": STRATEGY,
        "rf_annual": RF_ANNUAL,
        "prior_scale": agg.DECISION_VALUE_PRIOR_SCALE,
        "min_events": agg.MIN_EVENTS_FOR_AGGREGATE,
        "base_rate_null": 0.0,
        "names": MANAGER_NAMES,
    }
    document = report.pack_report(
        meta=meta,
        events=events,
        posterior=posterior,
        scorecard={"event": sc_event, "realized_forward": realized_fwd,
                   "realized_factor_alpha_annual": realized_fa_annual},
        cohort_paths=_cohort_paths(world, events, records),
        detectability=detectability,
    )
    return write_json(out_dir / "p3_hirefire.json", document)


def _scan_seeds(seeds=range(0, 80)) -> None:
    # Recovery helper (HELD-FOR-GATE note): print seeds whose synthetic allocator
    # reproduces the Goyal-Wahal stylized facts AND keeps N_eff below the 12 gate:
    #   all three rungs present, posterior straddles zero, raw mean refused.
    for seed in seeds:
        world, _ = _simulate_world(seed=seed)
        records = _build_records(world)
        events = ledger.resolve_events(records, world)
        rungs = {ev.counterfactual_rung for ev in events}
        values = np.array([ev.forward_gap_raw for ev in events])
        cohorts = np.array([_cohort_id(ev.decision_date) for ev in events])
        post = agg.aggregate_value_add(values, cohorts)
        straddles = post.posterior_ci[0] < 0.0 < post.posterior_ci[1]
        if len(rungs) == 3 and straddles and post.raw_mean_gated:
            print(f"seed {seed}: n_eff={post.n_effective:.1f} rho={post.intra_cohort_rho:.2f} "
                  f"post_ci={post.posterior_ci}")
