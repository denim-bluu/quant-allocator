"""Local-only demo-data generation package.

Consumes numpy/pandas and the simulator to build seeded synthetic rosters and
exposure paths, then writes deterministic JSON into site/data/. NEVER imported
by quant_allocator.site (the CI builder renders committed JSON; it never
computes). Run locally: python -m quant_allocator.demo_data build [card|all].
"""
