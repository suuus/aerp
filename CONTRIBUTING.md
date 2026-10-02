# Contributing

Contributions are welcome.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Build the package with:

```bash
python -m pip install build
python -m build
```

## Compatibility

Changes to record or bundle semantics require:

- updated JSON Schemas;
- matching deterministic CLI validation;
- tests for valid and invalid cases;
- migration or versioning notes;
- documentation of interoperability consequences.

Do not weaken validation or silently reinterpret existing result values.

## Pull requests

Keep changes focused. Include tests for behavior changes and update directly
related documentation.
