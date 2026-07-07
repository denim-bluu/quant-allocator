# E1 · Trust-Preserving Transparency Ladder — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [E1 · Trust-preserving transparency ladder](../2026-07-05-idea-cards.md#e1--trust-preserving-transparency-ladder--quick-win-memo)
**Type:** Process / doctrine card (zero code; effort S). This is a *memo*, not an analytic — it ships a negotiation playbook, not an estimator. Where the house spec template asks for a data pipeline, a power test, or a reference implementation, the doctrine equivalent is given and flagged inline.

---

## 1. What this is

This card is a **three-rung playbook for asking a fund manager for more data without damaging the relationship that supplies it.** Each rung names one grant an allocator might request — monthly returns, then exposure summaries, then position files — and pairs it with two things: what the manager gets back in exchange, and the plain statistical reason the ask is warranted. The output is a single page a senior allocator can forward to a peer or lay on the table in a review meeting. There is no model to run and no number to certify; the deliverable is the *argument* for each ask and the *discipline* around making it.

The reader who needs this is the person sitting across from a manager in an **ENGAGE** conversation — a quarterly review, an onboarding discussion, a moment where the question "can you also send us X?" is about to be asked. The ladder exists because transparency in this business is *granted, not owed*: nothing in a typical mandate compels a manager to share exposure buckets or position files, so the depth of data an allocator receives is a resource that is cultivated over time, not a right that is invoked. The way the ask is worded and reciprocated determines whether that resource deepens or collapses. This memo is the house doctrine for making it deepen.

---

## 2. Why we use it

**The decision problem.** Every other analytic in this portfolio — the manager tear sheet, the factor-hygiene pack, the sizing and exit diagnostics — consumes manager data as its input. The richer the tier of data granted, the more those analytics can say. So an allocator has a standing incentive to escalate: to move a manager from monthly returns up to exposure summaries, and from exposures up to positions. The question is *how* to escalate without the escalation itself destroying the supply.

**Why the naive approach fails.** The obvious move is to simply ask — or, worse, to require — more data, framed as verification: "we need your positions so we can check what you are doing." The intuition that this backfires is not folklore; it is a measured result. Falk and Kosfeld (2006), *The Hidden Costs of Control*, ran principal–agent experiments in which a principal could impose a minimum effort on an agent. When the principal exercised that control, agents **cut their effort below what they would have volunteered freely.** The monitoring signal reads as distrust, and the agent reciprocates the distrust by withdrawing. Transpose this to allocation: an analytics program that reads as an audit invites the manager to withdraw the very position and exposure detail the program runs on. The failure mode is therefore not "the manager is mildly annoyed." It is "the data tier that every other card depends on shrinks, and those cards go dark." The asset you were trying to exploit is the asset you destroy.

**What the ladder wins.** By framing each ask as help, attaching it to a question the manager also wants answered, and handing back something useful at every rung, the ladder converts escalation from an extraction into a collaboration. The measurable win is *tier survival*: a grant that persists after the manager sees the first diagnostic, and an escalation-acceptance rate that rises over the life of the relationship rather than triggering a redemption. The decision it primarily improves is **ENGAGE** — it is the team's negotiation script. Secondarily it protects **MONITOR** and **SELECT**, because those decisions consume exactly the tier the ladder is defending.

---

## 3. How the ladder works

This section builds the mental model in prose first, then gives the statistical arithmetic that justifies each rung, then explains the research each design choice rests on. A doctrine card has no closed-form estimator, so "the math" here is the **power arithmetic** that tells an allocator what the current data tier can and cannot resolve — which is precisely the argument each rung's ask is built from.

### 3.1 The mental model — the ask/reciprocity/justification triple

A rung is a **triple**. It is never just "send us more data." Every rung carries:

1. **The ask** — the specific grant requested (a data type, a format, a cadence).
2. **The reciprocity** — what the manager receives back at the moment of the ask, and it is always something they can *adjust*, not a verdict handed down.
3. **The power justification** — the statistical reason the ask is warranted: a concrete question the *current* tier provably cannot answer, which the requested tier can.

The through-line that makes the ladder coherent is this: **each ask is the answer to a question the current tier cannot resolve.** The allocator is not asking for positions because positions are nice to have; they are asking because a specific analytic *refuses to produce an honest number* without them. That reframes the request from suspicion ("prove you are not lying") to shared curiosity ("neither of us can separate your skill from your style at this sample — let us fix that together"). The statistics do the asking; the allocator is merely the messenger.

### 3.2 Why returns alone cannot resolve skill — the sampling-error intuition

Start from the smallest possible version of the problem. Suppose a manager truly *does* have skill: a genuine positive alpha. Can five years of monthly returns prove it? The obstacle is **sampling error** — the estimate of an average wobbles around the truth, and the size of the wobble shrinks only with the square root of the number of observations.

Concretely, if you estimate a manager's average monthly excess return from `T` months, the standard error of that average is the monthly volatility divided by `√T`. Because the error falls only as `√T`, halving it again needs *four times* the data — and monthly data accrues just one point per month. At 36–60 months you simply do not have many independent draws.

**A worked toy example with small numbers.** Take a genuinely good manager: true annual alpha of **3%** against a tracking error of **6%** — an information ratio (IR) of `3 / 6 = 0.5`, which is real, respectable skill. Over 5 years the standard error of the *estimated* annual alpha is the tracking error divided by `√5`:

```
SE(alpha) ≈ 6% / √5 ≈ 6% / 2.236 ≈ 2.7% per year
```

So the estimate arrives as roughly `3% ± 2.7%` at one standard error, or about `3% ± 5.3%` at two — an interval of roughly **[−2.3%, +8.3%]**. That interval **straddles zero.** After five years of clean monthly data, a truly skilled manager's return record is statistically indistinguishable from a lucky zero-alpha manager. You cannot honestly say "this manager has skill" from returns alone; you can only say "the data are consistent with skill, and also consistent with none."

This is not pessimism, it is arithmetic — and it is exactly why the rung-1 reciprocity is an *uncertainty-honest* tear sheet that states what cannot be concluded rather than pretending to a verdict.

### 3.3 The rung-by-rung power justification

**Rung 1 → 2 (returns → exposures).** Formalize the toy example. The t-statistic on a manager's factor alpha, estimated from `T` months, is approximately:

```
t ≈ IR × √(T / 12)
```

where:

- `t` — the t-statistic on estimated annualized alpha (roughly, estimate ÷ its standard error); values near 2 are the usual bar for "distinguishable from zero."
- `IR` — the manager's true *annualized* information ratio (annual alpha ÷ annual tracking error). `IR = 0.5` denotes a genuinely good manager.
- `T` — the number of monthly return observations.
- `√(T / 12)` — converts the monthly sample into annualized units; the `12` is months per year, and the square-root is the sampling-error scaling from §3.2.

**What it means in words:** even a genuinely good manager produces only a faint statistical signal at this sample length. Plug in `IR = 0.5` and `T = 60`: `t ≈ 0.5 × √5 ≈ 1.0`. A t of about 1.0 corresponds to a **power below roughly 30%** — meaning that if you ran this test on a stream of truly-skilled managers, you would correctly flag skill fewer than one time in three. **Returns alone cannot separate skill from style at 36–60 months.**

The escalation follows directly. A large part of what looks like alpha in a returns series is really *style* — persistent exposure to factors (value, momentum, size, credit) that a returns-only view cannot strip out. Pástor and Stambaugh's estimation insight is the relevant one here: pinning down a manager's factor *betas* with measured exposure data tightens the alpha interval, because variance you were previously attributing to an uncertain mean is reassigned to known loadings. So the rung-2 ask — "send us monthly exposure summaries" — is justified by a question *both sides want answered*: how much of your track record is skill versus style? The exposures shrink the interval that returns alone leaves hopelessly wide.

**Rung 2 → 3 (exposures → positions).** Some skills leave no trace in monthly returns or exposure buckets at all. **Sizing** (does the manager put more weight on their better ideas?) and **exit timing** (do they cut losers and ride winners?) are visible only at the *position* level, and the relevant sample size is not months — it is **trades × breadth** (the *effective N*). Consider the simplest test of sizing/selection skill: is the manager's hit rate genuinely 55% rather than a 50% coin flip? The number of independent trades needed to resolve a 5-percentage-point edge, at 80% power and a two-sided 5% test, is:

```
N ≈ (z_α/2 + z_β)² × p(1 − p) / δ²
  ≈ (1.96 + 0.84)² × 0.25 / 0.05²
  ≈ 7.8 × 0.25 / 0.0025
  ≈ 780 independent trades
```

where:

- `N` — required number of independent trades.
- `z_α/2 = 1.96` — the critical value for a two-sided 5% significance test.
- `z_β = 0.84` — the value giving 80% power.
- `p(1 − p) ≈ 0.25` — the variance of a near-even Bernoulli (hit/miss) outcome.
- `δ = 0.05` — the effect size to be resolved (55% versus 50%).

**What it means in words:** you need on the order of **780 independent trades** before a real 5-point edge becomes statistically visible. A concentrated 30-name book turning over slowly *never clears that bar in five years*; a high-turnover book clears it in one to two. So below the position rung, the sizing and exit analytics **refuse to render rather than fake a number** — and that refusal, not any suspicion, is the honest justification for asking to climb to rung 3.

### 3.4 The research each design choice rests on

The *arithmetic* above says which ask is warranted. The following results say *how* to make the ask so that it deepens the tier instead of collapsing it. Each is stated with what the study showed and why it applies.

- **Falk & Kosfeld (2006), "The Hidden Costs of Control" (*American Economic Review*).** In controlled principal–agent games, agents whose principals imposed monitoring reduced their effort below the freely-chosen level; control signalled distrust and was reciprocated with withdrawal. *Why it applies:* it is the load-bearing reason every ask is framed as help and attached to a shared question — audit framing does not merely offend, it measurably shrinks the grant.
- **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion" (*Management Science*).** People who had abandoned an imperfect forecasting model would use it again if allowed to *modify* it, even trivially — the driver was a desire for control, not for accuracy. *Why it applies:* every reciprocity artifact (the tear sheet, the hygiene pack, the sizing/decay diagnostics) ships as an **adjustable output** — thresholds, priors, sliders the manager tunes — so interpretive control stays with the PM and the artifact is used rather than dismissed. The manager is never handed a verdict.
- **Bonaccio & Dalal (2006), advice-taking review.** Across the advice-taking literature, egocentric discounting — the tendency to underweight others' input — shrinks when information is framed as *advice from an expert source* rather than as a competing opinion. Framing alone raises perceived helpfulness and uptake. *Why it applies:* reciprocity language is deliberately "here is what we can and cannot conclude, for you to weigh," never "here is our finding on you."
- **Goyal & Wahal (2008).** Studying plan-sponsor hiring and firing, they found sponsors hire managers on trailing outperformance and fire on underperformance — yet fired managers subsequently perform about as well as the newly hired replacements, so the churn destroys value. *Why it applies:* the ladder invests in *deepening* a relationship rather than churning it; it is a patience instrument, and the reciprocal analytics are the investment.
- **Open Protocol (OPERA) / AIMA SMA doctrine (Sweep A).** Open Protocol is the SBAI-governed, allocator-neutral **industry-standard risk-exposure template** — three drill-down levels (portfolio stress → asset class → sector), with over $1trn of AUM reported through it. The AIMA "SMA Renaissance" framing treats transparency and risk guidelines as *collaboratively set and contractual*, positioned as relationship-deepening. *Why it applies:* rung 2 asks in OPERA format under an SMA frame precisely because asking in the published industry format lowers the cost of the grant — it is the exact template for the position-light-versus-position-rich reconciliation this program faces.

### 3.5 An optional illustration — interval width versus sample size

The rung-1 argument is entirely about how the signal-to-noise of a skill estimate grows with track length. The following self-contained snippet makes that concrete: it computes the expected t-statistic and an approximate power for a genuinely-skilled manager across a range of track lengths. It is teaching code — paste-and-run, no project imports — and it implements the *same* `t ≈ IR × √(T/12)` relationship as §3.3.

```python
"""Illustrate how a skilled manager's statistical signal grows with track length.

Standalone teaching code: no external estimator, no project imports.
Shows why 36-60 months of returns cannot resolve skill from style.
"""
from math import sqrt
from statistics import NormalDist

NORMAL = NormalDist()  # standard normal, for power via the CDF


def expected_t_stat(annualized_ir: float, months: float) -> float:
    """Expected t-stat on annualized alpha from `months` of returns.

    Mirrors the spec's t ~= IR * sqrt(T / 12): the signal grows with the
    square root of track length, so confidence accrues painfully slowly.
    """
    return annualized_ir * sqrt(months / 12.0)


def approx_power(t_stat: float, two_sided_crit: float = 1.96) -> float:
    """Probability the test flags skill, given the expected t-stat.

    Power = P(observed t exceeds the critical value) when the true mean of
    the t-statistic is `t_stat` and its sampling SD is ~1.
    """
    return 1.0 - NORMAL.cdf(two_sided_crit - t_stat)


if __name__ == "__main__":
    true_ir = 0.5  # a genuinely good manager
    print(f"{'months':>7} {'exp. t':>8} {'power':>8}")
    for months in (24, 36, 60, 120, 240):
        t = expected_t_stat(true_ir, months)
        print(f"{months:>7} {t:>8.2f} {approx_power(t):>8.0%}")

    # At 60 months: exp. t ~= 1.0, power ~= 30% -- returns alone are not enough.
    # Only past ~120-240 months does the same manager become reliably visible,
    # which no live allocation can wait for. Hence the rung-2 exposure ask.
```

Running it shows the expected t-stat crossing 2 (reliable detection) only somewhere past 120–240 months for an `IR = 0.5` manager — a horizon no live allocation can wait for. That gap, at the actual track lengths allocators work with, *is* the rung-2 ask.

### 3.6 Does the doctrine work — validation for a process artifact

*A doctrine card has no statistical power test of its own; validation is qualitative but concrete. The question is whether the doctrine holds up in a real engagement conversation and whether grants survive contact with the analytics.*

**Pilot-conversation checklist (run before and after each escalation ask):**

1. Is a **specific shared question** attached to the ask, stated in the manager's own terms? (No question → do not escalate.)
2. Is the **reciprocity artifact ready to hand back** at the moment of the ask, and is it adjustable?
3. Is the ask worded as help and papered contractually (AIMA SMA framing)?
4. Does the manager **see everything** that will be computed on the granted data?
5. If declined — is the decline **recorded and respected**, with the relationship unchanged?

**Tracked outcome metric — transparency-grant survival and escalation-acceptance rate over time.** The signal that matters is not "did they say yes once" but **"does the grant persist after the analytics ship."** A grant withdrawn once the manager sees the first diagnostic is the failure signal: it means the reciprocity read as audit. Track, per manager, three things: rungs granted, escalation asks accepted versus declined, and grants withdrawn post-analytics. Rising acceptance with zero post-analytics withdrawals means the doctrine is working.

**Explicit anti-Goodhart note.** The ladder is **never quota'd.** There is no target for "managers at rung 3," no scorecard of transparency attained. The moment tier depth becomes a KPI, the incentive flips from cultivating trust to extracting data — which is precisely the Falk–Kosfeld failure the ladder exists to prevent. The metric above is a *health check on the relationship*, not a target to maximize.

---

## 4. Reading the demo

The gallery page (`e1-ladder.html.j2`) renders the ladder as a designed, printable page. Because E1 is doctrine, it carries **no SYNTHETIC DATA badge** (no data is shown) and the go-live box is replaced by a **"How to use this" usage note**. What each element on the page means:

- **The intro line** — states the doctrine's premise ("transparency is granted, not owed") and the promise that every ask is justified by the math, not by suspicion.
- **Each rung block** (Rung 1, Rung 2, Rung 3) — one section per rung, laid out as the §3.1 triple:
  - **"The ask"** — the grant requested at that rung (returns → exposures → positions).
  - **"In return"** — the reciprocity artifact handed back (the tear sheet, the hygiene pack, the sizing/exit diagnostics).
  - **"Why the math asks"** — the one-line power justification distilled from §3.3; this line is the sentence an allocator can say out loud in the meeting.
- **The rung scopes** (e.g. "every manager, default"; "Open Protocol-aligned"; "quarterly lag acceptable") — the cadence and format terms of each grant.
- **The "Standing rules" block** — the four non-negotiables that apply across all rungs: ask only with a stated question, the manager sees everything computed, asks are contractual and reciprocal, a decline is recorded and respected.

**What an allocator should conclude from the page:** the ladder is a *script*, used one rung per conversation. When a manager is at rung 1 and the team wants exposures, the allocator reads the rung-2 "why the math asks" line — returns cannot separate skill from style at this sample — and pairs it with the rung-2 reciprocity. The page is not a policy document to file; it is the thing you bring to the table.

---

## 5. Honest limits & go-live

*For a doctrine card, "go live" is publication and use, not a data pipeline. The gallery page's go-live box is replaced by the "how to use this" usage note. The data contract below describes the grants the ladder negotiates — it is the contract the memo argues for, not a schema the card ingests.*

**The tiered data contract (what each rung's grant consists of):**

| Rung | Ask (grant) | Format | Cadence | Lag tolerance |
| --- | --- | --- | --- | --- |
| **1 — Monthly returns** | Monthly net returns, every manager, default | Net-of-fee monthly return series | Monthly | Timely (current month within reporting cycle) |
| **2 — Exposure summaries** | Monthly factor / sector / gross / net buckets | **Open Protocol** (OPERA) — the industry-standard risk template, three drill-down levels (portfolio stress → asset class → sector), SBAI-governed, >$1trn AUM coverage | Monthly | Short (monthly, one cycle) |
| **3 — Positions** | Position files, ideally with trade dates | Position/holdings file; trade-date stamps where available | Quarterly acceptable | **Quarterly lag acceptable** — the ladder does not demand real-time positions |

**Standing rules on the grant (all rungs):**

- Escalation happens **only with a stated question attached** — never as standing surveillance. A rung-2 ask reads "we cannot separate skill from style at your track length without measured betas," not "send us your exposures."
- The manager **sees every analytic computed on their rung-2+ data.** There is no back-room file.
- Asks are **contractual and reciprocal**, framed in the AIMA SMA doctrine: transparency and risk guidelines set collaboratively, positioned as relationship-deepening.
- A **declined ask is recorded and respected, not punished.** Decline is data about the relationship, never a redemption trigger.

Open Protocol is the deliberate rung-2 standard because it is the published, allocator-neutral template for exactly the position-light-versus-position-rich reconciliation this program faces (Sweep A); asking in the industry format lowers the cost of the grant.

**Reciprocity map (the manager's return at each rung):**

| Rung | What the manager receives back |
| --- | --- |
| 1 | An uncertainty-honest tear sheet **of themselves** — what we can and cannot conclude at their track length (S2). |
| 2 | A peer-relative factor-hygiene pack and drift review, framed as help; the manager sees everything we compute (M1). |
| 3 | The sizing and exit-timing diagnostics platforms give their own PMs — adjustable outputs, interpretive control retained (S3, S4). |

**Power statements that must survive (never weakened):**

- At 36–60 monthly observations, returns support interval statements about Sharpe and factor mix and little else; a true `IR = 0.5` gives an expected `t ≈ 1.0` at `T = 60`, power under ~30%. Returns alone cannot separate skill from style at this sample.
- Hit-rate discrimination (55% vs 50%) needs **~780 independent trades at 80% power**; a concentrated 30-name book never clears in five years, a high-turnover book clears in one to two. Below the position rung, these analytics **refuse to render rather than fake a number.**

**Go-live requirements (publication and use):**

- **Data ask:** none for the artifact itself — it is a playbook. (The rungs *describe* data asks made of managers, but the ladder ships on zero data.)
- **Sample required:** n/a.
- **Build effort:** S (this document + one template + the printable one-pager, produced by the existing print-CSS path — no separate build step).
- **Compliance gate:** the published version must be **generic enough to publish** (no employer process detail, no manager names, no internal thresholds) yet **specific enough to use.** This is the card's only real gate — verified against the standing public-repo policy at publish time.
- **Readiness for use:** the reciprocity artifacts referenced at each rung (S2 at rung 1; M1 at rung 2; S3/S4 at rung 3) must exist at least in demo form, so the reciprocity is not vaporware when the conversation happens.

**Adoption discipline.** This card *is* Sweep E doctrine applied to the transparency negotiation itself, so its packaging follows the rules it preaches: help not audit (every rung leads with the shared question and the reciprocity, never the ask in isolation); in-workflow not a standing dashboard (used *inside* the engagement conversation, not filed in a tab that dies — the BI-adoption failure mode is ~25% dashboard uptake); adjustable reciprocity (every artifact handed back is Dietvorst-adjustable); and a clear who-sees-what (the manager sees every analytic computed on their data at the time it is computed, the internal team sees the grant-survival tracking, and nothing manager-specific enters the public repo).

---

## 6. Deeper reading

**The five core references — what each showed and why it is here:**

1. **Falk & Kosfeld (2006), "The Hidden Costs of Control" (*AER*).** Monitoring that signals distrust lowers agent effort below the freely-chosen level. *The reason audit framing causes transparency withdrawal — every ask must be help-framed.*
2. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion" (*Mgmt Sci*).** People use imperfect models when they can modify them; control beats accuracy as the driver of adoption. *The reason every reciprocity artifact is adjustable.*
3. **Bonaccio & Dalal (2006), advice-taking review.** "Advice from an expert" framing beats "competing opinion" framing on trust and uptake. *The reason reciprocity copy leads with help.*
4. **Goyal & Wahal (2008).** Hire-high/fire-low destroys value; fired managers match new hires. *The reason the ladder favors patient engagement over rotation.*
5. **Open Protocol (OPERA) / AIMA SMA doctrine (Sweep A).** The SBAI-governed industry-standard exposure template plus the collaborative-contractual framing. *The reason rung 2 asks in OPERA format under an SMA frame.*

Supporting the arithmetic: **Pástor & Stambaugh** on how pinning factor betas tightens the alpha interval — the estimation logic behind the rung-1 → rung-2 escalation.

**Questions you should be able to answer after reading this page:**

- **In 60 seconds, why does monitoring framing cause transparency withdrawal?** Falk–Kosfeld: a monitoring signal reads as distrust; the agent reciprocates by withdrawing effort — here, the position and exposure detail the whole program runs on. The tier is the asset; audit framing spends it. Every ask must therefore be help-framed, reciprocal, and attached to a shared question.
- **Recite the rung-2 power justification with the actual numbers.** At 36–60 monthly observations a factor alpha's t-stat is `IR × √(T/12)`; a true `IR = 0.5` gives an expected `t ≈ 1.0` at `T = 60` — power under ~30%. Returns cannot separate skill from style at this N. Measured exposures pin the betas and tighten the alpha interval, so we ask for exposures because the returns-only interval provably cannot answer a question both sides care about.
- **Recite the rung-3 power justification.** Sizing and exit skill live at the position level, where effective N is trades × breadth, not months; discriminating a 55% hit rate from a coin needs ~780 independent trades at 80% power — a bar a concentrated book never clears in five years. Below that rung the analytics refuse to render rather than fake a number.
- **State the anti-Goodhart rule.** The ladder is never quota'd; grant depth is a relationship health check, not a target — the moment it becomes a KPI, the incentive flips back to extraction and the Falk–Kosfeld failure returns.
