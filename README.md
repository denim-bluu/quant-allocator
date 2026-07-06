# Quant Allocator

A research portfolio of allocator-side analytics for hedge-fund manager
selection, monitoring, and engagement — built on a synthetic-manager simulator
and public data only. The gallery presents each idea as an honest mockup: what
the analytic claims, what data tier it needs, and the statistical reason the
ask exists.

**Thesis:** Every analytic here is an exercise in inference under partial transparency.

## Gallery

<!-- set after Pages enablement -->
Live gallery: `https://USERNAME.github.io/quant-allocator/`

## Repository map

- `site/` — the static gallery: card manifest (`cards.yaml`), Jinja2 templates,
  Interval design-system assets, vendored KaTeX, and committed demo data.
- `src/quant_allocator/site/` — the render-only builder (`build.py`, CLI).
- `src/quant_allocator/simulator/`, `.../adapters/` — the synthetic-manager
  simulator and public-data adapters that produce the numbers.
- `docs/ideas/`, `docs/superpowers/` — idea cards, design specs, and plans.
- `tools/` — publication-readiness scanning.

## Data policy

All data on this site is synthetic or public. No employer-internal facts and no
real manager names appear anywhere in this repository.

## License

MIT — see `LICENSE`.
