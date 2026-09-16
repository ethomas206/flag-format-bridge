"""Render flat-format flags as CSV, for pasting into a spreadsheet.

This is one-way: overrides and rules get squashed into readable text
columns rather than a structure you could parse back out. If you need
the flag definitions back, keep the JSON and treat the CSV as a view.
"""

from __future__ import annotations

import csv
import io

from .converter import ConversionError, flat_to_ld

FIELDNAMES = ["name", "enabled", "default_value", "off_value", "overrides", "rules"]


def _format_overrides(overrides: dict) -> str:
    return "; ".join(
        f"{user_key}={str(value).lower()}"
        for user_key, value in sorted(overrides.items())
    )


def _format_rules(rules: list) -> str:
    parts = []
    for rule in rules:
        op = "not in" if rule.get("negate") else "in"
        values = ", ".join(rule["in"])
        parts.append(f"{rule['attribute']} {op} [{values}] => {str(rule['value']).lower()}")
    return "; ".join(parts)


def flat_to_csv(flags: list) -> str:
    """Convert a list of flat-format flag dicts to a CSV string.

    Each flag is validated the same way flat_to_ld validates it, so a
    malformed flag raises ConversionError instead of producing a row
    with missing or garbled columns.
    """
    if not isinstance(flags, list):
        raise ConversionError(f"expected a list of flags, got {flags!r}")

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(FIELDNAMES)
    for flag in flags:
        flat_to_ld(flag)  # raises ConversionError on anything malformed
        writer.writerow(
            [
                flag["name"],
                str(bool(flag.get("enabled", False))).lower(),
                str(flag["default_value"]).lower(),
                str(flag["off_value"]).lower(),
                _format_overrides(flag.get("overrides", {})),
                _format_rules(flag.get("rules", [])),
            ]
        )
    return output.getvalue()
