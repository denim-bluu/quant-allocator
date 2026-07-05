# Demo Layer — Design Doctrine & Visual System

**Date:** 2026-07-05
**Status:** Approved (direction chosen from rendered mockups)
**Decision:** Direction C — **"Interval"** — is the house design system. A dark
scheme derived from Direction B ("Desk Terminal") is the playground default
and optional pack view. Direction A ("Research Desk") survives only as print
manners in the pack print stylesheet.

## 1. Architecture (locked)

- **Python owns the numbers; a static layer owns the pixels.** The simulator
  and analytics emit JSON; presentation is hand-controlled HTML/CSS with thin
  vanilla JS. No app framework, no server.
- **Interactive demos precompute.** The transparency playground ships a
  precomputed scenario grid as JSON; dials snap to grid points.
- **Hosting:** public GitHub Pages (synthetic/public data only — standing repo
  policy).
- **Packs are HTML-first with print CSS**: browser print-to-PDF must produce a
  clean paginated A4 pack (page-break rules, interactivity degrades to static).
- **One small app maximum** until a flagship earns a second.

## 2. Demo doctrine (fifth rubric input at convergence)

Every idea card's wow-demo must satisfy:

1. **Narrated artifact first** — a static pack renderable from synthetic/public
   data in one command; portable and email-able.
2. **Interactive only where interaction is the argument** (the playground
   qualifies; a tear-sheet does not).
3. **Adjustable outputs** wherever a manager-facing version exists — the
   algorithm-aversion fix (Dietvorst 2018, Sweep E): outputs are inputs to
   judgment, never verdicts.
4. **Help-not-audit framing** in all copy (Sweep E trust doctrine).

## 3. The Interval identity

**Thesis: the methodology is the brand.** One accent color, spent exclusively
on *what the data can support* — credible bands, power scores, measured (not
inferred) quantities. No statistic ever renders as a bare point estimate.
Analytics below their power threshold refuse to render. This is the visual
expression of the Sweep C robust/shrink/noise taxonomy.

### Tokens — light (default)

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#FBFBF9` | page/card ground (warm grey, chosen not inherited) |
| `--ink` | `#1F2428` | primary text |
| `--dim` | `#5C6470` | secondary text, labels |
| `--line` | `#E4E3DD` | hairline borders (1px, no shadows) |
| `--track` | `#EEEDE7` | slider tracks, interval rails |
| `--accent` | `#10685E` | **supportable claims only**: bands, power, measured values, interactive controls |
| `--band` | `rgba(16,104,94,0.16)` | credible/confidence band fills |
| `--pos` | `#3D7A4E` | semantic positive (muted; never the accent) |
| `--neg` | `#B04A3E` | semantic negative (muted) |
| `--warn` | `#99621D` | hygiene-band breaches, shrink verdicts |

### Tokens — dark (Terminal-derived; playground default)

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#13161B` | ground (blue-black) |
| `--ink` | `#D5DCE4` | primary text |
| `--dim` | `#828D9B` | secondary |
| `--line` | `#272E38` | hairlines |
| `--accent` | `#4FB3A5` | supportable claims (teal, lightened for dark ground) |
| `--data` | `#E8A33D` | numeric emphasis in dense tables (Terminal convention) |
| `--pos` / `--neg` | `#55B97C` / `#E05252` | P&L sign, finance convention |

### Typography & form

- System sans (`system-ui`) with tight heading tracking (−0.015em);
  **`font-variant-numeric: tabular-nums` mandatory wherever digits align**.
  Mono numerals acceptable in the dark/dense contexts. Production face
  upgrade (e.g., Neue Haas Grotesk) is a later, optional decision.
- Cards: 8px radius, 1px `--line` borders, no drop shadows.
- Labels: 9.5–10.5px uppercase, +0.10em letter-spacing.
- Charts: inline SVG emitted from Python; band fills + faint zero gridline +
  emphasized endpoint. No charting library.

## 4. Signature components (codify with first consumer)

| Component | Rule it enforces |
| --- | --- |
| **`IntervalStat`** | Every statistic = point + interval rail + range text. Bare point estimates are a lint error of the design system. |
| **`PowerGate`** | An analytic below its pre-computed power threshold renders a dashed empty-state naming the threshold and the unlock date — never a number. |
| **`TierBadge`** | Every view carries its data-provenance tier (R / E / P) so no claim floats free of what could be known. |
| **`VerdictChip`** | robust / shrink ("partially visible") / noise ("can't call it") — Sweep C's taxonomy in copy calibrated to help, not accuse. |

## 5. Deferred (YAGNI until Session 4 / first flagship)

`design-tokens.css` and component templates are born with their first consumer
(the playground + winning flagship's pack) — a tokens file with no renderer
invites drift. The mockup source of record is the approved artifact page
("initial-three-directions"); this document is the binding spec.
