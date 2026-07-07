"""E2 engagement-pack generator: project committed source-card payloads -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
until certified with the rest of wave-2 batch-1. E2 computes NOTHING of its own:
it reads the CERTIFIED payloads other cards already emit into site/data/
(s2_tearsheet, m5_saydo, x1_atlas thresholds, s1_ledger roster), selects and
orders the sections the manager's tier and the X1 PowerGate registry permit, and
binds HAND-AUTHORED narration (the demo is human-edited; the live build adds the
auto-narration harness, spec §5 "Demo vs. live"). One manager: the fictional
Kestrelmoor Partners (M07). The pack shows a real PowerGate refusal (posterior
standing, X1 null threshold — the Plan-D refusal state) and a real tier-omitted
footer entry (exposure drift, min_tier E). Numeric faithfulness is enforced by
compose -> lint_pack before this file is written.
"""

from __future__ import annotations

import json
from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.packs.compose import compose

# Authored demo identity. Kestrelmoor Partners is the existing fictional name S2
# and M5 use (repo rule: no real manager names; the banner discloses fiction).
PACK_MANAGER_CODE = "M07"
PACK_MANAGER_NAME = "Kestrelmoor Partners"
PACK_TIER = "R"
# NUMERICS-GATE E2-05: authored as-of quarter for the demo pack (the last M5
# exposure month is 2021-06). No statistic depends on it; it labels the header.
PACK_QUARTER = "2021-Q2"

# Hand-authored narration. Every numeral below is one of the certified display
# values of its section (compose -> lint_pack fails the build otherwise).
SUMMARY = (
    "Kestrelmoor Partners, returns-only tier. The tear sheet is honest — a "
    "reported Sharpe of 0.71 that de-smooths to 0.60, an alpha interval that "
    "still spans zero. Skill standing stays gated at 48 months, and the "
    "exposure-drift panel waits for tier-E data. Nothing here is asserted "
    "beyond what its source card certified."
)
TEAR_NARRATION = (
    "Getmansky–Lo–Makarov de-smoothing pulls the reported Sharpe of "
    "0.71 down to 0.60 once the volatility smoothed marks hide is restored. The "
    "annualized alpha's 90% interval runs -4.4% to +10.8% and still spans zero, "
    "so the chip reads provisionally alternative beta — a track-length "
    "statement, not a verdict on skill."
)
SAY_DO_NARRATION = (
    "Three stated views from the letter — disciplined net exposure, a value "
    "tilt, and trimmed momentum. At the returns-only tier the pack lists what the "
    "manager said; the say–do alignment against the measured book unlocks at "
    "tier E."
)
STANDING_REFUSAL = (
    "What this section will hold — the posterior probability the manager's "
    "alpha is genuinely positive — cannot be stated yet: at 48 months no "
    "tenure in the sampler atlas separates a true IR of 0.5 from luck. The pack "
    "shows the gate, not a number it cannot defend."
)
DRIFT_OMIT_REASON = "requires exposure summaries (tier-E data ask)"


def _read(out_dir: Path, name: str) -> dict:
    # Inputs are always the COMMITTED payloads in site/data/; out_dir is only the
    # write target (mirrors the S2/M5 test signature).
    return json.loads((SITE_DATA_DIR / name).read_text(encoding="utf-8"))


def _tear_sheet_body(s2: dict) -> dict:
    st = s2["statistics"]
    ab = s2["alt_beta"]

    def interval(label, stat, level, pct=False):
        if pct:
            value = f"{stat['point'] * 100:+.1f}%"
            rng = f"{level} interval {stat['ci_lo'] * 100:+.1f}% … {stat['ci_hi'] * 100:+.1f}%"
            numbers = [value, f"{stat['ci_lo'] * 100:+.1f}%", f"{stat['ci_hi'] * 100:+.1f}%", level]
        else:
            value = f"{stat['point']:.2f}"
            rng = f"{level} interval {stat['ci_lo']:.2f} … {stat['ci_hi']:.2f}"
            numbers = [value, f"{stat['ci_lo']:.2f}", f"{stat['ci_hi']:.2f}", level]
        return (
            {"kind": "interval", "label": label, "point": stat["point"],
             "ci_lo": stat["ci_lo"], "ci_hi": stat["ci_hi"], "level": level,
             "value": value, "range": rng},
            numbers,
        )

    rep, rep_n = interval("Reported Sharpe", st["sharpe_reported"], "95%")
    des, des_n = interval("De-smoothed Sharpe", st["sharpe_desmoothed"], "95%")
    alpha, alpha_n = interval("Annualized alpha", st["alpha"], "90%", pct=True)
    verdict = {"kind": "verdict", "label": "Alt-beta", "verdict": "shrink", "chip": ab["chip"]}

    display = sorted(set(rep_n + des_n + alpha_n))
    return {
        "provenance": {"card": "s2", "metric": "tear_sheet", "as_of": PACK_QUARTER},
        "narration": TEAR_NARRATION,
        "display_numbers": display,
        "stats": [rep, des, alpha, verdict],
        "views": [],
    }


def _say_do_body(m5: dict) -> dict:
    # Tier R: the letter-view INVENTORY only (no alignment rung, no exposure
    # numbers) — spec §2 R row. Qualitative, so display_numbers is empty and any
    # numeral in the narration is a hallucination the lint would reject.
    views = [
        {"direction": v["direction"], "theme": v["theme"],
         "conviction": v["conviction"], "quote": v["quote"]}
        for v in m5["views"]
    ]
    return {
        "provenance": {"card": "m5", "metric": "letter_views", "as_of": m5["views"][0]["letter_date"]},
        "narration": SAY_DO_NARRATION,
        "display_numbers": [],
        "stats": [],
        "views": views,
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    s2 = _read(out_dir, "s2_tearsheet.json")
    m5 = _read(out_dir, "m5_saydo.json")
    x1 = _read(out_dir, "x1_atlas.json")
    s1 = _read(out_dir, "s1_ledger.json")

    # Read-only against the X1 sampler registry (Plan-D thresholds). E2 chooses
    # no threshold — the null threshold is X1's, audited in the X1 spec.
    powergate_registry = x1["registry_snippet"]

    # s1_ledger is read to record that M07 is not in the S1 roster; the rendered
    # refusal reason is the X1 null-threshold gate (belt-and-suspenders honesty).
    roster_codes = {m["code"] for m in s1["managers"]}
    meta = {
        "generator": "e2_pack",
        "manager_code": PACK_MANAGER_CODE,
        "manager_name": PACK_MANAGER_NAME,
        "tier": PACK_TIER,
        "quarter": PACK_QUARTER,
        "registry_version": powergate_registry["version"],
        "s1_posterior_available": PACK_MANAGER_CODE in roster_codes,
    }

    pack = compose(
        meta=meta,
        sections_in={
            "tear_sheet": _tear_sheet_body(s2),
            "say_do": _say_do_body(m5),
        },
        gate_quantities={"months": s2["meta"]["months"]},  # 48
        powergate_registry=powergate_registry,
        summary=SUMMARY,
        refusal_narration={"posterior_standing": STANDING_REFUSAL},
        omitted_reason={"exposure_drift": DRIFT_OMIT_REASON},
    )
    return write_json(out_dir / "e2_pack.json", pack)
