"""Command-line interface for flagconv."""

from __future__ import annotations

import argparse
import json
import sys

from .converter import ConversionError, flat_to_ld, ld_to_flat


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="flagconv",
        description="Convert feature flag definitions between formats.",
    )
    parser.add_argument(
        "direction",
        choices=["ld-to-flat", "flat-to-ld"],
        help="which way to convert",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input JSON file (default: stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="output JSON file (default: stdout)",
    )
    args = parser.parse_args(argv)

    flag = json.load(args.input)
    convert = ld_to_flat if args.direction == "ld-to-flat" else flat_to_ld

    try:
        result = convert(flag)
    except ConversionError as exc:
        print(f"flagconv: {exc}", file=sys.stderr)
        return 1

    json.dump(result, args.output, indent=2, sort_keys=True)
    args.output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
