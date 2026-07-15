# Editorial Website Design QA

**Status:** Passed

**Date:** 2026-07-15

**Scope:** Publication homepage, global shell, long-form article, numerical exhibit,
responsive behavior, and the primary discovery interactions. Numerical fixture review
remains a separate gate; this record covers the website as rendered.

## Visual sources

- Reference site captured before implementation: Aligrithm homepage, desktop and mobile.
- Selected direction: Editorial Field Guide desktop concept
  `exec-3a9fd3fd-dd0d-48f5-9015-ec8368ec6cfe.png`.
- Responsive concept: `exec-48ec8b92-93d3-4354-839c-328c25eea063.png`.
- Article/exhibit concept: `exec-43efcd4b-3822-4cd0-8cc7-7e4de6135609.png`.
- Final implementation captures:
  - `/private/tmp/quant-allocator-after-desktop-final-2.png`
  - `/private/tmp/quant-allocator-after-mobile-final-3.png`
  - `/private/tmp/quant-allocator-article-s1-final-2.png`
  - `/private/tmp/quant-allocator-exhibit-s1-final-2.png`
  - `/private/tmp/quant-allocator-exhibit-s1-ledger.png`
  - `/private/tmp/quant-allocator-x2-mobile.png`

The desktop, mobile, and article source concepts were each inspected beside their
implementation capture in one comparison view. The final screenshots are session-local
QA evidence and are intentionally not publication assets.

## Comparison result

### 1. Information hierarchy

Passed. The masthead, thesis, Start Here path, five research pillars, selected research,
browser, and full 23-idea index follow the selected concept's publication-first order.
The evidence browser no longer reads as the product's first screen.

### 2. Visual system

Passed. Warm paper, ink, muted teal, rust links, serif reading type, sans-serif labels,
hairline dividers, and restrained control geometry match the approved direction. The
desktop thesis renders at 64px and the 390px thesis at 46.8px, inside the approved range.

### 3. Responsive shape

Passed at the in-app browser's native 1280x900 desktop cap and at 390x844 mobile. Both
render with zero horizontal overflow. At 390px the masthead uses the compact menu, the
homepage becomes one reading column, controls retain 44px targets, and exhibit dials and
intervals remain usable. The design is fluid above 1280px with a 1320px content cap; the
browser surface did not expose a native 1440px canvas in this session.

### 4. Article and exhibit continuity

Passed. Articles now open with an editorial title, deck, decision, maturity, and minimum-
evidence band before the full method spec. Prose is held to 760px. Every tested article
links to its paired exhibit and the exhibit links back. The S1 article rendered 119 KaTeX
nodes with `data-math-render-status="ok"` and no KaTeX errors. Its paired exhibit retained
the committed data node, tier badges, synthetic badge, decision context, 40 interval
components, and working rank-order control.

### 5. Interaction and runtime integrity

Passed in the in-app browser:

- Journey to Catalog changed the view and URL.
- Search for `provenance` reported 4 of 23 ideas; browser back and forward restored state.
- The returns-only preset reported 11 of 23 ideas.
- The public-equity facet reported 5 of 23 ideas.
- Dark theme survived a reload and was returned to light for handoff.
- The mobile menu exposed four primary links and closed cleanly.
- The S1 rank control changed from OLS to posterior order while preserving interval geometry.
- The X2 transparency tier changed to P and updated all four precomputed analytic outputs.
- Homepage, S1 article, S1 exhibit, and X2 rendered with zero horizontal overflow and no
  browser warnings or errors.

## Fix history

1. A stale browser cache initially showed the pre-redesign CSS. Shared publication assets
   now carry `editorial-v4`, with a regression test covering all five shared assets.
2. The first desktop thesis exceeded the approved type range and pushed the publication
   structure below the fold. It was reduced to a 48-72px fluid range.
3. The first mobile thesis was constrained to 10 characters and wrapped into six lines.
   It now uses the full reading width and a 42.4-54.4px range.
4. Long-form pages initially looked like raw method-spec output. A tested article intro and
   evidence band now establish the editorial hierarchy while preserving the full spec.
5. The final review caught a pre-content exhibit-to-article link that bypassed M1's
   decision-adjacent synthetic boundary. The shared exhibit header now keeps the boundary
   intact; the tested article link remains after the exhibit's explanatory content.
6. The final review also caught that the complete Research index still opened exhibits.
   Start Here and all 23 index entries now open long-form articles directly; the five
   Selected Research entries intentionally remain exhibit links.

## Intentional differences from the concepts

- The exact synthetic/public and fictional-manager disclosure stays directly below the
  masthead on every page. The concept placed it at the bottom, but the product contract
  requires it to remain visible.
- The implementation shows real maturity labels and evidence requirements rather than
  invented reading times or dates.
- The complete 23-idea index and its advanced evidence filters remain available below the
  editorial entry points; the concept only showed a compact sample.
- The 390px implementation is a true single column. The generated responsive concept's
  lower two-column region was treated as art direction, not a literal narrow-screen rule.
- The article keeps the complete governed method spec instead of replacing it with a short
  mock article or newly invented side rails.

No material P0, P1, or P2 visual mismatch remains.
