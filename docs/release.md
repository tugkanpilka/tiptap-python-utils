# Release

This package is intended to be published from its own repository.

## One-time PyPI setup

Use PyPI trusted publishing for the GitHub repository. Configure a PyPI project
named `tiptap_python_utils` and allow the `publish.yml` workflow to publish
tagged releases.

## Publish flow

```bash
pytest -q
python -m build
python -m twine check dist/*
git tag v0.1.0
git push origin v0.1.0
```

The publish workflow builds the package again in CI and uploads it to PyPI.
