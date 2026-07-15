# Quant Allocator Product Charter

**Status:** Canonical product authority

**Last approved:** 2026-07-15

## Objective

Quant Allocator is a public, static editorial research publication and project-idea bank
about quantitative methods for allocator decisions under partial transparency.
The public artifact is the product: long-form technical articles paired with honest
synthetic or public exhibits.

It is not a production allocator platform, enterprise evidence system, or standing
monitoring dashboard. Deep engineering follows explicit approval; it never becomes a
prerequisite merely because an implementation plan describes it.

## Reader and decisions

Write for a motivated reader who wants to understand how a quantitative allocator
could select, size, monitor, engage with, and redeem external managers. The site must
work both as a structured curriculum and as a project-idea bank.

## Editorial form

Aligrithm is the primary reference for publication structure, reading rhythm,
research pillars, article discovery, and long-form composition. This is not a
pixel-level clone. Quant Allocator uses a clear thesis, a Start Here path, topical
pillars, a readable article index, and long-form pieces combining intuition,
mathematics, code, evidence, and limitations.

`docs/EDITORIAL_SYSTEM.md` is the binding reader-facing specification for page order,
curriculum, progressive disclosure, navigation, and responsive presentation.

Interval remains the quantitative semantic system. Intervals, provenance labels,
and refusal states communicate what the evidence supports. Aligrithm governs
editorial composition; Interval governs quantitative meaning.

## Article and exhibit contract

Every idea has a long-form article and, where useful, a compact exhibit. Articles
explain what the method is, why it matters, why naive alternatives fail, how it
works, a small numerical example, defined notation, self-contained teaching code,
honest limits, go-live requirements, references, and questions the reader should
be able to answer.

Exhibits use synthetic or public data and explain “What this exhibit shows” and
“How to read it.” Static narration is the default. Interaction is used only when
changing state is part of the teaching argument.

## Publication correctness

- Use public or synthetic data only and fictional displayed names.
- Never include an employer identity or employer-internal fact.
- Support every displayed quantitative claim with committed article/exhibit data.
- Use an interval, scenario, or explicit refusal for estimate-bearing outputs.
- Independently check load-bearing arithmetic before publication.
- Check rendered desktop/mobile layout, formulas, copy, links, and visible controls.
- Load publication terms from the gitignored canary file before every push.
- Push or publish only with explicit user approval.

These are page- and claim-level gates. They do not require a shared production
database, global receipt graph, or hardened engine for every article.

## Scope boundaries

The 36-card bitemporal-platform roadmap is superseded product scope. P4 and its
fixture work are parked optional research and are not website prerequisites. Existing
committed work remains available for later reuse.

Plans may add articles, exhibits, and supporting code within an approved website task.
New cards or deeper engines require explicit user approval unless that approved task
already names them. A charter amendment is required only when changing the product
objective, the platform boundary, or publication prerequisites.

## Authority

1. Direct user instruction.
2. This product charter.
3. `.harness/current.yaml`.
4. Approved specifications cited by the current task.
5. The single active plan named by the current harness, if any.
6. Historical plans, ledgers, handoffs, reports, and Git history as evidence only.

A lower authority may add implementation detail but may not broaden a higher one.
