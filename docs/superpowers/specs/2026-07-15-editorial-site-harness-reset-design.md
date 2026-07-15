# Quant Allocator Editorial Site and Harness Reset Design

**Date:** 2026-07-15
**Status:** Direction approved by the user; written specification awaiting review
**Scope:** Product authority, agent initialization, stale campaign instructions, and safe parking of the P4 platform work

## 1. Decision

Reset the repository around one product objective: Quant Allocator is a public,
static editorial research publication and project-idea bank. It presents long-form
technical articles with honest synthetic or public exhibits. It is not a production
allocator platform, an enterprise evidence system, or a standing monitoring dashboard.

The later 36-card, bitemporal-platform campaign is superseded as product scope. Its
committed work remains historical research and reusable code, but it does not govern the
website and does not create prerequisites for publication. P4 is parked as optional
follow-on work and removed from the website critical path.

## 2. Product objective

### 2.1 Purpose

The site helps a motivated reader understand quantitative methods for selecting, sizing,
monitoring, engaging with, and redeeming external managers under partial transparency. It
also serves as a structured personal curriculum and a bank of projects that may later earn
deeper implementation.

The public artifact is the product. A deeper engine is built only after explicit user
approval based on learning value, editorial value, or demonstrated demand.

### 2.2 Editorial form

[Aligrithm](https://aligrithm.com/) is the primary reference for publication structure,
reading rhythm, density, article discovery, and long-form composition. Quant Allocator is
not a pixel-level clone. The intended reader experience is:

- a clear publication thesis and a deliberate “Start Here” path;
- research pillars or categories rather than an application workflow;
- a readable article index with concise descriptions and recent or featured work;
- long-form essays that combine intuition, mathematics, code, evidence, and limitations;
- ordinary navigation and progressive disclosure rather than dashboard controls.

The existing Interval system remains the quantitative semantic layer. Its restrained
palette, interval displays, provenance labels, and explicit refusal states distinguish
what the evidence supports. Aligrithm governs editorial composition; Interval governs the
meaning and honesty of quantitative elements.

### 2.3 Article contract

Each research idea has two connected surfaces:

1. An editorial article containing what the method is, why it matters, why naive methods
   fail, a conceptual walkthrough, a worked numerical example, defined notation,
   self-contained teaching code, honest limits, go-live requirements, references, and
   questions the reader should be able to answer.
2. A compact exhibit using synthetic or public data, with “What this exhibit shows” and
   “How to read it” guidance linked to the full method article.

Static narration is the default. Interaction is allowed only when changing a state is
part of the teaching argument. JavaScript may select committed states or map committed
values to pixels; it must not recompute estimators.

### 2.4 Correctness boundary

The publication keeps the following strict rules:

- all displayed data is synthetic or public and every displayed manager or fund name is
  fictional;
- no employer identity or employer-internal fact appears in tracked artifacts;
- every displayed quantitative claim is supported by the committed article/exhibit data;
- estimates use an interval, scenario, or explicit refusal rather than an unsupported
  bare point;
- load-bearing arithmetic receives an independent check before publication;
- rendered desktop/mobile layout, formulas, copy, links, and visible controls are checked;
- publication terms are loaded from the gitignored canary file and reviewed before push;
- pushing or publishing always requires explicit user approval.

These are page- and claim-level publication gates. They do not require every article to
share one global evidence database, receipt graph, or production calculation engine.

### 2.5 Non-goals

- Completing 36 cards before improving or publishing the site.
- A production bitemporal evidence platform as a website prerequisite.
- A global reconstruction-receipt system for synthetic teaching exhibits.
- Standing operational dashboards, alerts, or workflow software.
- Building live integrations merely because a method article describes how they could
  work.
- Reopening independently certified numbers when an editorial-only change does not touch
  them.

## 3. Authority model

Fresh agents use this precedence order:

1. The user’s direct instruction in the current task.
2. `docs/PRODUCT.md`, the canonical product charter.
3. `.harness/current.yaml`, the compact current objective and scheduler state.
4. Approved product and design specifications explicitly cited by the current task.
5. The single implementation plan named by `.harness/current.yaml`, if one exists.
6. Git history, completed plans, progress ledgers, handoffs, and review reports as
   historical evidence only.

A lower authority may add implementation detail but may not broaden a higher authority.
No implementation plan may add cards, engines, platform layers, or publication
prerequisites beyond `docs/PRODUCT.md` without a new explicit user decision and a product
charter amendment.

Method-spec rulings continue to govern the arithmetic and claims of their own article.
They do not govern the overall product roadmap.

## 4. Minimal harness

The reset uses a small repository-backed harness instead of merging the earlier campaign
control-plane branch wholesale.

### 4.1 Tracked initialization surface

- `docs/PRODUCT.md` — durable product objective, boundaries, content contract, and scope
  change rule.
- `AGENTS.md` — short routing and execution guide; points to the product charter and
  current state.
- `.harness/README.md` — explains the initialization sequence and what is historical.
- `.harness/current.yaml` — current objective, active task, active plan, next action,
  parked work, verification level, and outward-action authority.
- `tests/harness/test_current_context.py` — checks that the compact context is internally
  consistent, the named active plan exists when non-null, P4 is parked, and the
  superseded roadmap cannot become active accidentally.

No model pinning, agent-role configuration, telemetry framework, generated packets, or
large task database is required for this reset. Responsibility-based delegation remains
in `AGENTS.md`.

### 4.2 Local historical surface

`.superpowers/sdd/progress.md` remains an append-only historical ledger. It is not normal
initialization material. The local continuation prompt becomes a short pointer to the
tracked charter and current state. Historical P4 reports remain untouched, while both P4
handoffs receive a prominent parked banner that forbids automatic resumption.

## 5. Document disposition

| Document family | Disposition |
| --- | --- |
| `README.md` | Align the public description with the editorial publication and idea-bank objective. |
| Ratified convergence decision | Retain as the origin of demo-first and earn-a-build doctrine. |
| Demo-layer and gallery designs | Retain quantitative semantics; `docs/PRODUCT.md` resolves later editorial-structure conflicts. |
| House editorial brief | Retain as the article-writing contract. |
| External-manager 36-card roadmap | Add a superseded banner and point to `docs/PRODUCT.md`. Preserve its body as history. |
| P4 implementation and shared-fixture plans | Add parked banners. They are optional research work, not website prerequisites. |
| Other completed plans and review reports | Preserve unchanged as history. They become executable only if the current harness cites them. |
| Local continuation prompt and global constraints | Replace stale campaign/model/dependency instructions with compact current guidance. |
| P4 continuation handoffs | Preserve technical checkpoint details under a parked/no-auto-resume banner. |

## 6. P4 parking contract

Parking preserves resumability without making P4 current work:

- fixture branch `codex/roadmap-p4-terms-fixture-impl` remains at `b0596db`;
- card branch `codex/roadmap-p4-impl` remains at `7c2964f`;
- both worktrees remain untouched and clean;
- no merge, branch deletion, reset, rebase, push, publication, or fixture correction is
  authorized by this reset;
- the P4 handoff remains the technical recovery record;
- resumption requires a new explicit user instruction and a fresh product-fit decision;
- P4 is never selected as the current or next website task automatically.

## 7. Current website baseline

At the reset point, `site/cards.yaml` contains 23 live cards and the site build contract
expects 47 HTML outputs: one index, 23 exhibits, and 23 method pages. P4 is not a manifest
entry and does not block any existing page.

The current index already has complete static links, responsive behavior, search, and
no-JavaScript coverage. Its decision-journey controls are application-like and will be
assessed in the next website-specific design task. This reset changes authority and
continuation state; it does not redesign the website itself.

## 8. Verification

The documentation reset is accepted when:

1. `tests/harness/test_current_context.py` passes.
2. The YAML state parses and names exactly one current objective and next action.
3. The active-plan field is null after the reset; the next task is a website-design task,
   not P4 or platform continuation.
4. The roadmap and P4 banners link to the canonical product charter.
5. A repository search finds no remaining document that both claims to be active and
   requires the 36-card platform campaign.
6. The existing focused site build tests still pass and the static site builds without
   changing committed data.
7. The scoped publication scan reports no new tracked match.
8. Git status contains only the intended tracked reset files; local ignored-harness edits
   are itemized separately.
9. No push or publication occurs.

## 9. Next task after the reset

The next task is to write and review a website-first design specification grounded in a
captured Aligrithm reference and the current rendered site. That specification will decide
the publication homepage, reading path, research pillars, article index, and minimal
changes to existing exhibit pages. It will separate visual/editorial QA from per-page
numerical certification and keep platform work parked.
