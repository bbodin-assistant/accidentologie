#!/usr/bin/env python3
"""Construit le site cartographique publié par le workflow GitHub Pages."""

from __future__ import annotations

import argparse
from pathlib import Path

from accidentologie import build_web_map


CARA_COMMUNES = (
    "17015", "17021", "17034", "17060", "17064", "17068", "17079",
    "17098", "17119", "17131", "17152", "17155", "17160", "17183",
    "17151", "17452", "17097", "17225", "17228", "17230", "17247",
    "17248", "17306", "17307", "17311", "17333", "17380", "17393",
    "17409", "17421", "17425", "17437", "17461",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(2005, 2025)),
        help="années publiées (défaut : 2005 à 2024)",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("site"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = build_web_map(
        years=args.years,
        communes=CARA_COMMUNES,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        title="Accidents corporels dans la CARA",
    )
    print(f"Site cartographique : {index.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
