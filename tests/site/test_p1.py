import shutil
import subprocess
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "p1",
    "title": "Allocation under alpha uncertainty",
    "lane": "P",
    "one_liner": "Given posterior skill, how much capital? Sizing that consumes uncertainty.",
    "decisions": ["size", "redeem"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/p1-allocation.html.j2",
    "data": "p1_allocation.json",
    "spec": "p1-allocation-uncertainty.md",
    "golive": {
        "data_ask": "S1's tier-R inputs (monthly net returns >=36m for >=10 managers with strategy "
                    "labels, factor sets, risk-free) plus a per-manager residual vol (S2 de-smoothed).",
        "sample": "Any T renders honest bands (width carries the honesty); decisive bands need "
                  "T >= 48 and true skill dispersion >= 2%/yr.",
        "effort": "S (+M for the wave-3 policy-regret study).",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "p1_allocation.json",
                site / "data" / "p1_allocation.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs" / "ideas" / "specs" / "p1-allocation-uncertainty.md",
                specs / "p1-allocation-uncertainty.md")
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out", allow_legacy=True)
    return (tmp_path / "out" / "p1.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_assets(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/p1.html" in html
    assert "assets/pages/p1.css" in html
    assert (out / "assets" / "pages" / "p1.css").exists()
    assert "assets/p1-allocation.js" in html
    assert (out / "assets" / "p1-allocation.js").exists()


def test_exhibit_explainer_present(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_gate_ruled_copy_substrings(tmp_path):
    html, _ = _build(tmp_path)
    assert "10th&ndash;90th percentile of posterior-draw weights" in html   # §8.1 band label
    assert "residual volatility constant at 8%/yr" in html                  # §8.2 disclosure
    assert "treat manager posteriors as independent" in html               # §8.3 provisional
    assert "policy-regret study" in html and "pending" in html             # §8.4 study pending
    assert "every band on this page is advisory" in html                   # §8.4 advisory
    assert "fund-or-not" in html                                           # §5 fund-or-not signal
    assert "point optimizer" in html                                       # §5 cautionary contrast


def test_b10_headline_and_contrast_rendered(tmp_path):
    html, _ = _build(tmp_path)
    # Server-rendered from the committed JSON: the headline manager and its verdict.
    assert "Cinderbank Capital" in html
    # 20 band rows, each an IntervalStat (no bare points).
    assert html.count('class="interval-stat"') >= 20
    # The naive-OLS contrast marker and the fund-or-not chip render.
    assert "p1-naive" in html
    assert "p1-chip--fund" in html
    # PowerGate refusal with its threshold arithmetic.
    assert "power-gate" in html
    assert "T &ge; 48" in html or "T ≥ 48" in html


def test_tau_dial_is_precomputed(tmp_path):
    html, _ = _build(tmp_path)
    # The skepticism dial snaps among precomputed τ-scale states (x2/M3 idiom); no client compute.
    assert "data-dial" in html or "p1-dial" in html
    assert "skepticism" in html


def test_tau_states_carry_fixed_domain_and_complete_state_payload(tmp_path):
    html, _ = _build(tmp_path)
    assert html.count("data-domain-min=") == 20
    assert html.count("data-domain-max=") == 20
    assert html.count("data-floor=") >= 80
    assert html.count("data-anchor=") >= 80
    assert html.count("data-ceil=") >= 80
    assert 'aria-live="polite"' in html


def test_tau_click_updates_attributes_copy_geometry_and_aria(tmp_path):
    _html, _ = _build(tmp_path)
    script_path = REPO_ROOT / "site" / "assets" / "p1-allocation.js"
    harness = r"""
const fs = require("fs"), vm = require("vm");
function node(dataset) { return {dataset: dataset || {}, style: {}, textContent: "", title: "",
  attrs: {}, setAttribute(k,v){this.attrs[k]=String(v);}, getAttribute(k){return this.attrs[k];},
  classList:{add(){},remove(){}}}; }
const band=node(), point=node(), naive=node(), value=node(), range=node(), readout=node();
const stat=node({lo:"0.1",point:"0.15",hi:"0.2"}); stat.querySelector=(s)=>({
  ".interval-stat__band":band,".interval-stat__point":point,
  ".interval-stat__value":value,".interval-stat__range":range}[s]);
const rail=node(); rail.querySelector=(s)=>({".interval-stat__band":band,
  ".interval-stat__point":point,".p1-naive":naive}[s]);
function button(scale,floor,anchor,ceil){ const b=node({scale,floor,anchor,ceil});
  b.listeners={}; b.addEventListener=(k,fn)=>b.listeners[k]=fn; return b; }
const buttons=[button("1","0.1","0.15","0.2"),button("2","0.02","0.12","0.26")];
const dial=node(); dial.querySelector=(s)=>s==="[data-dial-readout]"?readout:null;
dial.querySelectorAll=()=>buttons;
const row=node({floor:"0.1",anchor:"0.15",ceil:"0.2",naive:"0.24",domainMin:"0.02",domainMax:"0.26"});
row.querySelector=(s)=>({".p1-band__rail":rail,".p1-dial":dial,".interval-stat":stat}[s]);
global.document={readyState:"complete",querySelectorAll:()=>[row]};
vm.runInThisContext(fs.readFileSync(process.argv[1],"utf8")); buttons[1].listeners.click();
const checks=[row.dataset.floor==="0.02",stat.dataset.lo==="0.02",stat.dataset.point==="0.12",
  stat.dataset.hi==="0.26",value.textContent==="2.0%–26.0%",range.textContent.includes("anchor 12.0%"),
  readout.textContent.includes("×2.0"),buttons[1].attrs["aria-pressed"]==="true",
  buttons[0].attrs["aria-pressed"]==="false",band.style.left==="0.00%",band.style.width==="100.00%",
  point.style.left==="41.67%",naive.style.left==="91.67%",stat.attrs["aria-label"].includes("2.0% to 26.0%")];
if (checks.some(x=>!x)) { console.error(checks); process.exit(1); }
"""
    subprocess.run(["node", "-e", harness, str(script_path)], check=True)


def test_tau_active_and_focus_contrast_tokens_are_explicit():
    css = (REPO_ROOT / "site" / "assets" / "pages" / "p1.css").read_text(encoding="utf-8")
    assert ".p1-dial__btn--active" in css and "background: var(--accent)" in css
    assert "color: var(--paper)" in css
    assert ".p1-dial__btn:focus-visible" in css
    assert "outline: 3px solid var(--accent)" in css
