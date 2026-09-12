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
    """Raised when a flag can't be represented in the target format, or
    when the input doesn't even have the shape of a flag definition."""


def _require_dict(value: Any, what: str) -> dict:
    if not isinstance(value, dict):
        raise ConversionError(f"{what} must be a JSON object, got {value!r}")
    return value


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


def _variation_index(value: Any, variations: list, key: Any, where: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value < len(variations)
    ):
        raise ConversionError(
            f"{key!r}: {where} variation index must be 0 or 1, got {value!r}"
        )
    return value


def ld_to_flat(flag: dict) -> dict:
    """Convert a LaunchDarkly-style flag dict to the flat format."""
    flag = _require_dict(flag, "flag")
    key = flag.get("key")
    if not isinstance(key, str) or not key:
        raise ConversionError(f"flag is missing a non-empty 'key', got {key!r}")

    variations = flag.get("variations")
    _boolean_variations(variations)

    fallthrough = _require_dict(flag.get("fallthrough", {}), f"{key!r}: fallthrough")
    if "rollout" in fallthrough:
        raise ConversionError(
            f"{key!r}: percentage rollouts have no equivalent in the flat "
            "format"
        )
    if "variation" not in fallthrough:
        raise ConversionError(f"{key!r}: fallthrough must set a variation index")
    default_variation = _variation_index(
        fallthrough["variation"], variations, key, "fallthrough"
    )

    off_variation_raw = flag.get("offVariation")
    if off_variation_raw is None:
        raise ConversionError(f"{key!r}: missing offVariation")
    off_variation = _variation_index(off_variation_raw, variations, key, "offVariation")

    default_value = variations[default_variation]
    off_value = variations[off_variation]

    targets = flag.get("targets", [])
    if not isinstance(targets, list):
        raise ConversionError(f"{key!r}: targets must be a list, got {targets!r}")

    overrides: dict = {}
    for target in targets:
        target = _require_dict(target, f"{key!r}: target")
        if "variation" not in target or "values" not in target:
            raise ConversionError(
                f"{key!r}: target must have 'variation' and 'values'"
            )
        variation = _variation_index(target["variation"], variations, key, "target")
        values = target["values"]
        if not isinstance(values, list) or not all(
            isinstance(v, str) for v in values
        ):
            raise ConversionError(
                f"{key!r}: target values must be a list of user keys, got "
                f"{values!r}"
            )
        value = variations[variation]
        for user_key in values:
            if user_key in overrides and overrides[user_key] != value:
                raise ConversionError(
                    f"{key!r}: user {user_key!r} is targeted into two "
                    "different variations"
                )
            overrides[user_key] = value

    rules_in = flag.get("rules", [])
    if not isinstance(rules_in, list):
        raise ConversionError(f"{key!r}: rules must be a list, got {rules_in!r}")

    rules = []
    for rule in rules_in:
        rule = _require_dict(rule, f"{key!r}: rule")
        if "variation" not in rule:
            raise ConversionError(f"{key!r}: rule is missing 'variation'")
        variation = _variation_index(rule["variation"], variations, key, "rule")

        clauses = rule.get("clauses", [])
        if not isinstance(clauses, list) or len(clauses) != 1:
            raise ConversionError(
                f"{key!r}: only single-clause rules are supported (no "
                "AND/OR of multiple clauses)"
            )
        clause = _require_dict(clauses[0], f"{key!r}: clause")
        if "attribute" not in clause or "values" not in clause:
            raise ConversionError(
                f"{key!r}: clause must have 'attribute' and 'values'"
            )
        attribute = clause["attribute"]
        if not isinstance(attribute, str) or not attribute:
            raise ConversionError(
                f"{key!r}: clause attribute must be a non-empty string, got "
                f"{attribute!r}"
            )
        values = clause["values"]
        if not isinstance(values, list):
            raise ConversionError(
                f"{key!r}: clause values must be a list, got {values!r}"
            )
        if clause.get("op") != "in":
            raise ConversionError(
                f"{key!r}: unsupported clause operator {clause.get('op')!r}, "
                "only 'in' is supported"
            )
        flat_rule = {
            "attribute": attribute,
            "in": values,
            "value": variations[variation],
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
    flag = _require_dict(flag, "flag")
    name = flag.get("name")
    if not isinstance(name, str) or not name:
        raise ConversionError(f"flag is missing a non-empty 'name', got {name!r}")

    for field in ("default_value", "off_value"):
        value = flag.get(field)
        if not isinstance(value, bool):
            raise ConversionError(
                f"{name!r}: {field} must be a boolean, got {value!r}"
            )

    variations = [True, False]

    def index_of(value: bool) -> int:
        return variations.index(value)

    overrides_in = flag.get("overrides", {})
    overrides_in = _require_dict(overrides_in, f"{name!r}: overrides")

    targets_by_variation: dict = {}
    for user_key, value in overrides_in.items():
        if not isinstance(user_key, str):
            raise ConversionError(
                f"{name!r}: override keys must be strings, got {user_key!r}"
            )
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

    rules_in = flag.get("rules", [])
    if not isinstance(rules_in, list):
        raise ConversionError(f"{name!r}: rules must be a list, got {rules_in!r}")

    rules = []
    for rule in rules_in:
        rule = _require_dict(rule, f"{name!r}: rule")
        if "attribute" not in rule or "in" not in rule or "value" not in rule:
            raise ConversionError(
                f"{name!r}: rule must have 'attribute', 'in', and 'value'"
            )
        attribute = rule["attribute"]
        if not isinstance(attribute, str) or not attribute:
            raise ConversionError(
                f"{name!r}: rule attribute must be a non-empty string, got "
                f"{attribute!r}"
            )
        in_values = rule["in"]
        if not isinstance(in_values, list):
            raise ConversionError(
                f"{name!r}: rule 'in' must be a list, got {in_values!r}"
            )
        value = rule["value"]
        if not isinstance(value, bool):
            raise ConversionError(
                f"{name!r}: rule value must be a boolean, got {value!r}"
            )
        clause = {
            "attribute": attribute,
            "op": "in",
            "values": in_values,
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
