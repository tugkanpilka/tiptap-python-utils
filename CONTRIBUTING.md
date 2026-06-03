# Contributing

Thanks for improving `tiptap_python_utils`.

## Before you open a pull request

Please open an issue first at
[github.com/tugkanpilka/tiptap-python-utils/issues](https://github.com/tugkanpilka/tiptap-python-utils/issues)
and describe what you want to change. This lets us align on the approach before
you invest time in a PR — especially for anything that touches the public API,
the round-trip invariant, or the identity model.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

`pyproject.toml` sets `pythonpath = ["src"]`, so `pytest` works without
installing. Python ≥ 3.9. No runtime dependencies.

## Running tests

```bash
pytest -q                                      # full suite
pytest tests/test_content.py -q                # single file
pytest tests/test_content.py::test_name -q     # single test
```

## Architecture

The package is layered: `contract` (key/kind/policy primitives) → `model`
(immutable AST with a registry of node classes; unknown kinds round-trip via
`Unknown`) → `codec` (raw I/O in `raw.py`, hydration in `reader.py`, dump in
`writer.py`) → `walk` & `tree` (traversal + path-based replacement on the
immutable tree) → `select` (fluent `Selection` — the single home for mutation)
→ `content` (public facade) → `text` / `tasks` / `shared` (user-facing
workflows built on `Content`). All nodes are `@dataclass(frozen=True)`;
mutations return new instances.

A core invariant is the **lossless round trip**: parsing must never silently
drop fields. `Node.extra` stores unknown top-level keys, `Node.present` records
which structural keys appeared in the raw input, and unknown node kinds become
`Unknown`. When editing `Node.raw()` or its subclasses, do not lose `extra` or
violate `present` semantics — `tests/test_content.py` exercises round-trip
cases. See [CLAUDE.md](CLAUDE.md) for the full architecture notes.

## Release checklist

1. Update `CHANGELOG.md`.
2. Bump the version in `pyproject.toml`.
3. Run `pytest -q`.
4. Run `python -m build`.
5. Run `python -m twine check dist/*`.
6. Tag the release as `vX.Y.Z`.

See [docs/release.md](docs/release.md) for the trusted-publishing setup and the
full publish flow.
</content>
