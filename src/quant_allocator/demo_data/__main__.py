"""CLI: python -m quant_allocator.demo_data build [card|all].

Each generator registers a zero-argument builder that writes its JSON into
site/data/ and returns the written path. Later tasks add entries to
_builders(); this scaffolding task ships it empty.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path


def _builders() -> dict[str, Callable[[], Path]]:
    from quant_allocator.demo_data import (
        e2_pack,
        e3_knowledge,
        e4_operational_change,
        m1_drift,
        m2_convexity,
        m3_alarms,
        m4_crowding,
        m5_saydo,
        m6_holdings,
        p1_allocation,
        p2_xray,
        p3_hirefire,
        powergate_registry,
        s1_ledger,
        s2_tearsheet,
        s3_lab,
        s4_sell,
        s5_shortbook,
        s6_signatures,
        s7_provenance,
        x1_atlas,
        x2_playground,
        x3_universe,
    )

    return {
        "e2_pack": e2_pack.build,
        "e3_knowledge": e3_knowledge.build,
        "e4_operational_change": e4_operational_change.build,
        "m1_drift": m1_drift.build,
        "m2_convexity": m2_convexity.build,
        "m3_alarms": m3_alarms.build,
        "m4_crowding": m4_crowding.build,
        "m5_saydo": m5_saydo.build,
        "m6_holdings": m6_holdings.build,
        "p1_allocation": p1_allocation.build,
        "p2_xray": p2_xray.build,
        "p3_hirefire": p3_hirefire.build,
        "powergate_registry": powergate_registry.build,
        "s1_ledger": s1_ledger.build,
        "s2_tearsheet": s2_tearsheet.build,
        "s3_lab": s3_lab.build,
        "s4_sell": s4_sell.build,
        "s5_shortbook": s5_shortbook.build,
        "s6_signatures": s6_signatures.build,
        "s7_provenance": s7_provenance.build,
        "x1_atlas": x1_atlas.build,
        "x2_playground": x2_playground.build,
        "x3_universe": x3_universe.build,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quant_allocator.demo_data")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build one card by id, or 'all'")
    build.add_argument("card", help="card id (e.g. s1_ledger, m5_saydo) or 'all'")
    args = parser.parse_args(argv)

    builders = _builders()
    if args.card == "all":
        for card_id, builder in sorted(builders.items()):
            path = builder()
            print(f"wrote {path}")
        return 0
    if args.card not in builders:
        parser.error(f"unknown card {args.card!r}; known: {sorted(builders)} or 'all'")
    path = builders[args.card]()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
