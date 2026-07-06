"""CLI entry point: python -m quant_allocator.site build [--site-dir ...] [--out ...]."""

from __future__ import annotations

import argparse
from pathlib import Path

from quant_allocator.site.build import BuildError, build


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m quant_allocator.site")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Render the static site")
    build_parser.add_argument("--site-dir", type=Path, default=Path("site"))
    build_parser.add_argument("--out", type=Path, default=Path("site/_build"))

    args = parser.parse_args(argv)

    if args.command == "build":
        try:
            build(args.site_dir, args.out)
        except BuildError as error:
            parser.exit(status=2, message=f"build failed: {error}\n")


if __name__ == "__main__":
    main()
