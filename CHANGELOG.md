# Changelog

## 0.3.0

Shared-node API aligned with the `Content` / `Selection` chain. The previous
dict-in / dict-out functional surface is gone — every shared-node operation is
now a method on `Content`, `Node`, or the new `SharedFamilies` value object.

### Breaking changes

- Removed the functional shared API: `shared_families`, `sync_shared`,
  `has_shared`, `shared_id`, `stamp_shared`, `fingerprint_shared`, and
  `normalize_shared_id` no longer exist (neither at the package root nor under
  `tiptap_python_utils.shared`).
- Migration:
  - `shared_families(content)` → `Content.require(content).shared_families()`
    (returns a `SharedFamilies`, not a raw dict).
  - `sync_shared(content, families)` → `Content.require(content).sync_shared(families)`
    (returns a new `Content`; the `(json, changed)` tuple is gone — compare
    `before.dump() != after.dump()` if you need a change flag).
  - `has_shared(content, sid)` → `Content.require(content).has_shared(sid)`.
  - `shared_id(node)` → `node.shared_id` (already a `Node` property).
  - `stamp_shared(node, sid)` → `node.with_shared_id(sid)`. To override the
    local id as well, chain `.with_attr("id", local_id)`.
  - `fingerprint_shared(raw_dict)` → `fingerprint(node)` — now takes a typed
    `Node`, not a raw dict.
- `SharedFamilies` itself is immutable: `__contains__`, `__getitem__`,
  `__iter__`, `__len__`, and `.merge(target)` for per-node rewrites.

### Added

- `Node.with_shared_id(value)` mirrors `with_attr` and returns a new node.
- `Content.where_shared_id(sid) -> Selection` selects every parseable node
  with a matching sharedId.
- `Content.has_shared(sid) -> bool`, `Content.shared_families() -> SharedFamilies`,
  and `Content.sync_shared(families) -> Content` replace the old functional
  helpers.
- `Selection.transform(fn)` is a new public escape hatch for per-node
  rewrites: `Selection(...).transform(lambda node: ...)` returns a new
  `Content`. Used internally by `Content.sync_shared`.

### Architecture

- `shared/sync.py` deleted; sync logic now lives on `Content` and reuses
  `Selection.transform`.
- `shared/families.py` rewritten around the new `SharedFamilies` dataclass,
  which holds canonical `Node` bodies (not raw dicts) and exposes `.merge`.
- `shared/fingerprint.py` operates on `Node`, not `dict`.
- `shared/identity.py` collapsed to just `new_shared_id()`.
- `shared/__init__.py` now exports `SharedFamilies`, `fingerprint`,
  `new_shared_id` (down from 8 names).
- Duplicate `TaskItem.shared_id` property removed — the base `Node.shared_id`
  was already covering it.

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
