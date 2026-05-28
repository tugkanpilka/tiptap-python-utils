# Changelog

## 0.2.0

Architecture refactor (audit phases 1–4). Public surface is reorganized;
behavior is unchanged for everything that was retained.

### Breaking changes

- Removed the `tiptap_python_utils.edit` package. The two document-level
  commands it exported are now methods on `Content`:
  - `append_node(doc, node)` → `Content.require(doc).append_root(node).dump()`
  - `replace_node(doc, id, node)` → `Content.require(doc).replace_by_id(id, node).dump()`
- `Selection.text(...)` and `Selection.marks(...)` are now strict and require a
  text ref. Chain `.leaf()` first to descend from a container, e.g.
  `where_id("p1").leaf().text("New")`.
- `Heading.level` is now a `@property` derived from `attrs.level`. The
  `Heading(level=...)` keyword argument was removed; set the value via
  `attrs={"level": N}` or `selection.attr("level", N)`.
- `TaskItem` stored fields (`task_item_id`, `is_completed`,
  `local_task_item_id`, `canonical_task_item_id`, `is_linked_copy`) are now
  `@property` derived from `attrs`/`extra`. Construct task items via
  `TaskItem(attrs={"id": ..., "checked": ...}, ...)`; the old keyword
  arguments were removed.

### Architecture

- `model/__init__.py` is now a re-export barrel. Implementation moved to
  `model/base.py`, `model/nodes.py`, `model/registry.py`, `model/payload.py`.
  All previous import paths still work.
- `codec/json.py` was split into `codec/raw.py` (JSON I/O + dict-shape
  helpers, zero `..model` dependency), `codec/reader.py` (raw → typed AST),
  and `codec/writer.py` (typed → raw + dump). Barrel exports unchanged.
- `shared/service.py` was split into `shared/identity.py`,
  `shared/fingerprint.py`, `shared/families.py`, and `shared/sync.py`. Barrel
  exports unchanged.
- `Content` gained `append_root(node_or_raw)` and `replace_by_id(id,
  node_or_raw)` document-level methods.
- `Selection` gained `.leaf()` to descend to the first text descendant of each
  ref.

### Added

- `tests/test_codec_raw.py` exercises the raw codec layer in isolation,
  including an invariant test that ensures `codec.raw` never imports
  `..model`.
- `tests/test_compat_imports.py` and `tests/test_public_api.py` snapshot the
  importable surface so future refactors can move implementation without
  breaking imports.
- README documents `Content.parse` / `require` / `wrap`, the lossless
  round-trip mechanism, document-level commands, `TaskItem` derived
  properties, and an end-to-end `shared_families` / `sync_shared` example.

## 0.1.0

- Initial public package structure.
- Typed TipTap AST model and content facade.
- JSON parsing and serialization with lossless unknown-node round trips.
- Traversal, selection, immutable edit helpers, text extraction, task helpers, and shared-node synchronization.
