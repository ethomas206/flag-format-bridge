"""Tests for flagconv.csv_export."""

import unittest

from flagconv.converter import ConversionError
from flagconv.csv_export import flat_to_csv


class FlatToCsvTests(unittest.TestCase):
    def test_header_only_for_empty_list(self):
        self.assertEqual(
            flat_to_csv([]),
            "name,enabled,default_value,off_value,overrides,rules\n",
        )

    def test_minimal_flag(self):
        flags = [
            {
                "name": "new-checkout",
                "enabled": True,
                "default_value": True,
                "off_value": False,
            }
        ]
        self.assertEqual(
            flat_to_csv(flags),
            "name,enabled,default_value,off_value,overrides,rules\n"
            "new-checkout,true,true,false,,\n",
        )

    def test_overrides_are_sorted_and_joined(self):
        flags = [
            {
                "name": "beta-ui",
                "enabled": True,
                "default_value": False,
                "off_value": False,
                "overrides": {"carol": False, "alice": True, "bob": True},
            }
        ]
        self.assertEqual(
            flat_to_csv(flags),
            "name,enabled,default_value,off_value,overrides,rules\n"
            "beta-ui,true,false,false,alice=true; bob=true; carol=false,\n",
        )

    def test_rules_are_rendered_readably(self):
        flags = [
            {
                "name": "eu-only",
                "enabled": True,
                "default_value": False,
                "off_value": False,
                "rules": [
                    {"attribute": "country", "in": ["DE", "FR"], "value": True}
                ],
            }
        ]
        self.assertEqual(
            flat_to_csv(flags),
            "name,enabled,default_value,off_value,overrides,rules\n"
            'eu-only,true,false,false,,"country in [DE, FR] => true"\n',
        )

    def test_negated_rule(self):
        flags = [
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
            }
        ]
        self.assertEqual(
            flat_to_csv(flags),
            "name,enabled,default_value,off_value,overrides,rules\n"
            'not-eu,true,false,false,,"country not in [DE, FR] => true"\n',
        )

    def test_multiple_flags_produce_multiple_rows(self):
        flags = [
            {
                "name": "flag-a",
                "enabled": True,
                "default_value": True,
                "off_value": False,
            },
            {
                "name": "flag-b",
                "enabled": False,
                "default_value": False,
                "off_value": False,
            },
        ]
        self.assertEqual(
            flat_to_csv(flags),
            "name,enabled,default_value,off_value,overrides,rules\n"
            "flag-a,true,true,false,,\n"
            "flag-b,false,false,false,,\n",
        )

    def test_input_must_be_a_list(self):
        with self.assertRaises(ConversionError):
            flat_to_csv({"name": "not-a-list"})

    def test_malformed_flag_raises_conversion_error(self):
        with self.assertRaises(ConversionError):
            flat_to_csv([{"name": "bad", "default_value": "yes", "off_value": False}])


if __name__ == "__main__":
    unittest.main()
