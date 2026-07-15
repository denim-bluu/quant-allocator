# Quant Allocator

A public editorial research publication and project-idea bank about quantitative
methods for allocator decisions under partial transparency. Its publication contract
pairs each idea with a long-form technical article and an honest synthetic or public
exhibit: what the method claims, why the decision is hard, what the data can support,
and what would be needed to use it live.

**Thesis:** Every allocator analytic is an exercise in inference under partial transparency.

## Gallery

Live gallery: **<https://denim-bluu.github.io/quant-allocator/>**

## Repository map

- `docs/PRODUCT.md` — the canonical product charter and scope boundary.
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
