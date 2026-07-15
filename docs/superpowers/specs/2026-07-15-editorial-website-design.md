# Quant Allocator Editorial Website Design

**Status:** Approved for implementation by the user's 2026-07-15 end-to-end directive

**Product authority:** `docs/PRODUCT.md`

**Reference:** Aligrithm supplies editorial hierarchy and reading rhythm, not brand,
assets, claims, or pixel geometry. Interval remains the quantitative semantic system.

## Outcome

Turn the existing 23-idea static gallery into a publication-first website for readers
learning how quantitative allocators select, size, monitor, engage with, and redeem
external managers under partial transparency.

The website must work in this order:

1. State a clear editorial thesis.
2. Give a short Start Here path.
3. Organize the corpus into five plain-language research pillars.
4. Present a readable article index.
5. Keep the existing evidence search and filters as a secondary discovery tool.
6. Carry the same publication voice into long-form articles and exhibits.

It is not a platform dashboard, subscription product, or production allocator engine.

## Selected visual direction

**Direction:** Editorial Field Guide

**Accepted desktop concept:** session-local generated concept
`exec-3a9fd3fd-dd0d-48f5-9015-ec8368ec6cfe.png` (not committed)

**Responsive concept:** session-local generated concept
`exec-48ec8b92-93d3-4354-839c-328c25eea063.png` (not committed)

**Article/exhibit concept:** session-local generated concept
`exec-43efcd4b-3822-4cd0-8cc7-7e4de6135609.png` (not committed)

The direction was selected over the denser Research Ledger and sidebar-heavy Reading
Room. It has the clearest publication hierarchy, the least dashboard residue, the
smallest implementation surface, and the strongest responsive path.

## Creative idea

The site reads like a field guide whose central rule is:

> Evidence should change what you are allowed to say.

Warm paper, dark ink, a muted teal evidence color, and a restrained rust link color
make the publication feel serious without becoming institutional. Serif typography
carries articles; compact sans-serif typography carries navigation, labels, and
evidence metadata.

No production image assets are required. The subject is reasoning, notation, and
evidence; typography and existing Interval exhibits are the visual material.

## Information architecture

### Global shell

- Wordmark: `QUANT ALLOCATOR`
- Primary navigation: `Start here`, `Research`, `Exhibits`, `Browse`
- Theme control remains functional and persists locally.
- The exact synthetic/public and fictional-manager disclosure remains visible on every
  page.
- Footer retains `MIT License` and `Source repository`.
- Mobile uses a compact native disclosure/menu pattern with 44px targets.

### Homepage

1. Thesis and one-sentence product description.
2. Start Here path:
   - Uncertainty-honest tear-sheet engine
   - Tier & Power Atlas
   - Transparency playground
3. Five research pillars, derived from existing manifest lanes:
   - Signal & skill — 7
   - Monitoring — 6
   - Portfolio decisions — 3
   - Evidence & engagement — 4
   - Cross-cutting foundations — 3
4. Selected research entries that demonstrate the breadth of the corpus.
5. Browse all 23 ideas: Journey/Catalog, search, presets, and evidence filters.
6. Complete article index; every existing idea remains directly linked without
   JavaScript.

### Article and exhibit pages

- Long-form specs inherit the publication masthead, paper, reading typography, and
  bounded line length.
- Article pages add a breadcrumb, evidence metadata, and a direct reciprocal link to
  the paired exhibit.
- Exhibit pages retain their tested data nodes, Interval components, decision context,
  methodology, go-live/refusal furniture, and link back to the full article.
- Existing per-card numerical templates and JavaScript remain unchanged unless a
  rendered defect requires a narrowly tested repair.

## Visible-copy lock

Above the homepage fold, the allowed visible copy is:

- `QUANT ALLOCATOR`
- `Start here`
- `Research`
- `Exhibits`
- `Browse`
- `Theme`
- `Evidence should change what you are allowed to say.`
- `Quantitative methods for allocator decisions under partial transparency.`
- the exact site-wide disclosure

No hero eyebrow, fake date, fake metric, subscription prompt, newsletter, employer
identity, or platform claim may be added.

## Design system

### Color

- Paper: warm off-white close to `#f7f4ee`
- Ink: near-black close to `#1d211f`
- Muted text: cool grey-brown close to `#626662`
- Evidence accent: deep muted teal close to `#0f5f59`
- Editorial link: restrained rust close to `#9a3d25`
- Lines: low-contrast neutral close to `#d9d4ca`
- Dark theme preserves semantic contrast and does not change evidence meaning.

### Typography

- Reading: `Iowan Old Style`, `Charter`, `Source Serif 4`, `Georgia`, serif.
- Interface: system sans-serif stack.
- Homepage thesis: fluid, approximately 48–72px desktop and 42–54px mobile.
- Article body: 18–19px, 1.65–1.75 line height, 65–75 characters per line.
- Labels: 12–13px uppercase with restrained tracking; never below 12px.

### Geometry

- Desktop content width: approximately 1320px for the homepage and 760px for article
  prose.
- Hairline dividers instead of card walls.
- Square or lightly rounded controls; no giant rounded wrappers.
- Existing Interval cards keep their 8px radius and semantic rails.
- Motion is limited to hover/focus feedback and respects reduced-motion preferences.

## Responsive behavior

- No horizontal overflow at 390px.
- Header, thesis, Start Here, pillars, selected research, browser, and article index
  become a single reading column.
- Pillar counts stay adjacent to their labels; summaries wrap naturally.
- Filter controls stack and remain at least 44px high.
- Article side rails move into flow before or after the prose.
- Tables scroll inside their own containers; body text never becomes a narrow column.
- Fixed synthetic badges must not overlap a taller publication masthead.

## Interaction contract

- Navigation anchors resolve from root, article, and exhibit paths.
- Theme choice persists through the existing local-storage behavior.
- Journey/Catalog, search, presets, facets, clear, URL serialization, and browser
  history remain functional.
- Search results report the visible count and expose an explicit empty state.
- The full article index remains available without JavaScript.
- Browser JavaScript may select or map committed states; it does not recompute
  estimators.

## Publication and content constraints

- Use only public or synthetic evidence and fictional displayed names.
- Current attestation and live ceiling remain visually distinct.
- Estimate-bearing outputs remain intervals, scenarios, or explicit refusals.
- The 36-card platform roadmap and parked P4 work are not website prerequisites.
- No existing card is reclassified as operationally ready merely because its page is
  live.

## Implementation boundary

Expected production edits are limited to:

- `src/quant_allocator/site/build.py`
- `site/templates/base.html.j2`
- `site/templates/index.html.j2`
- `site/templates/spec.html.j2`
- `site/templates/demo.html.j2`
- `site/assets/design-tokens.css`
- shell/article sections of `site/assets/interval.css`
- `site/assets/gallery.css`
- `site/assets/gallery.js` only if the new grouping contract requires it
- focused site tests and one static-output integrity test

The 23 page-specific exhibit templates, committed JSON, generators, and statistical
engines are out of scope.

## Acceptance

- The homepage visibly reads as a research publication before it exposes filters.
- Start Here, five pillars, and all 23 article/exhibit links are present.
- The paired article/exhibit relationship is navigable in both directions.
- Desktop 1440×900 and mobile 390×844 renders have no clipping or horizontal overflow.
- Search, view switching, one preset, one facet, clear, theme, and back/forward work.
- All 47 generated HTML files and local assets resolve.
- Existing numerical/page contracts pass unchanged.
- Final visual comparison against the selected concepts records no material P0/P1/P2
  mismatch.
