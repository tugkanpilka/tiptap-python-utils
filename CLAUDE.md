# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python -m pip install -e ".[dev]"   # install with dev extras
pytest -q                            # run full suite (also: `make test`)
pytest tests/test_content.py -q      # single file
pytest tests/test_content.py::test_name -q   # single test
python -m build                      # build sdist + wheel (also: `make build`)
python -m twine check dist/*         # validate artifact (also: `make check`)
make clean                           # remove build/dist/egg-info/.pytest_cache
```

`pyproject.toml` sets `pythonpath = ["src"]`, so `pytest` works without installing. Python ≥ 3.9. No runtime dependencies.

## Architecture

The package converts raw TipTap JSON to a typed, immutable AST and back, preserving unknown fields for lossless round-trip. Layering (lowest to highest):

1. **`contract/`** — Raw JSON contract. `key` (field names like `type`/`attrs`/`content`), `kind` (node kind strings like `paragraph`/`taskItem`), `policy` (identity rules: `content_id`, `node_id`, `tiptap_id`, `shared_id`, `is_parseable`).
2. **`model/`** — Frozen dataclass AST. `Node` is the base; concrete classes (`Paragraph`, `Heading`, `TaskItem`, `Text`, `Doc`, list/container nodes) register themselves in `registry`. `Unknown` captures any kind not in the registry — this is how round-trip preservation works. Every `Node` carries `extra` (unknown top-level fields) and `present` (which keys appeared in raw input), so `raw()` re-emits the same shape it parsed.
3. **`codec/json.py`** — Raw JSON ↔ model boundary. `parse_raw`, `read_doc`, `read_node`, `read_children` go raw→typed via `registry.read`; `dump`/`dumps` go typed→raw.
4. **`tree/path.py`** — `node_at_path` / `replace_at_path` operate on tuple paths `(int, int, ...)` into the immutable tree.
5. **`walk/traversal.py`** — `Walker` does depth-first iteration. `Ref(node, path, parent_kind)` is the addressable handle a `Selection` works against. `Ref.parseable` honors `policy.is_parseable` (used to skip non-selectable kinds like raw text).
6. **`select/selection.py`** — `Selection` is the fluent edit API and the single home for mutation. Atomic methods (`.text`, `.marks`, `.attr`, `.append`, `.replace`, `.set`) call `Node`/`Text` primitives directly. `.text` and `.marks` are strict — they require Text refs; callers chain `.leaf()` first to descend. `_apply` sorts refs by path length **descending** so deeper edits land before shallower ones shift their paths. `.set(name, value)` round-trips through codec so subclass-typed fields (e.g. `Heading.level`) re-hydrate; this is the OCP-respecting escape hatch.
7. **`content.py`** — `Content` is the public facade. Three constructors with different strictness: `parse` (lenient, allows `None`), `require` (must be a valid `doc`), `wrap` (auto-wraps a non-doc node in a `doc`). `where_id(id)` and `of(kind)` return `Selection`s. `append_root(node)` and `replace_by_id(id, node)` are the document-level entry points; they compose Selection chains internally.
8. **`text/`, `tasks/`, `shared/`** — User-facing workflows built on `Content`. `shared/service.py` handles synchronization of nodes that share a `sharedId` across the document (fingerprint + merge).

### Round-trip invariant

Parsing must not silently drop fields. The mechanism:
- `Node.extra` stores top-level keys other than `type`/`attrs`/`content` (and per-node known keys like `text`/`marks` for `Text`).
- `Node.present` records which structural keys appeared in the raw input, so `raw()` emits empty `attrs: {}` or `content: []` only when they were originally present.
- Unknown kinds become `Unknown(raw_kind=…)` rather than being rejected.

When adding behavior to `Node.raw()` or subclasses, do not lose `extra` or violate `present` semantics — `tests/test_content.py` exercises round-trip cases.

### Identity model

Multiple identity sources exist; `contract/policy.py` is the single source of truth:
- `content_id` — generic node ID from attrs.
- `tiptap_id` — TipTap's own attr key.
- `node_id` — resolution between the two.
- `shared_id` — used by `shared/` to link copies of the same logical node.
- `TaskItem` additionally tracks `local_task_item_id`, `canonical_task_item_id`, and `is_linked_copy` to model linked-copy tasks.

When selecting by ID, prefer `Content.where_id`, which uses `selection_id` (in `walk/traversal.py`) — that helper unifies the rules.

### Immutability

All nodes are `@dataclass(frozen=True)`. Mutations always return new instances via `dataclasses.replace` or `Node.with_*` helpers. `Selection._apply` rebuilds the path from leaf upward. Do not mutate `attrs`/`extra` dicts in place — `deepcopy` before changing.

## Known architecture debt

`docs/architecture-audit.md` (dated 2026-05-28) is an internal audit. Status:
- Phase 1 (model split into `base`/`nodes`/`registry`/`payload` re-exports): **done**.
- Phase 2 (edit layer): **done — different shape than the audit proposed**. The audit suggested splitting `edit/commands.py`; the actual outcome was deleting `edit/` entirely. Selection methods now call Node primitives directly; `append_node`/`replace_node` became `Content.append_root`/`Content.replace_by_id`. The audit's text on Phase 2 is stale.
- Phase 3 (`codec/json.py` split into raw I/O + AST hydration): **done**. `codec/raw.py` holds JSON parsing + dict-shape helpers with zero `..model` dependency; `codec/reader.py` hydrates the typed AST; `codec/writer.py` dumps. The barrel `codec/__init__.py` re-exports the same 11 names. `tests/test_codec_raw.py` exercises the raw layer in isolation.
- Phase 4 (`shared/service.py` split into `identity`/`fingerprint`/`families`/`sync`): **done**. `shared/identity.py` holds value-level helpers (`normalize_shared_id`, `new_shared_id`, `shared_id`, `stamp_shared`); `shared/fingerprint.py` isolates the JSON normalization used to detect divergent bodies; `shared/families.py` groups canonical bodies by sharedId and answers presence queries (`shared_families`, `has_shared`); `shared/sync.py` rewrites matching nodes (`sync_shared`, `_merge_preserving_identity`). Barrel `shared/__init__.py` re-exports the same 8 names. Dependency direction is one-way: identity → fingerprint → families → sync.
- Phase 5 (public API classification — `content_id`, `is_parseable`, `EMPTY_DOCUMENT_CONTENT` etc.): pending.

Compatibility requirement for any refactor: keep `from tiptap_python_utils import Paragraph`, `from tiptap_python_utils.model import ContentTuple`, and `from tiptap_python_utils.model import registry` working. Public API snapshot lives in `tests/test_public_api.py` and `tests/test_compat_imports.py`.

## Release

Trusted publishing to PyPI via the `publish.yml` GitHub workflow on tag push (`vX.Y.Z`). Full checklist in `docs/release.md` and `CONTRIBUTING.md`. Bump `pyproject.toml` `version` and update `CHANGELOG.md` before tagging.
