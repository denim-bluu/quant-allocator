# E1 · Trust-Preserving Transparency Ladder — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [E1 · Trust-preserving transparency ladder](../2026-07-05-idea-cards.md#e1--trust-preserving-transparency-ladder--quick-win-memo)
**Type:** Process / doctrine card (zero code; effort S). Sections 2, 4, and 5 are adapted for a doctrine artifact — see the note under each.

---

## 1. Problem & decision hook

Transparency is the binding input to every analytic in this portfolio, and it is *granted, not owed*. A manager can decline to share exposure summaries or position files; nothing in the mandate compels it. That makes the transparency tier a resource to be cultivated, not assumed — and the way an allocator asks for data determines whether the tier deepens or collapses.

Falk–Kosfeld (2006) is the load-bearing result: when a principal signals distrust through monitoring, the agent *withdraws* effort. Transposed to allocation, an analytics program that reads as audit invites the manager to withdraw the very position and exposure detail the program runs on. So the failure mode is not "the manager is annoyed" — it is "the data tier every other card depends on shrinks, and the cards go dark."

**Decision improved:** ENGAGE (primary) — this is the team's negotiation playbook for escalating data asks. Secondarily it protects MONITOR and SELECT by defending the tier those decisions consume. The E-brief's framing is explicit: *protecting the tier is itself a design goal*, not a side effect.

**The artifact:** a three-rung ladder. Each rung is a triple — the **ask** (what data), the **reciprocity** (what the manager receives back), and the **power justification** (why the ask is warranted by the statistics, not by suspicion). The ladder is the document a senior allocator would forward to a peer.

---

## 2. Data contract per tier

*Adapted: for a doctrine card the "data contract" is the definition of each rung's grant — what it consists of, its format, cadence, and lag tolerance. This is the contract the ladder negotiates, not a pipeline schema.*

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

Open Protocol is the deliberate rung-2 standard because it is the published, allocator-neutral template for exactly the position-light-vs-position-rich reconciliation this program faces (Sweep A); asking in the industry format lowers the cost of the grant.

---

## 3. Methodology

*The methodology of a doctrine card is its evidence base — why each design choice is the one the adoption and trust literature supports, and the statistical arithmetic behind each rung's power justification.*

**Why the ladder exists at all — the trust mechanism.**
- **Falk–Kosfeld (2006), "Hidden Costs of Control" (*AER*).** Monitoring that signals distrust lowers agent effort. Design consequence: every ask is framed as help and justified by a shared question, never as verification. Audit framing destroys the asset (the tier).
- **AIMA, "The SMA Renaissance."** The healthy version of transparency: collaborative, contractual, relationship-deepening. This is the framing template for how an ask is worded and papered.

**Why reciprocity artifacts are modifiable.**
- **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion" (*Mgmt Sci*).** People will use an imperfect model if they can *modify* it, even trivially — the driver is a desire for control, not accuracy. Design consequence: every reciprocity artifact (the tear sheet, the hygiene pack, the sizing/decay diagnostics) ships as an **adjustable output** the manager tunes — thresholds, priors, sliders — keeping interpretive control with the PM. The manager is never handed a verdict.

**Why the framing is "help," measurably.**
- **Bonaccio & Dalal (2006), advice-taking review.** Egocentric discounting shrinks when information is framed as *advice* from an expert source rather than a competing opinion — framing alone raises perceived helpfulness, trust, and uptake. Design consequence: reciprocity language is "here is what we can and cannot conclude, for you to weigh," not "here is our finding on you."

**Why patience-plus-engagement, not rotation.**
- **Goyal–Wahal (2008).** Sponsors hire on trailing outperformance and fire on underperformance; fired managers subsequently match new hires. Design consequence: the ladder invests in deepening a relationship (engagement, reciprocal analytics) rather than churning it — the ladder is a patience instrument.

**The power justification behind each rung (Sweep C arithmetic).** The ask is warranted by what the current tier *cannot* answer:

- **Rung 1 → 2.** At 36–60 monthly observations, returns support interval statements about Sharpe and factor mix and little else. The t-stat of a factor alpha is `t ≈ IR × √(T/12)`: a genuinely good manager with true annualized IR 0.5 produces an expected **t ≈ 1.0 at T = 60** — power below ~30%. Returns alone cannot separate skill from style at this sample. *Measured exposures pin the betas, which tightens the alpha interval* (Pástor–Stambaugh logic) — a question both sides want answered. That is the rung-2 ask, justified by the math.
- **Rung 2 → 3.** Sizing and exit skill are only measurable at position level; effective N is trades × breadth, not months. Hit-rate discrimination (55% vs 50%) needs **~780 independent trades at 80% power** — a concentrated 30-name book never clears in five years, a high-turnover book clears in one to two. Below the position rung, these analytics *refuse to render rather than fake a number.* That refusal is the honest justification for asking to climb.

The through-line: **each ask is the answer to a question the current tier provably cannot resolve** — the ladder converts a statistical limit into a collaborative reason to escalate.

---

## 4. Power & validation plan

*Adapted: there is no statistical power test — this is a process artifact. Validation is qualitative but concrete: does the doctrine hold up in a real engagement conversation, and do grants survive contact with the analytics?*

**Pilot-conversation checklist (run before and after each escalation ask):**

1. Is a **specific shared question** attached to the ask, stated in the manager's own terms? (No question → do not escalate.)
2. Is the **reciprocity artifact ready to hand back** at the moment of the ask, and is it adjustable?
3. Is the ask worded as help and papered contractually (AIMA SMA framing)?
4. Does the manager **see everything** that will be computed on the granted data?
5. If declined — is the decline **recorded and respected**, with the relationship unchanged?

**Tracked outcome metric — transparency-grant survival and escalation-acceptance rate over time.** The signal that matters is not "did they say yes once" but **"does the grant persist after the analytics ship."** A grant withdrawn after the manager sees the first diagnostic is the failure signal — it means the reciprocity read as audit. Track, per manager: rungs granted, escalation asks accepted vs. declined, and grants withdrawn post-analytics. Rising acceptance and zero post-analytics withdrawals = the doctrine is working.

**Explicit anti-Goodhart note.** The ladder is **never quota'd.** There is no target for "managers at rung 3," no scorecard of transparency attained. The moment tier depth becomes a KPI, the incentive flips from cultivating trust to extracting data, which is precisely the Falk–Kosfeld failure the ladder exists to prevent. The metric above is a *health check on the relationship*, not a target to maximize.

---

## 5. Implementation architecture

*Adapted: this card ships no code. Effort S.*

The only artifacts are:

1. **The gallery doctrine page** — `site/templates/pages/e1-ladder.html.j2`, sourced from this document, rendering the three-rung ladder as a designed page (per rung: ask / reciprocity / power justification). `doctrine: true` in `cards.yaml` suppresses the SYNTHETIC badge (no data is shown); print CSS applies; the go-live box is replaced by a "how to use this" note. See wave-1 gallery design §5 "E1 · Transparency ladder (doctrine page)."
2. **A printable one-pager** — the same ladder as a single A4 sheet a senior allocator forwards, produced by the existing print CSS path; no separate build step.

No modules, adapters, dependencies, simulator cells, or generators. The card's entire footprint is this markdown source and the template that renders it.

---

## 6. Adoption & packaging

This card *is* Sweep E doctrine applied to the transparency negotiation itself — so its packaging follows the same rules it preaches:

- **Help, not audit** — every rung's copy leads with the shared question and the reciprocity, never the ask in isolation. The manager reads a reason to collaborate, not a demand.
- **In-workflow, not a standing dashboard** — the ladder is used *inside* the engagement conversation, at the decision moment (a quarterly review, an escalation discussion), not filed as a policy document that dies in a separate tab (the BI-adoption failure mode, ~25% dashboard adoption).
- **Adjustable reciprocity** — the artifacts handed back (the S2 tear sheet, the M1 hygiene pack, the S3/S4 sizing and exit diagnostics) are all Dietvorst-adjustable; the manager keeps interpretive control.
- **Who sees what, when:** the manager sees every analytic computed on rung-2+ data, at the time it is computed. The internal team sees the grant-survival tracking. Nothing manager-specific enters the public repo — the published version is generic doctrine.

**Reciprocity map (the manager's return at each rung):**

| Rung | What the manager receives back |
| --- | --- |
| 1 | An uncertainty-honest tear sheet **of themselves** — what we can and cannot conclude at their track length (S2). |
| 2 | A peer-relative factor-hygiene pack and drift review, framed as help; the manager sees everything we compute (M1). |
| 3 | The sizing and exit-timing diagnostics platforms give their own PMs — adjustable outputs, interpretive control retained (S3, S4). |

---

## 7. Go-live requirements

For a **doctrine card, "go live" is publication and use**, not a data pipeline. The gallery page's go-live box is replaced by a "how to use this" note (§5). Requirements:

- **Data ask:** none for the artifact itself — it is a playbook. (The rungs *describe* data asks made of managers, but the ladder ships on zero data.)
- **Sample required:** n/a.
- **Build effort:** S (this document + one template + the one-pager).
- **Compliance gate:** the published version must be **generic enough to publish** (no employer process detail, no manager names, no internal thresholds) yet **specific enough to use.** This is the card's only real gate — verified against the standing public-repo policy at publish time.
- **Readiness for use:** the reciprocity artifacts referenced at each rung (S2 at rung 1; M1 at rung 2; S3/S4 at rung 3) exist at least in demo form, so the reciprocity is not vaporware when the conversation happens.

---

## 8. Learning notes

*The spec program doubles as a curriculum. For a doctrine card, own the five core references and be able to defend the trust mechanism and the arithmetic unaided.*

**The five core references (one-line takeaways):**

1. **Falk & Kosfeld (2006), "The Hidden Costs of Control" (*AER*).** Monitoring that signals distrust lowers agent effort — the reason audit framing causes transparency withdrawal.
2. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion" (*Mgmt Sci*).** People use imperfect models when they can modify them; control > accuracy — the reason every reciprocity artifact is adjustable.
3. **Bonaccio & Dalal (2006), advice-taking review.** "Advice" framing beats "opinion" framing on trust and uptake — the reason copy leads with help.
4. **Goyal & Wahal (2008).** Hire-high/fire-low destroys value; fired managers match new hires — the reason the ladder favors patient engagement over rotation.
5. **Open Protocol / AIMA SMA doctrine (Sweep A).** The industry-standard exposure template and the collaborative-contractual framing — the reason rung 2 asks in OPERA format under an SMA frame.

**Defend unaided:**

- **In 60 seconds, why monitoring framing causes transparency withdrawal.** Falk–Kosfeld: a monitoring signal reads as distrust; the agent reciprocates by withdrawing effort — here, by withdrawing the position and exposure detail the whole program runs on. The tier is the asset; audit framing spends it. Every ask must therefore be help-framed, reciprocal, and attached to a shared question.
- **Recite the rung-2 power justification with the actual numbers.** At 36–60 monthly observations, a factor alpha's t-stat is `IR × √(T/12)`; a true IR of 0.5 gives an expected **t ≈ 1.0 at T = 60** — power under ~30%. Returns cannot separate skill from style at this N. Measured exposures pin the betas and tighten the alpha interval — so we ask for exposures because the returns-only interval provably cannot answer a question both sides care about.
- **State the anti-Goodhart rule.** The ladder is never quota'd; grant depth is a relationship health check, not a target — because the moment it becomes a KPI, the incentive flips back to extraction and the Falk–Kosfeld failure returns.
