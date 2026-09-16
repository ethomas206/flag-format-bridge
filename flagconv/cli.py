"""Command-line interface for flagconv."""

from __future__ import annotations

import argparse
import json
import sys

from .converter import ConversionError, flat_to_ld, ld_to_flat
from .csv_export import flat_to_csv


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="flagconv",
        description="Convert feature flag definitions between formats.",
    )
    parser.add_argument(
        "direction",
        choices=["ld-to-flat", "flat-to-ld", "to-csv"],
        help="which way to convert; to-csv renders flat-format flags as "
        "CSV for spreadsheet review",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input JSON file (default: stdin). For to-csv this may be a "
        "single flat flag object or a JSON array of them",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="output file (default: stdout)",
    )
    args = parser.parse_args(argv)

    loaded = json.load(args.input)

    if args.direction == "to-csv":
        flags = loaded if isinstance(loaded, list) else [loaded]
        try:
            csv_text = flat_to_csv(flags)
        except ConversionError as exc:
            print(f"flagconv: {exc}", file=sys.stderr)
            return 1
        args.output.write(csv_text)
        return 0

    convert = ld_to_flat if args.direction == "ld-to-flat" else flat_to_ld

    try:
        result = convert(loaded)
    except ConversionError as exc:
        print(f"flagconv: {exc}", file=sys.stderr)
        return 1

    json.dump(result, args.output, indent=2, sort_keys=True)
    args.output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
