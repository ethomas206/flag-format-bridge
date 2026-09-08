"""Table-driven tests for flagconv.converter.

The cases here are the awkward ones: multivariate flags, percentage
rollouts, multi-clause rules, and other shapes LaunchDarkly allows that
the flat format has no way to represent.
"""

import unittest

from flagconv.converter import ConversionError, flat_to_ld, ld_to_flat

LD_TO_FLAT_CASES = [
    (
        "simple on flag",
        {
            "key": "new-checkout",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 0},
        },
        {
            "name": "new-checkout",
            "enabled": True,
            "default_value": True,
            "off_value": False,
        },
    ),
    (
        "flag turned off, fallthrough still set",
        {
            "key": "new-checkout",
            "on": False,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 0},
        },
        {
            "name": "new-checkout",
            "enabled": False,
            "default_value": True,
            "off_value": False,
        },
    ),
    (
        "default and off resolve to the same value",
        {
            "key": "always-on",
            "on": True,
            "variations": [True, False],
            "offVariation": 0,
            "fallthrough": {"variation": 0},
        },
        {
            "name": "always-on",
            "enabled": True,
            "default_value": True,
            "off_value": True,
        },
    ),
    (
        "individual user targets",
        {
            "key": "beta-ui",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "targets": [
                {"variation": 0, "values": ["alice", "bob"]},
                {"variation": 1, "values": ["carol"]},
            ],
        },
        {
            "name": "beta-ui",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "overrides": {"alice": True, "bob": True, "carol": False},
        },
    ),
    (
        "single-clause rule",
        {
            "key": "eu-only",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "rules": [
                {
                    "variation": 0,
                    "clauses": [
                        {
                            "attribute": "country",
                            "op": "in",
                            "values": ["DE", "FR"],
                        }
                    ],
                }
            ],
        },
        {
            "name": "eu-only",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "rules": [
                {"attribute": "country", "in": ["DE", "FR"], "value": True}
            ],
        },
    ),
    (
        "negated clause",
        {
            "key": "not-eu",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "rules": [
                {
                    "variation": 0,
                    "clauses": [
                        {
                            "attribute": "country",
                            "op": "in",
                            "values": ["DE", "FR"],
                            "negate": True,
                        }
                    ],
                }
            ],
        },
        {
            "name": "not-eu",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "rules": [
                {
                    "attribute": "country",
                    "in": ["DE", "FR"],
                    "value": True,
                    "negate": True,
                }
            ],
        },
    ),
]

LD_TO_FLAT_ERROR_CASES = [
    (
        "multivariate flag",
        {
            "key": "button-color",
            "on": True,
            "variations": ["red", "green", "blue"],
            "offVariation": 0,
            "fallthrough": {"variation": 1},
        },
    ),
    (
        "non-boolean two-way variations",
        {
            "key": "mode",
            "on": True,
            "variations": ["a", "b"],
            "offVariation": 0,
            "fallthrough": {"variation": 1},
        },
    ),
    (
        "percentage rollout",
        {
            "key": "gradual",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {
                "rollout": {
                    "variations": [
                        {"variation": 0, "weight": 50000},
                        {"variation": 1, "weight": 50000},
                    ]
                }
            },
        },
    ),
    (
        "rule with multiple clauses",
        {
            "key": "eu-enterprise",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "rules": [
                {
                    "variation": 0,
                    "clauses": [
                        {"attribute": "country", "op": "in", "values": ["DE"]},
                        {
                            "attribute": "plan",
                            "op": "in",
                            "values": ["enterprise"],
                        },
                    ],
                }
            ],
        },
    ),
    (
        "unsupported clause operator",
        {
            "key": "big-orgs",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "rules": [
                {
                    "variation": 0,
                    "clauses": [
                        {
                            "attribute": "employees",
                            "op": "greaterThan",
                            "values": [500],
                        }
                    ],
                }
            ],
        },
    ),
    (
        "same user targeted into two variations",
        {
            "key": "conflicted",
            "on": True,
            "variations": [True, False],
            "offVariation": 1,
            "fallthrough": {"variation": 1},
            "targets": [
                {"variation": 0, "values": ["dave"]},
                {"variation": 1, "values": ["dave"]},
            ],
        },
    ),
]

FLAT_TO_LD_ROUND_TRIP_CASES = [
    (
        "minimal flag",
        {
            "name": "new-checkout",
            "enabled": True,
            "default_value": True,
            "off_value": False,
        },
    ),
    (
        "with overrides",
        {
            "name": "beta-ui",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "overrides": {"alice": True, "carol": False},
        },
    ),
    (
        "with a rule",
        {
            "name": "eu-only",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "rules": [
                {"attribute": "country", "in": ["DE", "FR"], "value": True}
            ],
        },
    ),
    (
        "with a negated rule",
        {
            "name": "not-eu",
            "enabled": True,
            "default_value": False,
            "off_value": False,
            "rules": [
                {
                    "attribute": "country",
                    "in": ["DE", "FR"],
                    "value": True,
                    "negate": True,
                }
            ],
        },
    ),
]

FLAT_TO_LD_ERROR_CASES = [
    (
        "non-boolean default_value",
        {
            "name": "mode",
            "enabled": True,
            "default_value": "a",
            "off_value": "b",
        },
    ),
    (
        "non-boolean override",
        {
            "name": "weird",
            "enabled": True,
            "default_value": True,
            "off_value": False,
            "overrides": {"alice": "yes"},
        },
    ),
    (
        "non-boolean rule value",
        {
            "name": "weird-rule",
            "enabled": True,
            "default_value": True,
            "off_value": False,
            "rules": [{"attribute": "country", "in": ["DE"], "value": "on"}],
        },
    ),
]


class LdToFlatTests(unittest.TestCase):
    def test_conversions(self):
        for name, ld_flag, expected_flat in LD_TO_FLAT_CASES:
            with self.subTest(name=name):
                self.assertEqual(ld_to_flat(ld_flag), expected_flat)

    def test_errors(self):
        for name, ld_flag in LD_TO_FLAT_ERROR_CASES:
            with self.subTest(name=name):
                with self.assertRaises(ConversionError):
                    ld_to_flat(ld_flag)


class FlatToLdTests(unittest.TestCase):
    def test_round_trip_through_ld_to_flat(self):
        for name, flat_flag in FLAT_TO_LD_ROUND_TRIP_CASES:
            with self.subTest(name=name):
                ld_flag = flat_to_ld(flat_flag)
                self.assertEqual(ld_to_flat(ld_flag), flat_flag)

    def test_errors(self):
        for name, flat_flag in FLAT_TO_LD_ERROR_CASES:
            with self.subTest(name=name):
                with self.assertRaises(ConversionError):
                    flat_to_ld(flat_flag)


if __name__ == "__main__":
    unittest.main()
