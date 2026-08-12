#!/usr/bin/env python3
"""Construit le site cartographique publié par le workflow GitHub Pages."""

from __future__ import annotations

import argparse
from pathlib import Path

from accidentologie import Territory, build_web_map


CARA_GEOJSON = Path("data/reference/cara_communes.geojson")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=None,
        help="années publiées (défaut : toutes les années locales)",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("site"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cara = Territory.from_geojson(
        CARA_GEOJSON,
        name="Communauté d'agglomération Royan Atlantique (CARA)",
    )
    index = build_web_map(
        years=args.years,
        communes=cara.communes,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        title=f"Accidents corporels dans la {cara.name}",
    )
    print(f"Site cartographique : {index.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
