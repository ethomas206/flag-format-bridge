"""Convert feature flag definitions between the LaunchDarkly boolean-flag
export shape and a flat internal format.

Only boolean on/off flags are supported. LaunchDarkly's format also allows
multivariate flags and percentage rollouts, and neither has an equivalent
in the flat format, so those cases raise ConversionError instead of
silently dropping information.
"""

from __future__ import annotations

from typing import Any


class ConversionError(ValueError):
    """Raised when a flag can't be represented in the target format."""


def _boolean_variations(variations: Any) -> None:
    if not isinstance(variations, list) or len(variations) != 2:
        raise ConversionError(
            "only two-variation (on/off) flags are supported, got "
            f"{variations!r}"
        )
    if not all(isinstance(v, bool) for v in variations):
        raise ConversionError(
            f"variations must both be booleans, got {variations!r}"
        )


def ld_to_flat(flag: dict) -> dict:
    """Convert a LaunchDarkly-style flag dict to the flat format."""
    key = flag.get("key")
    variations = flag.get("variations")
    _boolean_variations(variations)

    fallthrough = flag.get("fallthrough", {})
    if "rollout" in fallthrough:
        raise ConversionError(
            f"{key!r}: percentage rollouts have no equivalent in the flat "
            "format"
        )
    if "variation" not in fallthrough:
        raise ConversionError(f"{key!r}: fallthrough must set a variation index")

    off_variation = flag.get("offVariation")
    if off_variation is None:
        raise ConversionError(f"{key!r}: missing offVariation")

    default_value = variations[fallthrough["variation"]]
    off_value = variations[off_variation]

    overrides: dict = {}
    for target in flag.get("targets", []):
        value = variations[target["variation"]]
        for user_key in target["values"]:
            if user_key in overrides and overrides[user_key] != value:
                raise ConversionError(
                    f"{key!r}: user {user_key!r} is targeted into two "
                    "different variations"
                )
            overrides[user_key] = value

    rules = []
    for rule in flag.get("rules", []):
        clauses = rule.get("clauses", [])
        if len(clauses) != 1:
            raise ConversionError(
                f"{key!r}: only single-clause rules are supported (no "
                "AND/OR of multiple clauses)"
            )
        clause = clauses[0]
        if clause.get("op") != "in":
            raise ConversionError(
                f"{key!r}: unsupported clause operator {clause.get('op')!r}, "
                "only 'in' is supported"
            )
        flat_rule = {
            "attribute": clause["attribute"],
            "in": clause["values"],
            "value": variations[rule["variation"]],
        }
        if clause.get("negate"):
            flat_rule["negate"] = True
        rules.append(flat_rule)

    flat = {
        "name": key,
        "enabled": bool(flag.get("on", False)),
        "default_value": default_value,
        "off_value": off_value,
    }
    if overrides:
        flat["overrides"] = overrides
    if rules:
        flat["rules"] = rules
    return flat


def flat_to_ld(flag: dict) -> dict:
    """Convert a flat-format flag dict to the LaunchDarkly-style format."""
    name = flag.get("name")
    for field in ("default_value", "off_value"):
        value = flag.get(field)
        if not isinstance(value, bool):
            raise ConversionError(
                f"{name!r}: {field} must be a boolean, got {value!r}"
            )

    variations = [True, False]

    def index_of(value: bool) -> int:
        return variations.index(value)

    targets_by_variation: dict = {}
    for user_key, value in flag.get("overrides", {}).items():
        if not isinstance(value, bool):
            raise ConversionError(
                f"{name!r}: override for {user_key!r} must be a boolean, "
                f"got {value!r}"
            )
        targets_by_variation.setdefault(index_of(value), []).append(user_key)

    targets = [
        {"variation": variation, "values": sorted(values)}
        for variation, values in sorted(targets_by_variation.items())
    ]

    rules = []
    for rule in flag.get("rules", []):
        value = rule.get("value")
        if not isinstance(value, bool):
            raise ConversionError(
                f"{name!r}: rule value must be a boolean, got {value!r}"
            )
        clause = {
            "attribute": rule["attribute"],
            "op": "in",
            "values": rule["in"],
        }
        if rule.get("negate"):
            clause["negate"] = True
        rules.append({"variation": index_of(value), "clauses": [clause]})

    ld_flag = {
        "key": name,
        "on": bool(flag.get("enabled", False)),
        "variations": variations,
        "offVariation": index_of(flag["off_value"]),
        "fallthrough": {"variation": index_of(flag["default_value"])},
    }
    if targets:
        ld_flag["targets"] = targets
    if rules:
        ld_flag["rules"] = rules
    return ld_flag
