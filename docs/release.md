# Release

This package is intended to be published from its own repository.

## One-time PyPI setup

Use PyPI trusted publishing for the GitHub repository. Configure a PyPI project
named `tiptap_python_utils` and allow the `publish.yml` workflow to publish
tagged releases.

Trusted publisher values:

- PyPI project name: `tiptap_python_utils`
- Owner: `tugkanpilka`
- Repository: `tiptap-python-utils`
- Workflow: `publish.yml`
- Environment: `pypi`

The expected trusted publishing subject is:

```text
repo:tugkanpilka/tiptap-python-utils:environment:pypi
```

## Publish flow

```bash
pytest -q
python -m build
python -m twine check dist/*
git tag v0.1.0
git push origin v0.1.0
```

The publish workflow builds the package again in CI and uploads it to PyPI.
If the tag workflow already ran before PyPI was configured, run the `Publish`
workflow manually from GitHub Actions after trusted publishing is connected.
