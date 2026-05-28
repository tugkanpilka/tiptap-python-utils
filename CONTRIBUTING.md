# Contributing

Thanks for improving `tiptap_python_utils`.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

## Release checklist

1. Update `CHANGELOG.md`.
2. Bump the version in `pyproject.toml`.
3. Run `pytest -q`.
4. Run `python -m build`.
5. Run `python -m twine check dist/*`.
6. Tag the release as `vX.Y.Z`.
