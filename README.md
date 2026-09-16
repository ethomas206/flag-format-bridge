# flagconv

I keep flag definitions for a small internal service in a flat JSON file
that's easy to diff in a PR, but the flags started life as exports from
LaunchDarkly. This converts between the two shapes so I don't have to
hand-translate them.

LaunchDarkly's flag JSON is built around a `variations` array plus integer
indices for `offVariation`, `fallthrough`, targets, and rules. That's fine
for their UI, but it's unreadable in a diff and it supports things (three-way
variations, percentage rollouts) that the internal service doesn't need. The
flat format spells out `true`/`false` directly.

## Example

LaunchDarkly-style input:

```json
{
  "key": "beta-ui",
  "on": true,
  "variations": [true, false],
  "offVariation": 1,
  "fallthrough": {"variation": 1},
  "targets": [
    {"variation": 0, "values": ["alice", "bob"]}
  ],
  "rules": [
    {
      "variation": 0,
      "clauses": [{"attribute": "country", "op": "in", "values": ["DE", "FR"]}]
    }
  ]
}
```

converts to:

```json
{
  "name": "beta-ui",
  "enabled": true,
  "default_value": false,
  "off_value": false,
  "overrides": {"alice": true, "bob": true},
  "rules": [
    {"attribute": "country", "in": ["DE", "FR"], "value": true}
  ]
}
```

## Usage

```python
from flagconv import ld_to_flat, flat_to_ld

flat_flag = ld_to_flat(launchdarkly_flag_dict)
ld_flag = flat_to_ld(flat_flag)
```

Or from the command line:

```sh
python -m flagconv.cli ld-to-flat flags/beta-ui.json -o flat/beta-ui.json
python -m flagconv.cli flat-to-ld flat/beta-ui.json
```

Piping works too — omit the input file to read from stdin.

## CSV export

For a quick spreadsheet review of a batch of flags, `flat_to_csv` renders a
list of flat-format flags as CSV. It's one-way: overrides and rules get
squashed into readable text columns rather than a structure you could parse
back out.

```python
from flagconv import flat_to_csv

csv_text = flat_to_csv([flat_flag_one, flat_flag_two])
```

```sh
python -m flagconv.cli to-csv flags/all-flat.json -o flags.csv
```

The input can be a single flat flag object or a JSON array of them.

## What it doesn't support

Both directions only handle plain on/off boolean flags. If a LaunchDarkly
flag has more than two variations, uses a percentage rollout, or has a rule
with more than one clause, `ld_to_flat` raises `ConversionError` with an
explanation rather than silently dropping the parts it can't represent.
`flat_to_ld` similarly rejects non-boolean values anywhere in the flat
format. Malformed input — missing fields, wrong types, an out-of-range
variation index, JSON that isn't even an object — is rejected the same
way, with a message pointing at what's wrong, rather than an unhandled
`KeyError` or `TypeError`.

## Running the tests

```sh
python -m unittest discover -v
```

The test suite is table-driven: one table of LaunchDarkly shapes that should
convert cleanly, one of shapes that should be rejected, and a round-trip
check for the flat format.
